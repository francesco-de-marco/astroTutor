"""UI checks with a saved real record; no additional model/API generation."""
import json,sys,os,tempfile
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1]/'demo'
sys.path[:0]=[str(HERE/'.packages'),str(HERE)]
(HERE/'.tmp').mkdir(exist_ok=True)
tempfile.tempdir=str(HERE/'.tmp')
from backend import TutorService,validate_question,adapt_messages
from streamlit.testing.v1 import AppTest

for invalid in ('','  ','x'*1501):
    try:validate_question(invalid,'B')
    except ValueError:pass
    else:raise AssertionError('invalid input accepted')
assert adapt_messages([{'role':'system','content':'s'},{'role':'user','content':'u'}],
    'merge_system_into_first_user')==[{'role':'user','content':'s\n\nu'}]
record=json.loads((HERE/'qa_live.json').read_text(encoding='utf8'))
with patch.object(TutorService,'answer',return_value=record) as answer:
    a=AppTest.from_file(str(HERE/'app.py'),default_timeout=60).run()
    assert not a.exception
    assert len(a.selectbox[1].options)==6
    a.radio[0].set_value('Confronto affiancato').run()
    a.chat_input[0].set_value('Come nasce una stella?').run()
    assert not a.exception
    assert len(a.session_state['records'])==1
    assert answer.call_args.args[3]=='compare'
    assert [m.value for m in a.metric]==['6','960','20']
    assert any('Fonti recuperate (2)' in e.label for e in a.expander)
    assert len(a.get('download_button'))==1
    [b for b in a.button if b.label=='Cancella la conversazione'][0].click().run()
    assert a.session_state['records']==[] and not a.exception
print('UI OK: controls, comparison rendering, sources, export, clearing; invalid input rejected.')
