"""Offline audit gate. Does not call APIs or modify the completed experiment."""
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent


def pedagogical_preference(judge, order):
    """Return original answer index, never assume the target-profile answer wins."""
    required = ('preferred_appropriate', 'both_natural', 'question_conceptual',
                'substantial_pedagogical_difference')
    if sorted(order) != [0, 1]:
        raise ValueError('invalid answer order')
    preferred = judge.get('preferred')
    if type(preferred) is not int or preferred not in (1, 2):
        return None
    if not all(judge.get(k) is True for k in required):
        return None
    return order[preferred - 1]


def factual_gate(review, answers, context):
    """Validate structured evidence, NOT semantic entailment or scientific truth.

    A separate verifier must assess every answer span. Full non-whitespace
    coverage avoids silently dropping the unsupported part of an answer.
    Quotes must be literal source spans. A valid report remains an AI judgment.
    """
    if not isinstance(review, dict) or review.get('uncertain') is not False:
        return False
    groups = review.get('answers')
    if not isinstance(groups, list) or len(groups) != 2:
        return False
    for answer, group in zip(answers, groups):
        claims = group.get('claims') if isinstance(group, dict) else None
        if not isinstance(claims, list) or not claims:
            return False
        covered = set()
        for claim in claims:
            if not isinstance(claim, dict):
                return False
            start, end = claim.get('start'), claim.get('end')
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(answer):
                return False
            if claim.get('text') != answer[start:end]:
                return False
            if claim.get('supported') is not True or claim.get('scientifically_correct') is not True:
                return False
            quotes = claim.get('source_quotes')
            if not isinstance(quotes, list) or not quotes:
                return False
            if any(not isinstance(q, str) or len(q.strip()) < 15 or q not in context for q in quotes):
                return False
            covered.update(range(start, end))
        if any(i not in covered for i, char in enumerate(answer) if not char.isspace()):
            return False
    return True


def replay():
    attempts = [json.loads(s) for s in (ROOT/'attempts.jsonl').read_text(encoding='utf-8').splitlines()]
    audit = json.loads((ROOT/'AUDIT_LOCALE.json').read_text(encoding='utf-8'))['accepted_audit']
    output = []
    for row in attempts:
        judge = row.get('judge') or {}
        order = [0, 1]
        random.Random(int(row['id'][:8], 16) % 2147483647).shuffle(order)
        preferred = pedagogical_preference(judge, order)
        content_keys = ('question_answerable', 'answer1_correct', 'answer2_correct',
                        'answer1_grounded', 'answer2_grounded', 'evidence_supports_both')
        status = 'rejected_by_existing_judgment'
        if preferred is not None and all(judge.get(k) is True for k in content_keys):
            status = 'needs_separate_factual_review'
        if row['id'] in audit:
            status = 'quarantined_by_local_audit'
        output.append(dict(id=row['id'],preferred_original_index=preferred,
                           status=status,local_audit=audit.get(row['id']),
                           training_ready=False))
    (ROOT/'replay_quality_gate.json').write_text(json.dumps(output, ensure_ascii=False, indent=2),encoding='utf-8')
    from collections import Counter
    print(json.dumps(dict(Counter(r['status'] for r in output)),ensure_ascii=False))
    print('No API calls. Original labels and accepted.jsonl unchanged.')


if __name__ == '__main__':
    replay()
