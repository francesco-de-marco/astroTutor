"""
AstroTutor — Allineamento DPO (QLoRA + TRL) — versione LOCALE / cloud (PC, AWS g5, ecc.)

Porting di `src/alignment_dpo_kaggle.ipynb` in uno script eseguibile fuori da Kaggle:
path locali del progetto (niente /kaggle/...), nessun magic Jupyter (`!pip`, `!git`),
GPU singola pinnata esplicitamente, e knob di tuning in cima per sfruttare schede più
grandi della T4 (es. A10G 24GB su AWS g5, RTX 4070).

Pipeline (identica al notebook): dataset triplette -> Qwen2.5-3B 4-bit (NF4) -> LoRA ->
DPOTrainer (ref implicito = adapter disattivati) -> merge bf16 -> GGUF Q4_K_M -> Modelfile.

--------------------------------------------------------------------------------
SETUP (una volta, nell'ambiente in cui giri):

    pip install -U trl peft bitsandbytes datasets accelerate transformers sentencepiece huggingface_hub

  Se compare l'errore `cannot import name 'CachedRepoTreeNotFoundError'` o simili
  mismatch transformers/huggingface_hub, pinna versioni coerenti, es.:
    pip install "transformers>=4.46" "huggingface_hub>=0.26"

  Per la conversione GGUF (step opzionale) servono anche: git, cmake e un compilatore C++
  (build-essential su Linux, "Desktop development with C++" su Windows/MSVC).
  Su Linux/WSL/AWS funziona liscio; su Windows nativo il build di llama.cpp è più fragile.

USO:
    python src/alignment_dpo_local.py                 # training completo + merge + GGUF
    python src/alignment_dpo_local.py --epochs 1      # 1 epoca invece di 2
    python src/alignment_dpo_local.py --skip-gguf     # ferma dopo il merge (niente GGUF)
    python src/alignment_dpo_local.py --skip-train    # solo export da un adapter gia' esistente

  Il training riprende automaticamente dall'ultimo checkpoint in models/dpo_out/ se presente.
--------------------------------------------------------------------------------
"""
import argparse
import gc
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

import torch

# --------------------------------------------------------------------------- #
# Path del progetto (lo script vive in src/, la radice e' la cartella superiore)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "alignment_data.json"

OUT_DIR = PROJECT_ROOT / "models"
DPO_OUT = OUT_DIR / "dpo_out"                       # checkpoint del trainer
ADAPTER_DIR = OUT_DIR / "astrotutor-dpo-adapter"    # adapter LoRA (~100 MB)
MERGED_DIR = OUT_DIR / "astrotutor-3b-dpo-merged"   # modello base + adapter, bf16
GGUF_F16 = OUT_DIR / "astrotutor-3b-dpo-f16.gguf"
GGUF_Q4 = OUT_DIR / "astrotutor-3b-dpo-Q4_K_M.gguf"
MODELFILE = OUT_DIR / "Modelfile"
LLAMA_DIR = OUT_DIR / "llama.cpp"

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"  # stesso modello di qwen2.5:3b su Ollama

# --------------------------------------------------------------------------- #
# KNOB DI TUNING VRAM — i default sono conservativi e girano anche su ~12 GB.
# Su una scheda >=24 GB (A10G/g5, o 4070 Ti Super 16GB) puoi velocizzare:
#   - GRADIENT_CHECKPOINTING = False   (togli il ricalcolo del forward in backward)
#   - PER_DEVICE_TRAIN_BATCH_SIZE = 2  (e magari GRAD_ACCUM = 8 per batch effettivo invariato)
# --------------------------------------------------------------------------- #
PER_DEVICE_TRAIN_BATCH_SIZE = 1
GRAD_ACCUM = 16                  # batch effettivo = BATCH * GRAD_ACCUM
GRADIENT_CHECKPOINTING = True
MAX_LENGTH = 3584                # copre prompt (fino a 3 chunk RAG) + risposta; nessun
                                 # esempio del dataset da 623 supera ~2760 token stimati
OPTIM = "paged_adamw_8bit"       # se dovesse ricomparire un "illegal memory access" in
                                 # optimizer.step(), prova "adamw_8bit" o "adamw_torch"


