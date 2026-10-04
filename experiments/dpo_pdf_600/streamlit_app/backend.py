"""Local demo using the original retrieval and the final, saved DPO adapters.

No training, API judge, checkpoint download, or writes to evaluation artifacts.
"""
import gc
import json
import os
import sys
import threading
import time
from contextlib import nullcontext
from pathlib import Path

HERE=Path(__file__).resolve().parent
EXPERIMENT=Path(os.environ.get('ASTROTUTOR_EXPERIMENT_DIR',str(HERE.parent))).resolve()
_default_repo=next((p for p in HERE.parents if (p/'src'/'retrieval.py').is_file()),Path.home()/'Documents'/'astroTutor')
REPO=Path(os.environ.get('ASTROTUTOR_REPO',str(_default_repo))).resolve()
MODELS={
    'Qwen 2.5 3B':'Qwen/Qwen2.5-3B-Instruct',
    'Qwen 2.5 1.5B':'Qwen/Qwen2.5-1.5B-Instruct',
    'SmolLM3 3B':'HuggingFaceTB/SmolLM3-3B',
    'Gemma 3 1B':'google/gemma-3-1b-it',
    'Llama 3.2 3B':'meta-llama/Llama-3.2-3B-Instruct',
    'Mistral 7B':'mistralai/Mistral-7B-Instruct-v0.3',
}
LEVELS={'A':'Scuola primaria','B':'Scuola media','C':'Scuola superiore','D':'Università'}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def run_path(model):
    if model not in MODELS.values():raise ValueError('Modello non previsto.')
    return EXPERIMENT/'runs'/(model.replace('/','__')+'_train_v1')

def validate_question(question,level):
    question=question.strip()
    if not question:raise ValueError('Scrivi una domanda.')
    if len(question)>1500:raise ValueError('La domanda deve avere al massimo 1500 caratteri.')
    if level not in LEVELS:raise ValueError('Livello non valido.')
    return question

def adapt_messages(messages,policy):
    messages=[dict(m) for m in messages]
    if policy=='merge_system_into_first_user':
        if len(messages)<2 or messages[0]['role']!='system' or messages[1]['role']!='user':
            raise ValueError('Formato del prompt inatteso.')
        messages=[{'role':'user','content':messages[0]['content']+'\n\n'+messages[1]['content']}]+messages[2:]
    return messages

def available_models():
    found=[]
    for label,model in MODELS.items():
        p=run_path(model)
        if (p/'result.json').exists() and read(p/'result.json').get('status')=='completed' and (p/'adapter'/'adapter_config.json').exists():
            found.append(label)
    return found

