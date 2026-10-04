"""AI review recorded against numbered answers before reading comparison_key.json.
Not independent human validation. No model or API judge was run.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# C: correct central answer, no substantial identified error; P: partial/ambiguous;
# I: wrong central answer or major error in the explanation. Language assessed in notes.
RAW='''
dev01_A|I|I|t|Entrambe impongono uguaglianza dei tempi vissuti; la seconda si contraddice anche internamente.
dev01_B|P|I|1|La prima nega correttamente la necessità ma poi dice che l'età totale rimane la stessa; la seconda afferma uniformità del tempo per tutti.
dev01_C|I|I|t|Entrambe rispondono sì erroneamente; la seconda aggiunge una falsa simultaneità universale.
dev01_D|I|I|t|Entrambe negano la possibile differenza dei tempi propri.
dev02_A|C|C|t|Entrambe distinguono correttamente tempo proprio vissuto e confronto con un altro percorso; differenza didattica non decisiva.
dev02_B|P|I|1|La prima conclude correttamente ma contiene 10ml anni e relazionismo; la seconda separa erroneamente tempo proprio ed età.
dev02_C|P|P|t|Nucleo corretto in entrambe, con spiegazioni ambigue sull'invarianza del tempo totale e sull'accelerazione del tempo vicino al buco nero.
dev02_D|P|C|2|La seconda mantiene il nesso orologio-invecchiamento; la prima aggiunge una spiegazione confusa della differenza di età dei gemelli.
dev03_A|C|C|t|Entrambe collegano la caduta alla variazione della gravità con la distanza; velocità al posto di accelerazione è una semplificazione da migliorare.
dev03_B|P|C|2|La seconda esplicita l'accelerazione maggiore vicino al centro; la prima usa velocità di accelerazione e devia sul caso tangenziale. La legge inversa quadratica della seconda è conoscenza aggiuntiva non esplicitata nel brano.
dev03_C|P|P|t|Entrambe colgono la non uniformità ma usano tides; la prima generalizza accelerazioni non parallele, la seconda è ripetitiva e confonde termini.
dev03_D|I|I|t|Entrambe inventano termini elettromagnetici/elettromotrici; la prima aggiunge una spiegazione falsa su ombre, mari e fiumi.
dev04_A|P|C|2|La seconda offre una semplificazione utile delle differenze di caduta; la prima aggiunge coordinate non più rette prive di spiegazione fisica.
dev04_B|P|I|1|La prima conserva il criterio di precisione pur con accelerazioni tangenti imprecise; la seconda introduce un centro di gravità della regione e un criterio scorretto.
dev04_C|P|I|1|La prima conserva il confronto con l'accuratezza sperimentale; la seconda inventa una forza tangenziale tra le parti come spiegazione generale.
dev04_D|P|P|t|Entrambe riconoscono la variazione del campo e la precisione, ma confondono il fenomeno con accelerazioni tangenziali.
dev05_A|C|C|t|Entrambe citano caduta libera e piccola regione. Restano astratte per la primaria; la seconda ripete la definizione senza chiarirla.
dev05_B|P|C|2|La prima sostituisce la caduta libera con un generico moto uniforme iniziale; la seconda mantiene la condizione fisica essenziale.
dev05_C|P|P|t|Entrambe sostituiscono la caduta libera con corpo pesante; la seconda aggiunge ripetizioni e un'affermazione confusa sull'estensione globale al limite di volume nullo.
dev05_D|P|C|2|La seconda include caduta libera e località; la prima usa corpo pesante e propone una motivazione impropria.
dev06_A|I|I|t|Risposta iniziale no corretta, ma entrambe inventano la ragione: impossibilità di cadere in un punto o negazione delle diverse direzioni di caduta.
dev06_B|C|P|1|La prima enuncia correttamente il limite locale, pur senza svilupparne il meccanismo; la seconda dà una motivazione confusa su oggetti lontani e contemporanei.
dev06_C|I|I|t|La prima introduce regione infinita e velocità di rotazione; la seconda attribuisce alla relatività speciale un vincolo locale della relatività generale.
dev06_D|P|I|1|La prima dà una risposta sostanzialmente pertinente ma tautologica e linguisticamente imprecisa; la seconda attribuisce il limite alla relatività speciale.
dev07_A|I|I|t|La prima usa il movimento del legno come conversione della massa; la seconda attribuisce la produzione stellare all'espansione e raffreddamento.
dev07_B|P|I|1|La prima presenta il legame ma corrompe il fattore quadratico in cattiva quadrata; la seconda inventa una velocità minima di trasferimento massa-energia.
dev07_C|P|P|t|La prima chiama fattore la velocità senza specificare il quadrato nella spiegazione; la seconda identifica inizialmente c² con la velocità e si corregge solo dopo.
dev07_D|P|C|2|La seconda espone l'equivalenza con c al quadrato; la prima ripete l'affermazione impropria sulle stelle dal momento del Big Bang presente nel contesto.
dev08_A|C|C|t|Entrambe identificano c correttamente; introducono dettagli ulteriori ma non necessari rispetto al contesto.
dev08_B|C|C|t|Entrambe identificano c; la seconda contiene aggiunte non necessarie. Nessun vantaggio fattuale netto.
dev08_C|P|C|2|La seconda è precisa; l'ultima frase della prima confonde il coefficiente e il quadrato con formulazione ambigua.
dev08_D|P|C|2|La seconda risponde senza deviazioni; la prima aggiunge una distinzione fuorviante sull'applicabilità di E=mc² all'energia stellare.
'''
records=[]
for line in RAW.strip().splitlines():
 ident,s1,s2,pref,note=line.split('|',4)
 records.append({'id':ident,'answer_1':s1,'answer_2':s2,'preference':pref,'reason':note})
assert len(records)==32 and len({r['id'] for r in records})==32
payload={'reviewer':'AI assistant, same assistant involved in dataset design',
 'independent_human_review':False,'blinded_to_answer_mapping_at_annotation':True,
 'rubric':{'C':'Nucleo corretto senza errori sostanziali individuati; ammesse semplificazioni minori',
 'P':'Risposta parziale, ambigua o con imprecisioni rilevanti',
 'I':'Nucleo errato oppure errore grave nella spiegazione'},
 'preference_rule':'Preferenza prudente per correttezza e chiarezza; t include entrambe sbagliate. Non è una misura isolata di adattamento al livello.',
 'records':records}
(ROOT/'review_blind.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Salvati 32 giudizi numerati; nessuna lettura della chiave.')