def build_dataset():
    from datasets import load_dataset

    if not DATA_FILE.exists():
        sys.exit(f"Dataset non trovato: {DATA_FILE}")

    # load_dataset("json", ...) gestisce sia array JSON che JSONL (il file e' JSONL)
    raw = load_dataset("json", data_files=str(DATA_FILE), split="train")
    print(f"Triplette totali: {len(raw)}")
    print("Distribuzione strategie:", sorted(set(raw["strategy"])))

    dataset = raw.select_columns(["prompt", "chosen", "rejected"])
    split = dataset.train_test_split(test_size=0.05, seed=42)
    train_ds, eval_ds = split["train"], split["test"]
    print(f"Train: {len(train_ds)} — Eval: {len(eval_ds)}")

    # Sanity check sul formato conversazionale
    example = train_ds[0]
    assert isinstance(example["prompt"], list) and example["prompt"][0]["role"] == "system"
    assert example["chosen"][0]["role"] == "assistant"
    print("Esempio domanda:", example["prompt"][-1]["content"][:120])
    return train_ds, eval_ds


def load_base_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,  # A10G (Ampere) e 4070 (Ada) hanno tensor
                                                 # core bf16 nativi: qui bf16 e' ideale
                                                 # (la lentezza era colpa della T4 senza)
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        dtype=torch.bfloat16,
        device_map={"": 0},  # tutto sulla prima GPU: con "auto" e piu' GPU visibili
                             # accelerate puo' spezzare il modello, e paged_adamw_8bit ha
                             # bug di sync con tensori sparsi su piu' device (causa dell'
                             # "illegal memory access" in optimizer.step()). Pin -> lo esclude.
    )
    model.config.use_cache = False

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    return model, tokenizer, lora_config


def train(epochs: int):
    from trl import DPOConfig, DPOTrainer
    from transformers.trainer_utils import get_last_checkpoint

    train_ds, eval_ds = build_dataset()
    model, tokenizer, lora_config = load_base_model()

    training_args = DPOConfig(
        output_dir=str(DPO_OUT),
        beta=0.1,
        learning_rate=5e-6,
        num_train_epochs=epochs,
        per_device_train_batch_size=PER_DEVICE_TRAIN_BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        max_length=MAX_LENGTH,
        gradient_checkpointing=GRADIENT_CHECKPOINTING,
        bf16=True,     # bf16 non ha bisogno di loss scaling: niente GradScaler da rompere
        fp16=False,
        optim=OPTIM,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=5,
        eval_strategy="epoch",
        per_device_eval_batch_size=1,   # il default (8) causava OOM in eval sulla T4
        save_strategy="steps",
        save_steps=5,                   # checkpoint frequenti e indipendenti dall'eval:
                                        # un crash non fa perdere piu' di ~5 step
        save_total_limit=3,
        report_to="none",
        precompute_ref_log_probs=True,  # calcola i log-prob del riferimento una volta sola
                                        # prima del training (solo inferenza), invece di
                                        # rifare quel forward a ogni step
        precompute_ref_batch_size=1,
    )

    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        peft_config=lora_config,
    )

    last_checkpoint = get_last_checkpoint(str(DPO_OUT)) if DPO_OUT.is_dir() else None
    if last_checkpoint:
        print(f"Riprendo dal checkpoint: {last_checkpoint}")

    trainer.train(resume_from_checkpoint=last_checkpoint)
    # Da monitorare nei log: rewards/accuracies deve salire verso ~0.8-0.9+
    # (frazione di coppie in cui chosen batte rejected).

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    print(f"Adapter LoRA salvato in: {ADAPTER_DIR}")

    # Libera la VRAM prima del merge (che gira su CPU)
    del trainer, model
    gc.collect()
    torch.cuda.empty_cache()


