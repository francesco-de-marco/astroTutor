import unittest
from quality_gate import factual_gate, pedagogical_preference


class GateTests(unittest.TestCase):
    def test_either_answer_can_win(self):
        j = dict(preferred=2, preferred_appropriate=True, both_natural=True,
                 question_conceptual=True, substantial_pedagogical_difference=True)
        self.assertEqual(pedagogical_preference(j, [0, 1]), 1)
        self.assertEqual(pedagogical_preference(j, [1, 0]), 0)
        j['preferred'] = 0
        self.assertIsNone(pedagogical_preference(j, [0, 1]))

    def test_missing_or_invented_evidence_fails(self):
        answer = 'Il gas caldo emette luce.'
        claim = dict(start=0,end=len(answer),text=answer,supported=True,
                     scientifically_correct=True,source_quotes=[answer])
        report = dict(uncertain=False,answers=[{'claims':[claim]},{'claims':[claim]}])
        self.assertTrue(factual_gate(report,[answer,answer],answer))
        self.assertFalse(factual_gate(None,[answer,answer],answer))
        self.assertFalse(factual_gate(report,[answer+' Un altro fatto.',answer],answer))
        claim['source_quotes'] = ['Una citazione che non esiste.']
        self.assertFalse(factual_gate(report,[answer,answer],answer))


if __name__ == '__main__':
    unittest.main()
