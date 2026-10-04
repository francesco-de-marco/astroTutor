"""Importa bozze IA nel flusso di revisione; nessuna chiamata al modello o training."""
import argparse
import importlib.util
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drafts', default='data/splits/pilot_curated_v1.json')
    parser.add_argument('--source-run', default='results/dpo_pilot_v2')
    parser.add_argument('--run-dir', default='results/dpo_pilot_curated_v1')
    args = parser.parse_args()
    module_path = Path(__file__).with_name('dpo_pilot_v2.py')
    spec = importlib.util.spec_from_file_location('pilot_tools', module_path)
    p = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p)
    old = p.read(Path(args.source_run) / 'manifest.json')
    drafts = p.read(args.drafts)
    # Blocca l'importazione se il builder del prompt e' cambiato.
    if old['system'] != p.SYSTEM or old['levels'] != p.LEVELS:
        raise ValueError('Prompt differente da quello del pilota v2. Importazione bloccata.')
    p.validate_spec(old['spec'])
    expected = {q['id'] + '_' + level for q in old['spec']['questions'] for level in p.LEVELS}
    if set(drafts['answers']) != expected:
        raise ValueError('Gli ID delle bozze non corrispondono esattamente al pilota.')
    if any(not isinstance(a, str) or not a.strip() for a in drafts['answers'].values()):
        raise ValueError('Risposta vuota o non testuale.')
    manifest = {
        'schema': 2, 'spec': old['spec'], 'system': old['system'], 'levels': old['levels'],
        'model': None, 'options': None,
        'authoring_method': 'assistant_authored_drafts_for_human_review',
        'authorship': drafts['authorship'], 'drafts_hash': p.digest(drafts),
        'source_manifest_hash': p.digest(old),
        'note': 'Stesso prompt v2, risposte riscritte. Nessuna provenienza Qwen per queste bozze. '
                'Preferenze non assegnate; giudizi precedenti non trasferiti.'}
    root = Path(args.run_dir)
    if root.resolve() == Path(args.source_run).resolve():
        raise ValueError('La destinazione deve essere diversa dal lotto originale.')
    path = root / 'manifest.json'
    if path.exists():
        if p.read(path) != manifest:
            raise ValueError('Bozze/configurazione cambiate: usa una nuova --run-dir.')
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError('Destinazione non vuota senza manifest.')
        p.save(path, manifest)
    for q in old['spec']['questions']:
        context = old['spec']['sources'][q['source_id']]['context']
        for level in p.LEVELS:
            cid = q['id'] + '_' + level
            row = {'id': cid, 'manifest_hash': p.digest(manifest),
                   'messages': p.build_prompt(q['question'], level, context),
                   'answer': drafts['answers'][cid],
                   'origin': 'assistant_authored', 'quality_status': 'requires_human_review'}
            destination = root / 'candidates' / (cid + '.json')
            if destination.exists():
                if p.read(destination) != row:
                    raise ValueError('Candidato modificato: usa una nuova --run-dir.')
            else:
                p.save(destination, row)
    assert len(p.pairs(root)) == len(expected)
    print(f'Importate {len(expected)} bozze; 0 preferenze assegnate automaticamente.')
    print(f'Cartella: {root}')
    print('Usa preview, review, status, export con --run-dir su questa cartella.')
    print('Non usare generate/audit su questo lotto: non contiene output Ollama.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        print(f'ERRORE: {exc}', file=sys.stderr)
        sys.exit(1)
