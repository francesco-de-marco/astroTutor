"""Package local demo assets after closing database writers. No base weights or secrets."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--index',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--database-closed',action='store_true',help='Confirm all database-writing processes are stopped')
    a=p.parse_args()
    if not a.database_closed:p.error('Close indexing/Streamlit processes, then pass --database-closed')
    if a.output.exists():p.error('Output already exists; choose a new filename')
    if not (a.index/'chroma.sqlite3').is_file():p.error('Chroma database not found')
    files=[]
    runs=sorted((a.experiment/'runs').glob('*_train_v1'))
    if len(runs)!=6:p.error('Expected six final train_v1 runs')
    for run in runs:
        adapter=run/'adapter'
        if not (adapter/'adapter_model.safetensors').is_file():p.error('Missing adapter weights: '+str(adapter))
        for f in adapter.rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:
                files.append((f,Path('experiments/dpo_pdf_600/runs')/run.name/'adapter'/f.relative_to(adapter)))
    for f in a.index.rglob('*'):
        if f.is_file():files.append((f,Path('data/vector_db')/f.relative_to(a.index)))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    manifest={}
    with zipfile.ZipFile(a.output,'x',zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        for src,dst in files:
            before=src.stat()
            digest=hashlib.sha256()
            with src.open('rb') as r,z.open(dst.as_posix(),'w',force_zip64=True) as w:
                while block:=r.read(1024*1024):digest.update(block);w.write(block)
            after=src.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                raise RuntimeError('File changed during packaging; discard this archive and retry after stopping writers')
            manifest[dst.as_posix()]={'bytes':before.st_size,'sha256':digest.hexdigest()}
        z.writestr('DEMO_ASSETS_MANIFEST.json',json.dumps(manifest,indent=2))
    print('Created:',a.output.resolve(),flush=True)
    print('Size MiB:',round(a.output.stat().st_size/2**20,1))
    print('Extract into the colleague repository root. Base models and encoders must be downloaded separately.')

if __name__=='__main__':main()