class TutorService:
    def __init__(self):
        self.lock=threading.RLock()
        self.retriever=None
        self.model=None
        self.model_id=None
        self.tokenizer=None
        self.manifest=None

    def _retrieval(self):
        if self.retriever is not None:return self.retriever
        if not (REPO/'src'/'retrieval.py').exists():
            raise RuntimeError('Repository non trovato. Imposta ASTROTUTOR_REPO prima di avviare.')
        sys.path.insert(0,str(REPO)) if str(REPO) not in sys.path else None
        from src.retrieval import AdvancedRetriever
        from chromadb import PersistentClient
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        from sentence_transformers import CrossEncoder
        db=Path(os.environ.get('ASTROTUTOR_DB_PATH',str(REPO/'data'/'vector_db')))
        if not (db/'chroma.sqlite3').exists():raise RuntimeError('Indice RAG assente: serve il database già costruito dal progetto.')
        # Reuse the original search method; keep encoder and reranker on CPU so
        # the 8 GB GPU is available for the language model.
        retriever=AdvancedRetriever.__new__(AdvancedRetriever)
        retriever.client=PersistentClient(path=str(db))
        retriever.bge_ef=SentenceTransformerEmbeddingFunction(model_name='BAAI/bge-m3',device='cpu')
        retriever.collection=retriever.client.get_collection(name='rag_knowledge_base',embedding_function=retriever.bge_ef)
        retriever.reranker=CrossEncoder('BAAI/bge-reranker-v2-m3',device='cpu',local_files_only=True)
        self.retriever=retriever
        return retriever

    def _unload(self):
        self.model=None;self.tokenizer=None;self.model_id=None;self.manifest=None
        gc.collect()
        import torch
        if torch.cuda.is_available():torch.cuda.empty_cache()

    def unload(self):
        with self.lock:self._unload()

    def _load(self,model_id):
        if self.model_id==model_id:return
        self._unload()
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig
        from peft import PeftModel
        if not torch.cuda.is_available():raise RuntimeError('Per questa demo dei modelli addestrati serve CUDA.')
        run=run_path(model_id);manifest=read(run/'run_manifest.json')
        if manifest['model']!=model_id or read(run/'result.json')['status']!='completed':raise RuntimeError('Run di training non valido.')
        tokenizer=AutoTokenizer.from_pretrained(str(run/'adapter'),local_files_only=True)
        quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
        base=AutoModelForCausalLM.from_pretrained(model_id,revision=manifest['revision'],
            quantization_config=quant,torch_dtype=torch.bfloat16,device_map={'':0},
            attn_implementation='sdpa',local_files_only=True)
        try:model=PeftModel.from_pretrained(base,str(run/'adapter'),is_trainable=False,local_files_only=True)
        except Exception:
            del base;gc.collect();torch.cuda.empty_cache();raise
        model.eval();self.model=model;self.tokenizer=tokenizer;self.manifest=manifest;self.model_id=model_id

    def _generate(self,messages,side,max_tokens=384):
        import torch
        prompt=self.tokenizer.apply_chat_template(adapt_messages(messages,self.manifest.get('message_policy','native_roles')),
            tokenize=False,add_generation_prompt=True,**self.manifest.get('chat_template_kwargs',{}))
        encoded=self.tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda')
        if encoded['input_ids'].shape[1]>4096:
            raise RuntimeError('Contesto troppo lungo per la demo: riduci il numero di fonti.')
        eos=self.model.generation_config.eos_token_id
        if eos is None:eos=self.tokenizer.eos_token_id
        with torch.inference_mode(),(self.model.disable_adapter() if side=='base' else nullcontext()):
            ids=self.model.generate(**encoded,max_new_tokens=max_tokens,do_sample=False,num_beams=1,
                repetition_penalty=1.0,use_cache=True,pad_token_id=self.tokenizer.pad_token_id,eos_token_id=eos)
        completion=ids[0,encoded['input_ids'].shape[1]:].tolist()
        eos_ids=set(eos if isinstance(eos,list) else [eos])
        return {'text':self.tokenizer.decode(completion,skip_special_tokens=True).strip(),
            'token_limit':len(completion)>=max_tokens and (not completion or completion[-1] not in eos_ids),
            'completion_tokens':len(completion)}

    def answer(self,question,level,model_id,mode='dpo',source_count=3):
        question=validate_question(question,level)
        if mode not in ('base','dpo','compare'):raise ValueError('Modalità non valida.')
        if source_count not in (1,2,3):raise ValueError('Numero fonti non valido.')
        with self.lock:
            started=time.perf_counter()
            retriever=self._retrieval()
            # Retrieval happens ONCE for a paired comparison. No translation or
            # adaptive rewriting: this live demo is not the frozen evaluation.
            docs=retriever.search([question],user_level=level,initial_k=15,final_k=source_count)
            result={'question':question,'level':level,'model':model_id,'mode':mode,'docs':docs,
                'answers':{},'retrieval_queries':[question],'guardrails_enabled':False,
                'note':'Demo RAG live: prompt originale, sola query italiana; non è il test congelato.'}
            if not docs:
                result['no_sources']=True;result['elapsed_seconds']=round(time.perf_counter()-started,2)
                return result
            self._load(model_id)
            from src.generation import RAGGenerator
            # Prompt construction has no side effects and does not require an
            # Ollama client. The actual model is the saved HF base + adapter.
            builder=RAGGenerator.__new__(RAGGenerator)
            messages=builder.build_prompt(question,docs,level)
            for side in (('base','dpo') if mode=='compare' else (mode,)):
                result['answers'][side]=self._generate(messages,side)
            result['elapsed_seconds']=round(time.perf_counter()-started,2)
            result['model_revision']=self.manifest['revision']
            return result

def result_summary():
    path=EXPERIMENT/'evaluation'/'final_groq_v1'/'summary.json'
    return read(path) if path.exists() else None
