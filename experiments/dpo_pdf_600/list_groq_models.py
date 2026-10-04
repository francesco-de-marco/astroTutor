"""Elenca i modelli Groq senza inviare contesti o generare risposte."""
import os
import sys

from build_dataset import http


def main():
    key = os.environ.get('ORACLE_API_KEY', '').strip()
    if not key:
        print('Chiave ORACLE_API_KEY mancante.', file=sys.stderr)
        return 2
    try:
        response = http(
            'https://api.groq.com/openai/v1/models',
            headers={'Authorization': 'Bearer ' + key},
        )
        identifiers = sorted({row['id'] for row in response['data']})
    except Exception as exc:
        print(f'Elenco non disponibile: {str(exc).replace(key, "[CHIAVE OSCURATA]")}', file=sys.stderr)
        return 2
    print('Modelli restituiti da Groq (la generazione richiede una prova separata):')
    for identifier in identifiers:
        print(identifier)
    print(f'Totale: {len(identifiers)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
