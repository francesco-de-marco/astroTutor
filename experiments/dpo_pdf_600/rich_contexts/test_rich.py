import unittest
import run_rich as r


class Tests(unittest.TestCase):
    def setUp(self):
        self.row={'facts':[{'id':1,'text':'Il gas caldo emette luce.'},
                           {'id':2,'text':'La luce viene osservata dalla Terra.'}],
                  'core_fact_ids':[1]}

    def test_optional_can_be_omitted(self):
        result=r.answer_check({'sentences':[{'text':'Il gas caldo emette luce.', 'fact_ids':[1]}]},self.row)
        self.assertIn('gas caldo',result['text'])

    def test_core_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError,'missing_core_fact'):
            r.answer_check({'sentences':[{'text':'La luce arriva alla Terra.', 'fact_ids':[2]}]},self.row)

    def test_invented_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown_fact'):
            r.answer_check({'sentences':[{'text':'Il gas caldo emette luce.', 'fact_ids':[1,99]}]},self.row)

    def test_new_core_judgment_required(self):
        a={'sentences':[{'text':'Il gas caldo emette luce.'}]}
        report={'sentences':[{'index':1,'supported':True,'scientifically_correct':True,'uncertain':False,
                             'reason':'Testo supportato dalla fonte.'}], 'natural':True,'core_preserved':True}
        j={'question_answerable':True,'in_astronomy_scope':True,'answers':[report,report],
           'preferred':2,'substantial_pedagogical_difference':True,'preferred_appropriate':True,
           'reason':'Definizione utile e corretta per il profilo.'}
        self.assertEqual(r.decide(j,[a,a],[0,1]),1)
        report.pop('core_preserved');report['all_facts_preserved']=True
        with self.assertRaisesRegex(ValueError,'facts_not_preserved'):r.decide(j,[a,a],[0,1])


if __name__=='__main__':unittest.main()