def merge():
    """Fonde l'adapter LoRA nel modello base (bf16, su CPU per non toccare la VRAM)."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not ADAPTER_DIR.exists():
        sys.exit(f"Adapter non trovato: {ADAPTER_DIR} (esegui prima il training)")

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.bfloat16, device_map="cpu"
    )
    merged = PeftModel.from_pretrained(base, str(ADAPTER_DIR))
    merged = merged.merge_and_unload()
    merged.save_pretrained(str(MERGED_DIR))
    AutoTokenizer.from_pretrained(str(ADAPTER_DIR)).save_pretrained(str(MERGED_DIR))
    print(f"Merge completato: {MERGED_DIR}")

    del base, merged
    gc.collect()


def _run(cmd, **kw):
    print(">", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def _patch_transformers_tokenizer():
    """Patch difensiva al bug in _set_model_specific_special_tokens (extra_special_tokens
    e' una list invece di un dict) che rompe convert_hf_to_gguf.py al caricamento del
    tokenizer. Due punti di rottura noti (.keys() e .items()); patchiamo il sorgente
    installato invece di inseguire versione per versione."""
    import transformers

    tub = Path(transformers.__file__).parent / "tokenization_utils_base.py"
    src = tub.read_text(encoding="utf-8")
    patches = [
        ("self.SPECIAL_TOKENS_ATTRIBUTES = self.SPECIAL_TOKENS_ATTRIBUTES + list(special_tokens.keys())",
         "self.SPECIAL_TOKENS_ATTRIBUTES = self.SPECIAL_TOKENS_ATTRIBUTES + (list(special_tokens.keys()) if isinstance(special_tokens, dict) else [])"),
        ("for key, value in special_tokens.items():",
         "for key, value in (special_tokens.items() if isinstance(special_tokens, dict) else []):"),
    ]
    changed = False
    for old, new in patches:
        if old in src:
            src = src.replace(old, new)
            changed = True
            print(f"Patchata riga: {old[:70]}")
        elif new in src:
            print(f"Gia' patchata: {old[:70]}")
        else:
            print(f"ATTENZIONE: pattern non trovato: {old[:70]}")
    if changed:
        tub.write_text(src, encoding="utf-8")


def to_gguf():
    """Converte il modello merged in GGUF f16 e lo quantizza in Q4_K_M.
    Richiede git, cmake e un compilatore C++. Su Windows nativo puo' essere fragile:
    in caso di problemi, esegui questo step in WSL2/Linux o salta con --skip-gguf e
    fai la conversione separatamente."""
    if not MERGED_DIR.exists():
        sys.exit(f"Modello merged non trovato: {MERGED_DIR} (esegui prima il merge)")

    # Clona/aggiorna llama.cpp
    if LLAMA_DIR.exists():
        shutil.rmtree(LLAMA_DIR)
    _run(["git", "clone", "--depth", "1",
          "https://github.com/ggml-org/llama.cpp", str(LLAMA_DIR)])

    _run([sys.executable, "-m", "pip", "install", "-q", "-r",
          str(LLAMA_DIR / "requirements" / "requirements-convert_hf_to_gguf.txt")])

    _patch_transformers_tokenizer()

    # HF -> GGUF f16
    _run([sys.executable, str(LLAMA_DIR / "convert_hf_to_gguf.py"), str(MERGED_DIR),
          "--outfile", str(GGUF_F16), "--outtype", "f16"])

    # Build del solo target llama-quantize
    _run(["cmake", "-S", str(LLAMA_DIR), "-B", str(LLAMA_DIR / "build"), "-DLLAMA_CURL=OFF"])
    _run(["cmake", "--build", str(LLAMA_DIR / "build"), "--target", "llama-quantize", "-j"])

    # Individua il binario (Linux: build/bin/llama-quantize ; Windows: build/bin/Release/llama-quantize.exe)
    matches = glob.glob(str(LLAMA_DIR / "build" / "**" / "llama-quantize*"), recursive=True)
    matches = [m for m in matches if not m.endswith((".o", ".obj"))]
    if not matches:
        sys.exit("llama-quantize non trovato dopo il build: converti manualmente da GGUF_F16.")
    quantize_bin = matches[0]

    _run([quantize_bin, str(GGUF_F16), str(GGUF_Q4), "Q4_K_M"])
    print(f"GGUF quantizzato: {GGUF_Q4} ({GGUF_Q4.stat().st_size / 1e6:.0f} MB)")


def write_modelfile():
    # Il FROM punta al .gguf nella stessa cartella del Modelfile
    modelfile = '''FROM ./astrotutor-3b-dpo-Q4_K_M.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>
"""
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''
    MODELFILE.write_text(modelfile, encoding="utf-8")
    print(f"Modelfile scritto: {MODELFILE}")
    print("Installa in Ollama con:")
    print(f"  cd {OUT_DIR}")
    print("  ollama create astrotutor-dpo -f Modelfile")


def main():
    parser = argparse.ArgumentParser(description="DPO locale per AstroTutor")
    parser.add_argument("--epochs", type=int, default=2, help="numero di epoche (default 2)")
    parser.add_argument("--skip-train", action="store_true", help="salta il training, esporta da adapter esistente")
    parser.add_argument("--skip-gguf", action="store_true", help="ferma dopo il merge (niente GGUF)")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        sys.exit("CUDA non disponibile: serve una GPU NVIDIA con driver/toolkit installati.")
    print(f"GPU: {torch.cuda.get_device_name(0)} | GPU visibili: {torch.cuda.device_count()}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_train:
        train(args.epochs)

    merge()

    if not args.skip_gguf:
        to_gguf()
        write_modelfile()
    else:
        print("GGUF saltato (--skip-gguf): modello merged pronto in", MERGED_DIR)


if __name__ == "__main__":
    main()
