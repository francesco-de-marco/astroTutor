import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import pipeline_facts as p


class Tests(unittest.TestCase):
    def setUp(self):
        self.row=dict(id='12345678',level='B',question_hint='Perché osserviamo la luce?',
                      context='Il gas caldo emette luce. Il disco contiene gas caldo.')
        self.facts=p.resolve_facts(dict(usable=True,question=self.row['question_hint'],fact_ids=[1,2]),self.row)
        self.answer=dict(sentences=[dict(text='Il disco contiene gas caldo che emette luce.',fact_ids=[1,2])])
        self.resolved=p.resolve_answer(self.answer,self.facts)
        report=dict(sentences=[dict(index=1,supported=True,scientifically_correct=True,uncertain=False,
                    reason='La frase riprende i due fatti citati.')],all_facts_preserved=True,natural=True)
        self.judge=dict(question_answerable=True,in_astronomy_scope=True,answers=[copy.deepcopy(report),copy.deepcopy(report)],
                    preferred=2,substantial_pedagogical_difference=True,preferred_appropriate=True,
                    reason='Definisce il termine necessario per il profilo.')

    def test_exact_source_and_invalid_ids(self):
        self.assertTrue(all(f['text'] in self.row['context'] for f in self.facts['facts']))
        for ids in ([0],[3],[True],[1,1],[]):
            with self.assertRaises(ValueError):
                p.resolve_facts(dict(usable=True,question=self.row['question_hint'],fact_ids=ids),self.row)

    def test_uncovered_facts_fail(self):
        self.answer['sentences'][0]['fact_ids']=[1]
        with self.assertRaisesRegex(ValueError,'unreferenced_fact'):
            p.resolve_answer(self.answer,self.facts)

    def test_either_response_can_win(self):
        self.assertEqual(p.decision(self.judge,[self.resolved]*2,[0,1]),1)
        self.assertEqual(p.decision(self.judge,[self.resolved]*2,[1,0]),0)

    def test_missing_factual_check_fails(self):
        self.judge['answers'][1]['sentences']=[]
        with self.assertRaisesRegex(ValueError,'incomplete_factual_audit'):
            p.decision(self.judge,[self.resolved]*2,[0,1])

    def test_factual_failure_cannot_be_overridden_by_preference(self):
        self.judge['answers'][0]['sentences'][0]['supported']=False
        with self.assertRaisesRegex(ValueError,'factual_rejection'):
            p.decision(self.judge,[self.resolved]*2,[0,1])

    def test_four_steps_independent_answers(self):
        calls=[]
        variant=copy.deepcopy(self.answer)
        variant['sentences'][0]['text']='Il gas presente nel disco è caldo ed emette luce.'
        replies=iter([dict(usable=True,question=self.row['question_hint'],fact_ids=[1,2]),
                      self.answer,variant,self.judge])
        def chat(args,prompt,seed):
            calls.append((args.model,prompt));return next(replies)
        result=p.process(self.row,SimpleNamespace(chat=chat))
        self.assertEqual(result['status'],'auto_accepted')
        self.assertEqual([x[0] for x in calls],[p.AUTHOR]*3+[p.JUDGE])
        self.assertNotIn(self.answer['sentences'][0]['text'],calls[2][1])
        self.assertIn('Il gas caldo emette luce.',calls[1][1])
        self.assertIn('Il gas caldo emette luce.',calls[2][1])

    def test_cap_before_transport(self):
        c=p.Client.__new__(p.Client);c.count=30
        with self.assertRaisesRegex(RuntimeError,'30 richieste'):
            c.http('https://example.test')

    def test_503_retry_is_bounded(self):
        c=p.Client.__new__(p.Client);c.count=0
        with patch.object(p.transport.Client,'http',side_effect=RuntimeError('HTTP 503: capacity')) as call:
            with patch.object(p.transport.time,'sleep') as sleep:
                with self.assertRaises(RuntimeError):c.http('https://example.test')
                self.assertEqual(call.call_count,3)
                self.assertEqual([x.args[0] for x in sleep.call_args_list],[15,30])


if __name__=='__main__':unittest.main()
