"""Explicit model download for the offline demo. No credentials are stored here."""
import argparse,json
from pathlib import Path
from huggingface_hub import snapshot_download,HfApi

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--all',action='store_true',help='Download all six model families (many GB)')
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]/'experiments'/'dpo_pdf_600'
    manifests=sorted((root/'runs').glob('*_train_v1/run_manifest.json'))
    selected=[json.loads(f.read_text(encoding='utf-8-sig')) for f in manifests]
    if not a.all:selected=[m for m in selected if m['model']=='Qwen/Qwen2.5-3B-Instruct']
    if not selected:raise RuntimeError('Training manifests not found')
    for m in selected:
        print('Download/cache:',m['model'],m['revision'],flush=True)
        snapshot_download(m['model'],revision=m['revision'],allow_patterns=['*.json','*.safetensors','*.model','*.txt','*.jinja','*.tiktoken'])
    for name in ['BAAI/bge-m3','BAAI/bge-reranker-v2-m3']:
        print('Download/cache:',name,flush=True)
        info=HfApi().model_info(name)
        files={s.rfilename for s in info.siblings}
        weights=['*.safetensors'] if 'model.safetensors' in files else ['pytorch_model.bin','pytorch_model-*.bin']
        snapshot_download(name,revision=info.sha,allow_patterns=['*.json','*.model','*.txt','*.py']+weights)
    print('Download completato. Copiare gli adapter e l’indice prima di avviare la demo.')

if __name__=='__main__':main()
