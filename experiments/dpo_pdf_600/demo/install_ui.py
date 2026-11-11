"""Install UI-only wheels into .packages; preserve the training environment.

PyPI HTTPS downloads are checked against the SHA256 in PyPI metadata.
Only pure Python or Windows ABI-independent wheels are accepted.
"""
from pathlib import Path
import hashlib,json,urllib.request,zipfile,io
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent
PACKAGES={'streamlit':'1.64.0','altair':'6.0.0','pydeck':'0.9.1','toml':'0.10.2',
          'watchdog':'6.0.0','starlette':'0.48.0','python-multipart':'0.0.20','itsdangerous':'2.2.0'}
def install(item):
    name,version=item
    with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=30) as r:d=json.load(r)
    wheels=[f for f in d['urls'] if f['filename'].endswith(('py3-none-any.whl','py2.py3-none-any.whl','py3-none-win_amd64.whl'))]
    if len(wheels)!=1:raise RuntimeError(f'Wheel ambiguous/missing: {name}')
    f=wheels[0]
    with urllib.request.urlopen(f['url'],timeout=90) as r:blob=r.read()
    assert hashlib.sha256(blob).hexdigest()==f['digests']['sha256']
    target=(ROOT/'.packages').resolve();target.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for member in z.namelist():
            if not (target/member).resolve().is_relative_to(target):raise RuntimeError('Unsafe wheel path')
        z.extractall(target)
    print('Installed',name,version,flush=True)
    return {'name':name,'version':version,'wheel':f['filename'],'sha256':f['digests']['sha256']}
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:installed=list(pool.map(install,PACKAGES.items()))
    (ROOT/'ui_dependencies.json').write_text(json.dumps(installed,indent=2),encoding='utf8')
