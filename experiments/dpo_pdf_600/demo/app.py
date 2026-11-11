import json
import os
os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
import streamlit as st
from backend import TutorService,MODELS,LEVELS,available_models,result_summary,EXPERIMENT

st.set_page_config(page_title='AstroTutor',page_icon='🔭',layout='wide')

@st.cache_resource
def service():return TutorService()

st.title('AstroTutor')
st.write('Esplora l’astronomia con spiegazioni adatte al tuo livello e fonti consultabili.')
with st.sidebar:
    st.header('La tua spiegazione')
    level=st.selectbox('Livello',list(LEVELS),index=1,format_func=lambda x:f'{x} · {LEVELS[x]}')
    labels=available_models()
    selected=st.selectbox('Modello',labels or ['Nessun modello disponibile'])
    mode_label=st.radio('Risposta', ['DPO','Base','Confronto affiancato'])
    mode={'DPO':'dpo','Base':'base','Confronto affiancato':'compare'}[mode_label]
    with st.expander('Opzioni'):
        count=st.select_slider('Fonti da consultare',options=[1,2,3],value=3)
        st.caption('Il primo caricamento può richiedere qualche minuto. I modelli vengono letti dalla cache locale.')
        if st.button('Libera memoria del modello'):
            service().unload();st.success('Modello scaricato dalla memoria.')
    if st.button('Cancella la conversazione'):
        st.session_state['records']=[];st.rerun()
    st.caption('Ogni domanda è trattata separatamente. Il tutor non ricorda il contenuto delle domande precedenti.')

tutor,results,about=st.tabs(['Chiedi al tutor','Risultati dell’esperimento','Il progetto'])

def show_record(record):
    with st.chat_message('user'):st.write(record['question'])
    with st.chat_message('assistant'):
        st.caption(f"{record['model'].split('/')[-1]} · {LEVELS[record['level']]} · {record['elapsed_seconds']:.1f} s")
        if record.get('no_sources'):
            st.info('Non ho trovato fonti per questa domanda e questo livello. Prova a riformulare la domanda.')
        else:
            answers=record['answers']
            containers=st.columns(2) if len(answers)==2 else [st.container()]
            for box,(side,answer) in zip(containers,answers.items()):
                with box:
                    st.subheader('Modello base' if side=='base' else 'Modello con DPO')
                    st.markdown(answer['text'] or 'Il modello non ha prodotto una risposta.')
                    if answer['token_limit']:st.caption('La risposta ha raggiunto il limite di lunghezza e potrebbe essere incompleta.')
            with st.expander(f"Fonti recuperate ({len(record['docs'])})"):
                st.caption('Sono i brani forniti al modello; la loro presenza non garantisce la correttezza di ogni affermazione.')
                for i,doc in enumerate(record['docs'],1):
                    st.markdown(f"**{i}. {doc['title']}**")
                    st.caption(f"Livello della fonte: {doc.get('level','—')} · {doc.get('level_match','')}")
                    st.write(doc['text'])

with tutor:
    st.caption('Demo locale sui documenti indicizzati. Puoi confrontare base e DPO usando esattamente gli stessi brani.')
    st.session_state.setdefault('records',[])
    if not st.session_state['records']:
        st.info('Prova: «Come nasce una stella?» oppure «Perché la luce non può uscire da un buco nero?»')
    for record in st.session_state['records']:show_record(record)
    question=st.chat_input('Scrivi una domanda di astronomia',max_chars=1500,disabled=not labels)
    if question:
        try:
            with st.spinner('Cerco nei documenti e preparo la risposta…'):
                record=service().answer(question,level,MODELS[selected],mode,count)
            st.session_state['records'].append(record)
            st.rerun()
        except Exception as exc:
            st.error('Non è stato possibile completare la risposta.')
            st.caption('Verifica che indice e pesi siano presenti. Se manca memoria GPU, chiudi altri modelli in esecuzione e riprova con Qwen 1.5B.')
            with st.expander('Dettaglio per la risoluzione del problema'):st.code(str(exc))
    if st.session_state['records']:
        st.download_button('Scarica domande, risposte e fonti',json.dumps(st.session_state['records'],ensure_ascii=False,indent=2),file_name='astrotutor_sessione.json',mime='application/json')

with results:
    st.header('Base e DPO su sei modelli')
    data=result_summary()
    if data:
        a,b,c=st.columns(3);a.metric('Modelli',len(data['models']));b.metric('Risposte valutate',data['responses']);c.metric('Domande distinte',20)
        st.caption('Valutazione automatica con GPT-OSS 120B. Test congelato: 20 domande × 4 livelli; nessuna revisione umana indipendente.')
        table=[]
        for m in data['models']:
            table.append({'Modello':m['model'].split('/')[-1],
                'Corrette base /80':m['base']['correctness'].get('C',0),
                'Corrette DPO /80':m['dpo']['correctness'].get('C',0),
                'Adeguatezza base (0–2)':m['base']['adequacy'],
                'Adeguatezza DPO (0–2)':m['dpo']['adequacy']})
        st.dataframe(table,hide_index=True,width='stretch')
        for name in ['07_correctness.png','09_quality_dimensions.png']:
            p=EXPERIMENT/'results'/'figures'/name
            if p.exists():st.image(str(p),width='stretch')
        st.write('La correttezza migliora in cinque modelli su sei, ma l’adeguatezza didattica non migliora uniformemente. Il test non misura l’apprendimento degli studenti.')
    else:st.info('Il riepilogo del test non è presente in questa installazione.')

with about:
    st.header('Dai documenti alla risposta')
    st.write('AstroTutor recupera brani dalla raccolta di astronomia, li riordina per pertinenza e li fornisce a un modello linguistico insieme al livello richiesto. Il DPO modifica il modello tramite esempi di risposte preferite e rifiutate.')
    st.write('Questa interfaccia carica gli adapter effettivamente addestrati. Base significa adapter disattivato; DPO significa adapter attivo sullo stesso modello. Non serve una chiave Groq per fare domande.')
    st.caption('La demo usa ricerca live con query italiana e il prompt RAG del progetto. Non riproduce il test congelato, che usa contesti già fissati. I guardrail non sono applicati al confronto live. I modelli possono sbagliare: consulta le fonti.')
