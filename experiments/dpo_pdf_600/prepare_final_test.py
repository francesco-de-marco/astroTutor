"""Freeze a shared, source-disjoint test before model generation. No APIs."""
import json
import hashlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'dataset_consegna'))
from build import SYSTEM, LEVELS

# Contexts are explicitly labelled assistant paraphrases, not verbatim PDF quotations.
SPECS=[
('aac5247b74c8c4c3ddc7a744','Osservazioni infrarosse',
 'Le stelle appena formate possono essere nascoste nelle nubi di gas e polvere rimaste dalla loro formazione. La polvere assorbe gran parte della luce visibile e riemette energia nell’infrarosso. La radiazione infrarossa attraversa queste nubi con attenuazione minore rispetto al visibile. Osservare nell’infrarosso è quindi utile per studiare regioni di formazione stellare oscurate alla vista.',[
 ('Perché una stella nascosta dalla polvere nella luce visibile può essere studiata nell’infrarosso?', 'La polvere ostacola maggiormente il visibile; l’infrarosso è meno attenuato e consente di studiare la regione. Non attribuire il fenomeno alla scomparsa della polvere.'),
 ('L’energia della luce visibile assorbita dalla polvere viene semplicemente distrutta?', 'No: la polvere può riemettere energia nell’infrarosso. Distinguere assorbimento e riemissione dalla distruzione dell’energia.')]),
('4d7d0668ba9cfe537a40abc6','Gas vicino ai buchi neri',
 'Un buco nero può disgregare una stella che passa troppo vicino attraverso le forze di marea, prima che il materiale attraversi l’orizzonte degli eventi. Il gas proveniente da stelle disgregate o da nubi non cade necessariamente in modo indisturbato: interagisce con altro materiale. Durante l’accrescimento, energia potenziale gravitazionale può essere convertita in calore e radiazione. La radiazione considerata qui è prodotta dal materiale esterno all’orizzonte.',[
 ('Quale trasformazione energetica può rendere luminoso il gas che si avvicina a un buco nero?', 'Conversione di energia potenziale gravitazionale in calore e radiazione del gas. Non confondere con luce che esce dall’interno dell’orizzonte.'),
 ('La luce del gas attorno a un buco nero dimostra che qualcosa sta sfuggendo dall’interno dell’orizzonte?', 'No. Nel meccanismo descritto la radiazione nasce nel materiale ancora esterno all’orizzonte.')]),
('14105d95ad8e68c235dff254','Centro di massa',
 'La Terra e la Luna orbitano entrambe attorno al loro centro di massa comune, chiamato baricentro. Nel sistema Terra-Luna questo punto si trova all’interno della Terra, ma non coincide con il suo centro. Per descrivere con maggiore precisione il moto del sistema intorno al Sole si considera il baricentro Terra-Luna. Il moto della Terra comprende quindi anche il suo movimento attorno a questo punto comune.',[
 ('Nel sistema Terra-Luna, la Terra rimane perfettamente ferma mentre soltanto la Luna orbita?', 'No: entrambe orbitano attorno al baricentro comune. Il fatto che esso sia interno alla Terra non lo rende il suo centro né annulla il moto terrestre.'),
 ('Che cosa rappresenta il baricentro del sistema Terra-Luna?', 'Il centro di massa comune attorno a cui si muovono entrambi i corpi; è interno alla Terra ma distinto dal suo centro.')]),
('db6c38c2de6b59a887429abf','Periodi delle orbite',
 'Il brano confronta i tempi di percorrenza di orbite intorno alla Terra: una bassa orbita, come quelle citate per la Stazione spaziale internazionale e Hubble, richiede circa novanta minuti; alla distanza della Luna il periodo è circa un mese. A una distanza intermedia si può avere un periodo pari alla rotazione terrestre, approssimativamente ventiquattro ore. Un satellite geostazionario opportunamente collocato appare fermo rispetto alla superficie ed è utile come ripetitore di comunicazioni. Il solo valore del periodo, senza le altre condizioni orbitali, non è qui una descrizione completa di qualsiasi orbita.',[
 ('Un satellite in orbita bassa impiega necessariamente un giorno per girare attorno alla Terra?', 'No: gli esempi di orbita bassa impiegano circa novanta minuti; il periodo di circa un giorno appartiene a una diversa distanza orbitale.'),
 ('Perché un satellite che appare fermo rispetto al terreno è utile per le comunicazioni?', 'Può servire da ripetitore mantenendo la stessa posizione apparente rispetto alla superficie. Apparire fermo non significa smettere di orbitare.')]),
('67204f86fa1d36ca2e7a9980','Spettro e temperatura stellare',
 'La luce di una stella può essere separata nelle sue componenti di colore, ottenendo uno spettro. Per la componente termica della radiazione, la distribuzione relativa dell’intensità nei diversi colori è legata alla temperatura dell’oggetto che emette. Lo spettro permette quindi di stimare la temperatura di una stella anche quando essa appare come un punto non risolto. Negli spettri stellari possono inoltre comparire righe di assorbimento, cioè deficit di luce a specifiche lunghezze d’onda. Questa descrizione distingue la distribuzione termica dalle singole righe.',[
 ('Come possiamo stimare la temperatura di una stella senza distinguerne il disco?', 'Analizzando la distribuzione dell’intensità nei colori del suo spettro termico. Non occorre misurarne direttamente la forma.'),
 ('Nello spettro di una stella, una riga di assorbimento significa che manca tutta la sua luce?', 'No: indica una riduzione a una specifica lunghezza d’onda, non l’assenza di emissione in tutto lo spettro.')]),
('c50039b4433ac77bf5934e25','Formazione delle strutture cosmiche',
 'Nel quadro cosmologico descritto, piccole differenze iniziali di densità crescono fino a formare strutture. All’inizio la materia ordinaria è fortemente accoppiata ai fotoni: la pressione della radiazione ostacola il suo collasso gravitazionale. La materia oscura non subisce lo stesso ostacolo e può cominciare prima a formare concentrazioni gravitazionali. La materia ordinaria può successivamente cadere in queste concentrazioni. Le due componenti non hanno quindi la stessa evoluzione iniziale.',[
 ('Perché la materia ordinaria non può inizialmente collassare nello stesso modo della materia oscura nel quadro descritto?', 'L’accoppiamento ai fotoni e la pressione della radiazione ostacolano il collasso della materia ordinaria; la materia oscura non ha lo stesso vincolo.'),
 ('Che ruolo possono avere le concentrazioni di materia oscura nella successiva distribuzione della materia ordinaria?', 'Creano concentrazioni gravitazionali in cui può cadere la materia ordinaria. Non significa che materia oscura e ordinaria siano la stessa sostanza.')]),
('01d57b3e9e7dda8ffa4e101f','Trasparenza dell’universo',
 'Nell’universo primordiale caldo, elettroni e protoni non sono ancora legati in atomi neutri. La radiazione interagisce frequentemente con il plasma, perciò la luce non viaggia liberamente per grandi distanze. Con il raffreddamento, elettroni e protoni possono combinarsi formando soprattutto idrogeno neutro: questa fase è chiamata ricombinazione. L’universo diventa molto più trasparente e la radiazione può propagarsi più liberamente. La radiazione cosmica di fondo osservata oggi risale a questa fase di disaccoppiamento.',[
 ('Perché la formazione di atomi neutri rende l’universo più trasparente?', 'Diminuisce l’interazione frequente della radiazione con il plasma di cariche libere; i fotoni possono propagarsi più liberamente. Non perché cominci a esistere la luce.'),
 ('La ricombinazione indica la distruzione degli atomi di idrogeno oppure la loro formazione?', 'La formazione di atomi prevalentemente di idrogeno neutro dall’unione di elettroni e protoni, favorita dal raffreddamento.')]),
('1560a2cdb66264e6db96e858','Riconoscimento dei segnali gravitazionali',
 'Per estrarre un segnale di onde gravitazionali dal rumore si possono confrontare i dati con molti modelli di forma d’onda. Simulazioni complete di relatività numerica sono importanti per descrivere la fusione dei buchi neri, ma produrre un numero enorme di modelli usando soltanto queste simulazioni è molto costoso. Il brano propone di usare i risultati numerici per guidare e controllare la costruzione di modelli analitici, combinando descrizioni delle diverse fasi del segnale.',[
 ('Perché non costruire ogni modello di segnale gravitazionale usando soltanto una simulazione numerica completa?', 'Perché occorrono molti modelli e il costo delle simulazioni complete è elevato. Ciò non rende le simulazioni inutili o scientificamente scorrette.'),
 ('Usare modelli analitici dei segnali gravitazionali significa rinunciare ai risultati delle simulazioni numeriche?', 'No: i risultati numerici possono guidare e controllare i modelli analitici; i due approcci sono complementari.')]),
('dfead31d24e27a07ad19d1a0','Percorsi nell’interferometro',
 'In una versione dell’interferometro, un divisore separa un fascio luminoso in due parti e le invia in direzioni perpendicolari. Ciascuna parte raggiunge uno specchio, torna al divisore e viene ricombinata con l’altra. La luce ricombinata viene analizzata per rilevare piccole differenze fra i due percorsi. Il brano presenta questo apparato nel contesto storico della ricerca dell’etere, senza che descrivere l’ipotesi storica significhi dimostrarne l’esistenza.',[
 ('Quale percorso seguono le due parti del fascio nell’interferometro descritto?', 'Si separano, percorrono direzioni perpendicolari, vengono riflesse dagli specchi e tornano a ricombinarsi nel divisore.'),
 ('In questo apparato, gli specchi servono a creare due nuove sorgenti luminose indipendenti?', 'No: riflettono due parti della stessa luce iniziale verso il divisore, dove esse si ricombinano.')]),
('1335abb14617ce136f84d9b8','Vento solare e aurore',
 'Il Sole emette nello spazio un flusso di particelle cariche, tra cui elettroni, protoni e nuclei di elio. Questo flusso è chiamato vento solare. L’interazione di particelle energetiche con l’atmosfera terrestre, soprattutto vicino alle regioni polari magnetiche, può produrre aurore. La luce emessa dall’atmosfera presenta colori legati alle specie coinvolte e alle loro transizioni energetiche. Il vento solare è dunque un flusso di particelle, distinto dalla sola luce visibile del Sole.',[
 ('Il vento solare è un vento d’aria come quello che sentiamo sulla Terra?', 'No: è un flusso di particelle cariche emesso dal Sole; non un movimento di aria terrestre.'),
 ('La luce di un’aurora nasce semplicemente dalla riflessione della luce solare su una nuvola?', 'No: è prodotta dall’interazione di particelle energetiche con l’atmosfera e dalle emissioni delle specie coinvolte.')]),
]

