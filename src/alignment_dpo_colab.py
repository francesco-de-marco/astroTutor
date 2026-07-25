"""
AstroTutor — Allineamento DPO (QLoRA + TRL) — versione COLAB

Sostituisce `alignment_dpo_local.py` e `alignment_dpo_kaggle.ipynb`: il training in
locale e' stato abbandonato (vedi NOTA VRAM qui sotto), Kaggle pure (la T4 e' Turing,
niente tensor core bf16 -> ~11 min/step, ETA 8h).

Pipeline: dataset triplette -> Qwen2.5-3B 4-bit (NF4) -> LoRA -> DPOTrainer
(ref implicito = adapter disattivati) -> merge bf16 -> GGUF Q4_K_M -> Modelfile.

--------------------------------------------------------------------------------
NOTA VRAM — perche' serve Liger (o una GPU grande)

TRL calcola una metrica di entropia per-token a ogni batch:

    per_token_entropy = entropy_from_logits(shift_logits.detach())

E' incondizionata (nessun flag per spegnerla) e materializza i logits sull'intero
vocabolario di Qwen2.5 (151.936 token) per chosen e rejected insieme. Con le
lunghezze reali del dataset (mediana ~2.070 token, max ~3.020) sono 1,3-1,8 GB in
bf16, che diventano ~5-7 GB una volta contati l'upcast a fp32 e il gradiente.
E' la causa di tutti gli OOM di questo progetto (T4 in training, T4 in eval,
precompute a batch 4, RTX 4060 8GB). Il `.detach()` dice tutto: quel tensore non
partecipa nemmeno al gradiente, e' solo una diagnostica da stampare nei log.

`use_liger_kernel=True` instrada la loss sul path fuso di TRL (`_compute_loss_liger`),
che calcola lm_head + loss a blocchi e non materializza mai i logits interi. Il
problema sparisce alla radice ed e' anche piu' veloce. In cambio il path Liger NON
calcola le metriche di entropia (che e' esattamente cio' che vogliamo) e restituisce
un set di metriche piu' ridotto: verificare al primo step che `rewards/accuracies`
compaia ancora nei log (vedi --smoke).

Su Windows Liger non e' praticabile (dipende da Triton), da cui la scelta di Colab.
--------------------------------------------------------------------------------
USO SU COLAB — Runtime > Cambia tipo di runtime > GPU L4 (bastano; A100 se libera)

E' uno script, non un notebook: si lancia con `!python` da una cella. Ogni `!python`
e' un processo nuovo, quindi dopo il pip install non serve riavviare il runtime.
L'unica cosa che DEVE stare in una cella e' il mount di Drive: l'autorizzazione
OAuth passa dal frontend del notebook e da un subprocess non funziona.

Cella 1 — mount (interattivo, obbligatoriamente qui):
    from google.colab import drive
    drive.mount('/content/drive')

Cella 2 — setup:
    !git clone https://github.com/francesco-de-marco/astroTutor.git /content/repo
    !python /content/repo/src/alignment_dpo_colab.py --install

Cella 3 — verifica veloce (3 step: guarda VRAM e metriche, non tocca i checkpoint):
    !python /content/repo/src/alignment_dpo_colab.py --smoke 3

Cella 4 — run vero:
    !python /content/repo/src/alignment_dpo_colab.py

Non c'e' altro da preparare: il dataset (data/alignment_data.json) e' tracciato da
git e arriva col clone, e le cartelle su Drive le crea lo script. Su Drive
(MyDrive/astrotutor/models/) finiscono solo checkpoint per il resume, adapter LoRA,
GGUF Q4_K_M e Modelfile.

FLAG:
    --install         installa le dipendenze (inclusa liger-kernel) ed esce
    --smoke N         run di prova da N step in una cartella separata
    --epochs N        default 2
    --no-liger        disattiva Liger (serve allora una GPU >=24 GB, es. A100)
    --no-precompute   disattiva precompute_ref_log_probs (primo sospetto se il
                      primo step esplode con Liger attivo)
    --skip-train      solo export da un adapter gia' esistente su Drive
    --skip-gguf       ferma dopo il merge

Il training riprende da solo dall'ultimo checkpoint su Drive, se presente.
--------------------------------------------------------------------------------
"""
import argparse
import gc
import glob
import shutil
import subprocess
import sys
from pathlib import Path

import torch

