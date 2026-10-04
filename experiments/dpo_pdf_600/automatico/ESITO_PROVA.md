# Esito della prova automatica — 20 contesti

Analisi locale dell’assistente, non revisione umana indipendente. Nessuna nuova chiamata API.

## Conteggi

{
  "pedagogical_or_other_failure": 5,
  "content_or_support_failure": 5,
  "accepted_by_judge": 5,
  "opposite_preference": 3,
  "context_unsuitable": 2
}

57 richieste HTTP complessive. 5 accettazioni del giudice su 20 (25%); A=1, B=2, C=2, D=0. Questa percentuale non misura la correttezza delle coppie né l’efficacia del DPO.

## Esame delle cinque accettazioni

### cd886398909fba9b992f5924

La chosen aggiunge nuovi mutanti e contiene una nota tecnica (evidenza: [1]); la rejected dice prima che le nicchie scompaiono e poi che rimangono vuote. Coppia non pronta. Domanda biologica da valutare rispetto al dominio astronomico.

### 23374ac9b0a1ca82527f9994

Entrambe aggiungono il filtraggio/diffusione selettiva dei colori, non spiegato nel brano. La chosen usa rifratta senza definirlo per A. Non soddisfa il vincolo rigoroso di supporto adottato.

### 407ec6707fb6579efec634ba

La rejected introduce forza di galleggiamento e la prevalenza del trasferimento per convezione non esplicitate nel brano. Domanda sul forno: manca un collegamento astronomico. Da riesaminare, non promuovere.

### 166895efdf2d2cbac9ccfa8f

Le risposte aggiungono grande cerchio e generalizzano la rappresentazione delle geodetiche senza qualificare la proiezione. Contrasto didattico debole: entrambe spiegano il passaggio sfera/mappa. Non promuovere senza revisione.

### 6fefdf9a5155093443714c9a

Entrambe introducono conservazione del flusso e spiegazioni non presenti nel brano. La chosen dice superficie diminuisce di volume; la rejected equipara il principio magnetico a quello gravitazionale. Non pronta per training.

## Preferenza inversa

Tre coppie superano tutti i booleani del giudice ma sono scartate perché la seconda risposta è preferita. Il programma imponeva che vincesse quella generata per il profilo obiettivo. È un criterio troppo restrittivo per raccogliere preferenze osservate: in una prossima versione il giudice dovrebbe poter assegnare chosen a una qualunque delle due risposte. Non si può però trasformare retroattivamente questa osservazione in una validazione di quelle tre coppie. Il file separato conserva le proposte senza cambiare i risultati originali.

## Decisione

Non ampliare questo generatore a 600 coppie sulla base del 25%. Nessuna delle cinque accettazioni è qui promossa a coppia validata. Nessun file di training è stato modificato. La selezione deve controllare il dominio astronomico; il giudizio sul supporto va distinto dal gradimento didattico e deve localizzare le affermazioni non sostenute. Verificare qualsiasi nuovo controllo prima sui record e sulla cache già presenti, senza altra generazione.
