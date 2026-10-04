"""Offline regression tests. Synthetic scores exist ONLY in a temporary folder."""
import copy
import tempfile
import shutil
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch
import evaluate_final_local as ev

def judgment(key='sample', correctness='C', score=2):
    return {'id':key,'correctness':correctness,'completeness':score,'adequacy':score,
        'clarity':score,'unsupported_addition':False,'uncertain':False,
        'reason':'Synthetic software test, not a scientific judgment.'}

class EvaluationTests(unittest.TestCase):
    def test_invalid_and_missing_scores(self):
        ev.validate({'judgments':[judgment()]},['sample'])
        bad=judgment(); bad['adequacy']=True
        with self.assertRaises(ValueError):
            ev.validate({'judgments':[bad]},['sample'])
        with self.assertRaises(ValueError):
            ev.validate({'judgments':[judgment(),judgment()]},['sample','other'])
        with self.assertRaises(ValueError):
            ev.validate({'judgments':[]},['sample'])

    def test_preference_prioritizes_correctness_not_style(self):
        b={'judgment':judgment(correctness='C',score=0)}
        d={'judgment':judgment(correctness='I',score=2)}
        self.assertEqual(ev.preference(b,d),'base')
        self.assertEqual(ev.preference(b,b),'tie')

    def test_cluster_ci_constant_difference(self):
        pairs=[({'source_id':str(i),'judgment':judgment(correctness='I')},
                {'source_id':str(i),'judgment':judgment(correctness='C')})
               for i in range(10) for _ in range(8)]
        result=ev.clustered_ci(pairs)
        self.assertEqual(result['clusters'],10)
        self.assertEqual(result['delta_percentage_points'],100)
        self.assertEqual(result['percentile95_cluster_bootstrap'],[100,100])

    def test_relocated_training_manifest_hashes(self):
        from pathlib import PureWindowsPath
        count=0
        for p in (ev.ROOT/'evaluation').glob('*test_v1/manifest.json'):
            m=ev.read(p)
            tm=ev.read(ev.ROOT/'runs'/(m['model'].replace('/','__')+'_train_v1')/'run_manifest.json')
            output=tm['dpo']['output_dir']
            path_type=PureWindowsPath if '\\' in output else Path
            original_root=path_type(output).parent.parent
            self.assertEqual(ev.hashed({**tm,'dataset_path':str(original_root/'dataset_consegna')}),m['training_hash'])
            count+=1
        self.assertEqual(count,6)

    @unittest.skipUnless(all((ev.ROOT/'runs'/(ev.read(p)['model'].replace('/','__')+'_train_v1')/'adapter'/name).exists()
        for p in (ev.ROOT/'evaluation').glob('*test_v1/manifest.json')
        for name in ev.read(p)['adapter_hashes']), 'Full integrity test requires the original adapter files, excluded from Git')
    def test_real_input_integrity_and_report_in_temp(self):
        prompts,rows,manifests,training=ev.collect()
        self.assertEqual(len(rows),960)
        self.assertEqual(len(prompts),80)
        self.assertEqual(len(manifests),6)
        self.assertEqual(len({r['blind_id'] for r in rows}),952)
        temp=ev.ROOT/('.test_artifacts_'+uuid.uuid4().hex)
        temp.mkdir()
        try:
            with patch.object(ev,'OUT',Path(temp)):
                ev.save(ev.OUT/'private_mapping.json',rows)
                for r in rows:
                    ev.save(ev.OUT/'judgments'/(r['blind_id']+'.json'),
                            {'judgment':judgment(r['blind_id'])})
                ev.summary()
                result=ev.read(ev.OUT/'summary.json')
                self.assertEqual(result['responses'],960)
                for m in result['models']:
                    self.assertEqual(m['base']['correctness']['C'],80)
                    self.assertEqual(m['dpo']['correctness']['C'],80)
                    self.assertEqual(m['preferences_from_scores']['tie'],80)
                    self.assertEqual(m['correctness_uncertainty']['delta_percentage_points'],0)
                self.assertEqual(len(ev.read(ev.OUT/'human_review_key.json')),24)
                self.assertIn('<table>',(ev.OUT/'REPORT.html').read_text(encoding='utf-8'))
                self.assertTrue((ev.OUT/'correctness.png').stat().st_size>1000)
        finally:
            if not temp.resolve().is_relative_to(ev.ROOT.resolve()) or not temp.name.startswith('.test_artifacts_'):
                raise RuntimeError('Unsafe test cleanup path')
            shutil.rmtree(temp)

if __name__=='__main__':
    unittest.main()