# --------------------------------------------------------------------------- #
# Path
#   REPO_ROOT  -> il repo clonato nel runtime; contiene gia' il dataset (tracciato
#                 da git), quindi non c'e' niente da caricare a mano su Drive
#   DRIVE_ROOT -> sopravvive alla disconnessione del runtime: ci va solo l'output
#                 che non si vuole rigenerare (checkpoint, adapter, GGUF finale)
#   WORK_ROOT  -> disco locale del runtime: veloce, capiente, volatile. Ci vanno gli
#                 intermedi voluminosi, perche' scrivere GB su Drive (mount FUSE) e'
#                 lentissimo e si rigenerano dall'adapter in pochi minuti
# --------------------------------------------------------------------------- #
def _find_repo_root() -> Path:
    """Radice del repo clonato. `__file__` non e' definito se il codice viene
    incollato in una cella del notebook invece di essere lanciato con `!python`:
    in quel caso si cerca il repo nei percorsi noti."""
    try:
        return Path(__file__).resolve().parent.parent
    except NameError:
        for candidate in (Path("/content/repo"), Path.cwd(), Path.cwd().parent):
            if (candidate / "data" / "alignment_data.json").exists():
                return candidate
        return Path("/content/repo")


REPO_ROOT = _find_repo_root()
DRIVE_ROOT = Path("/content/drive/MyDrive/astrotutor")
WORK_ROOT = Path("/content/astrotutor_work")

DATA_FILE = REPO_ROOT / "data" / "alignment_data.json"
MODELS_DIR = DRIVE_ROOT / "models"
DPO_OUT = MODELS_DIR / "dpo_out"                      # checkpoint del trainer (resume)
SMOKE_OUT = WORK_ROOT / "dpo_smoke"                   # checkpoint della run di prova
ADAPTER_DIR = MODELS_DIR / "astrotutor-dpo-adapter"   # adapter LoRA (~120 MB)
GGUF_Q4 = MODELS_DIR / "astrotutor-3b-dpo-Q4_K_M.gguf"
MODELFILE = MODELS_DIR / "Modelfile"

MERGED_DIR = WORK_ROOT / "astrotutor-3b-dpo-merged"   # ~6 GB, usa e getta
GGUF_F16 = WORK_ROOT / "astrotutor-3b-dpo-f16.gguf"   # ~6 GB, usa e getta
LLAMA_DIR = WORK_ROOT / "llama.cpp"

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"  # stesso modello di qwen2.5:3b su Ollama

DEPS = [
    "trl", "peft", "bitsandbytes", "datasets", "accelerate",
    "transformers", "sentencepiece", "huggingface_hub", "liger-kernel",
]

# --------------------------------------------------------------------------- #
# KNOB
# Con Liger attivo il picco crolla: su A100 si puo' provare GRADIENT_CHECKPOINTING
# = False e PER_DEVICE_TRAIN_BATCH_SIZE = 2 (con GRAD_ACCUM 8) per andare piu' veloci.
# --------------------------------------------------------------------------- #
PER_DEVICE_TRAIN_BATCH_SIZE = 1
GRAD_ACCUM = 16                  # batch effettivo = BATCH * GRAD_ACCUM
GRADIENT_CHECKPOINTING = True
MAX_LENGTH = 3584                # cap di troncamento; il max reale misurato sulle 623
                                 # triplette e' ~3.020 token, quindi non tronca nulla.
                                 # Abbassarlo NON libera memoria: con batch=1 non c'e'
                                 # padding, il costo dipende dalla lunghezza reale.
OPTIM = "paged_adamw_8bit"       # se ricompare "illegal memory access" in optimizer.step(),
                                 # prova "adamw_8bit" o "adamw_torch"
SAVE_STEPS = 10                  # checkpoint su Drive: piu' frequenti = piu' scritture lente


# --------------------------------------------------------------------------- #
# Setup ambiente
# --------------------------------------------------------------------------- #
def install_deps():
    print("Installazione dipendenze...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", *DEPS], check=True)
    print("Fatto. Riavvia il runtime se pip segnala conflitti, poi lancia --smoke 3.")


def check_drive():
    """Verifica che Drive sia montato e crea l'albero di output.
    Il mount NON puo' avvenire qui: `drive.mount()` fa passare l'autorizzazione OAuth
    dal frontend del notebook, canale che un subprocess `!python` non ha. Va quindi
    eseguito una volta in una cella; da li' in poi /content/drive e' visibile a tutti
    i processi del runtime, questo incluso."""
    if not Path("/content/drive/MyDrive").is_dir():
        sys.exit(
            "Drive non montato. Esegui PRIMA in una cella del notebook:\n\n"
            "    from google.colab import drive\n"
            "    drive.mount('/content/drive')\n"
        )
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output durevoli su: {MODELS_DIR}")


def liger_available() -> bool:
    try:
        from trl.import_utils import is_liger_kernel_available
        return is_liger_kernel_available()
    except Exception:
        import importlib.util
        return importlib.util.find_spec("liger_kernel") is not None


