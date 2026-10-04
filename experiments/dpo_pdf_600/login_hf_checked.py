"""Interactive local login diagnostics. Never prints token or HTTP headers."""
import getpass
import os
import re
import sys
import warnings

def token_problem(value):
    if not value:
        return 'Input vuoto: il token non e stato incollato.'
    if not value.startswith('hf_'):
        return 'Prefisso errato: serve il valore del token personale Hugging Face, che inizia con hf_.'
    if not re.fullmatch(r'hf_[A-Za-z0-9_]+', value):
        return 'Sono presenti spazi, asterischi o altri caratteri inattesi: ricopia il valore completo con il pulsante Copy.'
    return None

def main():
    # Fix the endpoint before importing the HF library; never send credentials to custom endpoints.
    os.environ['HF_ENDPOINT'] = 'https://huggingface.co'
    os.environ.setdefault('HF_HUB_ETAG_TIMEOUT','30')
    import requests
    from huggingface_hub import login, hf_hub_download
    from huggingface_hub.utils import logging as hf_logging
    hf_logging.set_verbosity_error()
    print('Incolla soltanto il valore del token. Non verra mostrato ne inserito nella cronologia.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            value=getpass.getpass('Token Hugging Face (input nascosto): ').strip()
    except (getpass.GetPassWarning,EOFError):
        print('Input nascosto non disponibile. Eseguire direttamente in PowerShell, senza pipe.');return 1
    problem=token_problem(value)
    if problem:
        print(problem);return 1
    print('Formato plausibile. Verifica diretta su huggingface.co...')
    try:
        response=requests.get('https://huggingface.co/api/whoami-v2',
                              headers={'Authorization':'Bearer '+value},timeout=30,allow_redirects=False)
    except requests.RequestException:
        print('Connessione non riuscita. Nessun token salvato.');return 1
    if response.status_code!=200:
        print('HTTP',response.status_code,'dal controllo account. Nessun token salvato.')
        if response.status_code==401:
            print('Il servizio rifiuta questo valore: creare un nuovo token personale e copiarlo integralmente. Non e ancora un problema di accesso a Llama/Gemma.')
        return 1
    try:
        response.json()
        login(token=value,add_to_git_credential=False)
    except Exception:
        print('Token verificato, ma login/salvataggio locale non completato. Nessun dettaglio sensibile stampato.');return 1
    print('LOGIN OK: token salvato nella cache standard Hugging Face, non nelle credenziali Git.')
    for name in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN'):
        if os.environ.get(name) and os.environ[name].strip()!=value:
            print('ATTENZIONE:',name,'contiene un valore diverso e puo prevalere sul login nei successivi comandi.')
    for model in ('meta-llama/Llama-3.2-3B-Instruct','google/gemma-3-1b-it'):
        try:
            hf_hub_download(model,'config.json',token=value)
            print('ACCESSO OK:',model)
        except Exception as error:
            status=getattr(getattr(error,'response',None),'status_code',None)
            print('ACCESSO NON CONFERMATO:',model,'HTTP',status or 'non disponibile')
            print('Controllare approvazione sulla pagina del modello e permessi del token; in caso di errore di rete riprovare.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:
        print('\nOperazione annullata.');sys.exit(130)