def digest(b):return hashlib.sha256(b).hexdigest()
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 rows=json.loads((ROOT/'dataset_v5'/'contexts_test.json').read_text(encoding='utf-8'))
 byid={r['id']:r for r in rows}
 excluded=set()
 for name in ('train','development'):
  excluded.update(r['source_group'] for r in json.loads((ROOT/'dataset_v5'/f'contexts_{name}.json').read_text(encoding='utf-8')))
 sources=[];prompts=[];number=0
 for ident,topic,context,questions in SPECS:
  r=byid[ident];assert r['source_group'] not in excluded
  sources.append({'id':ident,'topic':topic,'source_group':r['source_group'],'source_file':r['source_file'],
   'chunk_file':r['chunk_file'],'chunk_line':r['chunk_line'],'original_context':r['context'],
   'evaluation_context':context,'context_kind':'assistant_paraphrase_not_verbatim'})
  for question,reference in questions:
   number+=1
   for level,profile in LEVELS.items():
    prompts.append({'id':f'test{number:02}_{level}','question_id':f'test{number:02}',
     'topic':topic,'question':question,'level':level,'group':r['source_group'],'source_id':ident,
     'reference_points':reference,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':
      f'Profilo: {profile}\n\nContesto:\n{context}\n\nDomanda: {question}'}]})
 assert len(prompts)==80 and number==20
 data={'split':'test','human_validated':False,'unique_questions':20,'context_kind':'assistant_paraphrase_not_verbatim',
  'note':'20 domande, 10 brani, quattro livelli. Valutazione della generazione con contesti controllati; non misura retrieval o apprendimento degli studenti.',
  'sources':sources,'prompts':prompts}
 target=ROOT/'test_common_v1.json'
 if target.exists():assert json.loads(target.read_text(encoding='utf-8'))==data,'Test già congelato: non sovrascrivere.'
 else:save(target,data)
 save(ROOT/'test_common_v1_manifest.json',{'version':'test_common_v1','sha256':digest(target.read_bytes()),
  'questions':20,'topics':10,'prompts':80,'generations_per_model_comparison':160,
  'source_groups':sorted({p['group'] for p in prompts}),'human_validated':False,
  'training_source_overlap':False,'development_source_overlap':False,
  'context_policy':'Italian assistant paraphrases with retained originals; same input for every model',
  'training_protocol':{'epochs':2,'learning_rate':5e-6,'beta':0.1,'lora_r':8,'lora_alpha':16,
   'effective_batch':4,'seed':42,'quantization':'NF4 double quant BF16'},
  'evaluation_policy':'No training/prompt changes based on this test; same frozen inputs across models; report failures and regressions.'})
 code=(ROOT/'compare_dpo_600.py').read_text(encoding='utf-8')
 changes={
 "Confronto di sviluppo NF4 base/LoRA: 32 prompt, 8 nuove domande.":"Test comune NF4 base/LoRA: 80 prompt, 20 domande congelate.",
 "dataset = read(source)":"dataset = read(source)\n    frozen = read(source.with_name('test_common_v1_manifest.json'))\n    if hashlib.sha256(source.read_bytes()).hexdigest() != frozen['sha256']:\n        raise ValueError('Test modificato dopo il congelamento.')",
 "dataset['split'] != 'development'":"dataset['split'] != 'test'",
 "Atteso sviluppo, non test finale.":"Atteso test comune congelato.",
 "Contaminazione train/development.":"Contaminazione train/test.",
 "len(rows)!=32 or len({r['question_id'] for r in rows})!=8":"len(rows)!=80 or len({r['question_id'] for r in rows})!=20",
 "Conteggi sviluppo inattesi.":"Conteggi test inattesi.",
 "Trentadue prompt: otto domande per quattro livelli da tre documenti di sviluppo.":"Ottanta prompt: venti domande per quattro livelli, dieci brani con contesti riformulati in italiano.",
 "Le varianti di livello non sono osservazioni indipendenti. Non è il test finale.":"Le varianti di livello non sono osservazioni indipendenti. Non usare questi risultati per adattare training o prompt.",
 "development_600_v1.json":"test_common_v1.json",
 "qwen3b_development_v1":"qwen3b_test_v1",
 }
 for old,new in changes.items():
  assert old in code,old
  code=code.replace(old,new)
 compile(code,'compare_test_600.py','exec')
 (ROOT/'compare_test_600.py').write_text(code,encoding='utf-8')
 print('TEST CONGELATO: 20 domande, 80 prompt, 160 risposte per modello base/DPO.')
 print('Documenti:',len({p['group'] for p in prompts}))
if __name__=='__main__':main()