def check_gpu():
    if not torch.cuda.is_available():
        sys.exit("Nessuna GPU: Runtime > Cambia tipo di runtime > GPU (L4).")
    name = torch.cuda.get_device_name(0)
    total = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"GPU: {name} — {total:.1f} GB")
    if "T4" in name:
        print(
            "⚠️  T4 (Turing): niente tensor core bf16 nativi. Il training sara' "
            "lentissimo (~11 min/step misurati il 20/07). Cambia runtime."
        )
    return total


# --------------------------------------------------------------------------- #
# Dataset e modello
# --------------------------------------------------------------------------- #
def build_dataset():
    from datasets import load_dataset

    if not DATA_FILE.exists():
        sys.exit(
            f"Dataset non trovato: {DATA_FILE}\n"
            "Dovrebbe arrivare col repo (e' tracciato da git): controlla il clone."
        )

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
        bnb_4bit_compute_dtype=torch.bfloat16,  # L4 (Ada) e A100 (Ampere) hanno tensor
                                                 # core bf16 nativi
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        dtype=torch.bfloat16,
        device_map={"": 0},  # tutto sulla prima GPU: con "auto" accelerate potrebbe
                             # spezzare il modello, e paged_adamw_8bit ha bug di sync
                             # su tensori sparsi tra device (l'"illegal memory access"
                             # in optimizer.step()). Pin -> lo esclude.
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


# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #
def _peak_vram_callback():
    """Stampa il picco di VRAM a ogni logging: serve a capire subito quanto margine
    c'e' (con Liger dovrebbe restare ben sotto i 10 GB)."""
    from transformers import TrainerCallback

    class PeakVRAM(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if torch.cuda.is_available():
                peak = torch.cuda.max_memory_allocated() / 1e9
                print(f"   [VRAM] picco allocato finora: {peak:.2f} GB")

    return PeakVRAM()


def train(epochs: int, use_liger: bool, precompute: bool, smoke_steps: int = 0):
    from trl import DPOConfig, DPOTrainer
    from transformers.trainer_utils import get_last_checkpoint

    train_ds, eval_ds = build_dataset()
    model, tokenizer, lora_config = load_base_model()

    out_dir = SMOKE_OUT if smoke_steps else DPO_OUT

    kwargs = dict(
        output_dir=str(out_dir),
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
        logging_steps=1 if smoke_steps else 5,
        save_strategy="steps",
        save_steps=SAVE_STEPS,          # checkpoint indipendenti dall'eval: un crash
                                        # in eval non azzera il progresso del training
        save_total_limit=3,
        report_to="none",
        use_liger_kernel=use_liger,     # vedi NOTA VRAM in cima al file
    )

    if smoke_steps:
        # Prova secca: niente eval, niente salvataggi, cartella separata per non
        # inquinare i checkpoint della run vera.
        kwargs.update(max_steps=smoke_steps, save_strategy="no", eval_strategy="no")
    else:
        kwargs.update(eval_strategy="epoch", per_device_eval_batch_size=1)
        # il default (8) causava OOM in eval: stesso tensore dei logits, batch 8x

    if precompute:
        kwargs.update(
            precompute_ref_log_probs=True,  # log-prob del riferimento calcolati una
                                            # volta sola prima del training (sola
                                            # inferenza) invece che a ogni step
            precompute_ref_batch_size=1,
        )

    training_args = DPOConfig(**kwargs)

    trainer = DPOTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=None if smoke_steps else eval_ds,
        processing_class=tokenizer,
        peft_config=lora_config,
        callbacks=[_peak_vram_callback()],
    )

    last_checkpoint = None
    if not smoke_steps and DPO_OUT.is_dir():
        last_checkpoint = get_last_checkpoint(str(DPO_OUT))
        if last_checkpoint:
            print(f"Riprendo dal checkpoint: {last_checkpoint}")

    trainer.train(resume_from_checkpoint=last_checkpoint)

    if smoke_steps:
        print(
            f"\n✓ Smoke test superato ({smoke_steps} step).\n"
            "  Controlla sopra: (1) il picco VRAM ha margine? (2) nei log compare "
            "`rewards/accuracies`?\n"
            "  Se `rewards/accuracies` manca, e' il path Liger che non la espone: o "
            "accetti di non monitorarla, o rilanci con --no-liger su GPU >=24 GB.\n"
            "  Poi lancia la run vera senza --smoke."
        )
        shutil.rmtree(SMOKE_OUT, ignore_errors=True)
        return

    # Da monitorare nei log: rewards/accuracies deve salire verso ~0.8-0.9+
    # (frazione di coppie in cui chosen batte rejected).
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(ADAPTER_DIR))
    tokenizer.save_pretrained(str(ADAPTER_DIR))
    print(f"Adapter LoRA salvato su Drive: {ADAPTER_DIR}")

    del trainer, model
    gc.collect()
    torch.cuda.empty_cache()


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def merge():
    """Fonde l'adapter LoRA nel modello base (bf16). Su GPU se c'e' VRAM libera —
    e' molto piu' veloce e su Colab la RAM di sistema e' piu' scarsa della VRAM."""
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not ADAPTER_DIR.exists():
        sys.exit(f"Adapter non trovato: {ADAPTER_DIR} (esegui prima il training)")

    free = torch.cuda.mem_get_info()[0] / 1e9 if torch.cuda.is_available() else 0
    device = "cuda" if free >= 10 else "cpu"   # il 3B in bf16 pesa ~6,2 GB
    print(f"Merge su {device} (VRAM libera: {free:.1f} GB)")

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.bfloat16, device_map=device
    )
    merged = PeftModel.from_pretrained(base, str(ADAPTER_DIR))
    merged = merged.merge_and_unload()
    MERGED_DIR.parent.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(MERGED_DIR))
    AutoTokenizer.from_pretrained(str(ADAPTER_DIR)).save_pretrained(str(MERGED_DIR))
    print(f"Merge completato: {MERGED_DIR}")

    del base, merged
    gc.collect()
    torch.cuda.empty_cache()


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
    Gira in /content: solo il Q4 finale (~2 GB) finisce su Drive."""
    if not MERGED_DIR.exists():
        sys.exit(f"Modello merged non trovato: {MERGED_DIR} (esegui prima il merge)")

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

    matches = glob.glob(str(LLAMA_DIR / "build" / "**" / "llama-quantize*"), recursive=True)
    matches = [m for m in matches if not m.endswith((".o", ".obj"))]
    if not matches:
        sys.exit("llama-quantize non trovato dopo il build: converti manualmente da GGUF_F16.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _run([matches[0], str(GGUF_F16), str(GGUF_Q4), "Q4_K_M"])
    print(f"GGUF su Drive: {GGUF_Q4} ({GGUF_Q4.stat().st_size / 1e6:.0f} MB)")


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
    print("\nScarica da Drive astrotutor-3b-dpo-Q4_K_M.gguf + Modelfile in models/, poi:")
    print("  ollama create astrotutor-dpo -f Modelfile")


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="DPO su Colab per AstroTutor")
    parser.add_argument("--install", action="store_true", help="installa le dipendenze ed esce")
    parser.add_argument("--smoke", type=int, default=0, metavar="N",
                        help="run di prova da N step (verifica VRAM e metriche)")
    parser.add_argument("--epochs", type=int, default=2, help="numero di epoche (default 2)")
    parser.add_argument("--no-liger", action="store_true", help="disattiva Liger (serve GPU >=24 GB)")
    parser.add_argument("--no-precompute", action="store_true", help="disattiva precompute_ref_log_probs")
    parser.add_argument("--skip-train", action="store_true", help="solo export da un adapter esistente")
    parser.add_argument("--skip-gguf", action="store_true", help="ferma dopo il merge")

    # In un notebook sys.argv contiene gli argomenti del kernel ipython (-f ...),
    # che argparse rifiuterebbe: in quel caso si usano i default.
    in_notebook = "ipykernel" in sys.modules
    args = parser.parse_args([] if in_notebook else None)

    if args.install:
        install_deps()
        return

    total_vram = check_gpu()
    check_drive()
    WORK_ROOT.mkdir(parents=True, exist_ok=True)

    use_liger = not args.no_liger
    if use_liger and not liger_available():
        sys.exit("liger-kernel non installato: lancia --install (oppure usa --no-liger).")
    if not use_liger and total_vram < 24:
        print(
            f"⚠️  Liger disattivato su una GPU da {total_vram:.0f} GB: i logits sull'intero "
            "vocabolario chiedono ~5-7 GB di picco in piu'. Rischio OOM concreto."
        )
    print(f"Liger: {'attivo' if use_liger else 'disattivo'} | "
          f"precompute_ref_log_probs: {not args.no_precompute}")

    if args.smoke:
        train(args.epochs, use_liger, not args.no_precompute, smoke_steps=args.smoke)
        return

    if not args.skip_train:
        train(args.epochs, use_liger, not args.no_precompute)

    merge()

    if not args.skip_gguf:
        to_gguf()
        write_modelfile()
    else:
        print("GGUF saltato (--skip-gguf): modello merged pronto in", MERGED_DIR)


if __name__ == "__main__":
    main()
