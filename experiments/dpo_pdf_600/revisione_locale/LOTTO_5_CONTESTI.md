# Cinque contesti PDF: revisione locale prima delle API

Nessuna chiamata Groq usata per questa selezione. Questo è un lotto di progettazione, non un dataset DPO pronto e non una certificazione scientifica indipendente. Le domande sono proposte dall’assistente, non ancora testate su studenti.

I brani sono estratti letterali da chunk dello split TRAIN già congelato. Gli split development/test non sono stati usati. La selezione privilegia intenzionalmente prosa italiana leggibile: non rappresenta l’intero corpus. I livelli indicati sono proposte, non etichette validate.

## Metodo da seguire

1. Controllare questi cinque brani, le domande e i limiti prima di ogni altra generazione.
2. Scrivere un esempio di risposta adeguata e una alternativa corretta per un diverso profilo; verificare che la preferenza dipenda dal livello, non da errori.
3. Eseguire una sola prova API limitata soltanto dopo la revisione del lotto.
4. Ampliare le fonti e gli argomenti; mantenere documenti separati tra split. Non replicare coppie solo per arrivare a 600.

La raccolta automatica precedente non è validata: il giudice ha approvato anche spiegazioni assenti dal contesto. La selezione dei brani riduce alcuni problemi ma non rende affidabile da sola il giudice.

## 1. Eclissi lunari

**Domanda proposta:** Perché non si verifica un’eclissi di Luna ogni volta che c’è la Luna piena?

**Livelli candidati:** A, B, C

**Fonte:** Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi

PDF: `data/raw/TOPIC 4 - Evoluzione stellare e supernovae/B - Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi.pdf`

Chunk: `TOPIC 4 - Evoluzione stellare e supernovae\B - Stelle_pianeti e galassie viaggio nella storia dell’astronomia dall’antichità ad oggi.jsonl`, riga 13; ID `4b1fced439ffbe5f199f3de1`.

### Contesto da leggere

La Terra gira attorno al Sole e la Luna intorno alla Terra. Quando la Terra passa tra il Sole e la Luna e i tre corpi celesti sono ben allineati, il Sole illumina la Terra e l’ombra della Terra oscura la Luna. È l’eclissi totale di Luna. Durante l’eclissi, la Luna è necessariamente nella fase di Luna piena. Ma se il nostro satellite è nella fase di Luna piena una volta al mese, perché non si verifica un’eclissi di Luna con la stessa frequenza?  
Il motivo è che l’orbita della Luna è inclinata di cinque gradi rispetto all’orbita della Terra attorno al Sole. Quindi, la maggior parte delle volte in cui la Luna è piena, essa non si trova in linea con la Terra, ma sopra o sotto. L’eclissi totale si verifica solo quando Sole, Terra e Luna sono perfettamente allineati, e la Luna attraversa il piano dell’orbita della Terra. Se l’allineamento tra i tre corpi è buono, ma non perfetto, l’ombra della Terra oscura solo parte della Luna e l’eclissi si dice parziale.

### Cosa deve spiegare la risposta

Inclinazione dell’orbita; la Luna piena non basta: serve un allineamento favorevole.

### Limiti da controllare

Non attribuire le fasi lunari all’ombra della Terra. Non usare il calendario datato in fondo al chunk.

**Revisione indipendente:** da svolgere.

## 2. Lenti gravitazionali

**Domanda proposta:** Come può una grande massa aiutare a osservare una galassia lontana?

**Livelli candidati:** B, C

**Fonte:** Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi

PDF: `data/raw/TOPIC 4 - Evoluzione stellare e supernovae/B - Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi.pdf`

Chunk: `TOPIC 4 - Evoluzione stellare e supernovae\B - Stelle_pianeti e galassie viaggio nella storia dell’astronomia dall’antichità ad oggi.jsonl`, riga 146; ID `6b263d14d56e8a7287840924`.

### Contesto da leggere

La relazione tra spazio, tempo ed energia scoperta da Einstein prevede che la luce si propaghi in linea retta nello spazio vuoto, ma cambi percorso quando passa vicino a una grande concentrazione di materia.  
Si può così verificare la situazione in cui una galassia lontanissima sia allineata con una grande massa, per esempio un gruppo di galassie, e con la Terra. Una parte dei raggi di luce della galassia lontanissima, la sorgente, vengono “piegati” e fatti convergere dal gruppo di galassie, la lente, verso la Terra. L’effetto appena descritto si chiama “lente gravitazionale” perché è molto simile a quanto succede ai raggi di luce che passano attraverso la lente di un telescopio: entrano paralleli da una parte della lente, si piegano mentre passano attraverso il vetro per la rifrazione, ed escono dalla lente di nuovo in linea retta, ma non più paralleli, bensì convergenti in un punto detto fuoco. È proprio questa convergenza che permette di sfruttare la luce raccolta dalla lente e ricreare un’immagine luminosa nel fuoco. Grazie all’effetto di lente gravitazionale, gli astronomi hanno potuto osservare galassie lontanissime che, altrimenti, con i telescopi convenzionali non sarebbero riusciti a vedere. Quando gli astronomi sfruttano l’effetto di lente gravitazionale, è come se usassero un potentissimo “telescopio gravitazionale”.

### Cosa deve spiegare la risposta

La massa modifica il percorso della luce e, con geometria favorevole, può renderla più facilmente osservabile.

### Limiti da controllare

L’analogia con il vetro non significa che nello spazio avvenga rifrazione nel vetro; non generalizzare a qualunque allineamento.

**Revisione indipendente:** da svolgere.

## 3. Luminosità apparente

**Domanda proposta:** Perché una stella che ci appare debole potrebbe essere molto luminosa?

**Livelli candidati:** A, B, C

**Fonte:** Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi

PDF: `data/raw/TOPIC 4 - Evoluzione stellare e supernovae/B - Stelle_pianeti e galassie viaggio nella storia dellastronomia dallantichit ad oggi.pdf`

Chunk: `TOPIC 4 - Evoluzione stellare e supernovae\B - Stelle_pianeti e galassie viaggio nella storia dell’astronomia dall’antichità ad oggi.jsonl`, riga 71; ID `8733473b5275d518d00e1f84`.

### Contesto da leggere

Luminosità e diametro dei corpi celesti sono definiti “apparenti” perché li misuriamo dalla Terra. Talvolta siamo in grado di misurare la distanza di alcuni corpi celesti e in questi casi risaliamo alle loro proprietà fisiche intrinseche.  
Per esempio, la dimensione apparente del Sole in cielo è mezzo grado. Se fossimo su Giove che è circa 5 volte più lontano dal Sole rispetto alla Terra, la nostra stella avrebbe un diametro apparente di appena un decimo di grado. Siccome conosciamo la distanza tra il Sole e la Terra (150 milioni di chilometri), possiamo calcolare il diametro intrinseco del Sole che è di 1,4 milioni di chilometri. Anche le luminosità degli oggetti che osserviamo sono apparenti: tra due stelle debolmente luminose non sappiamo distinguere quale sia luminosissima ma molto distante e quale sia vicina ma molto più debole. Si può sperimentare questa caratteristica delle sorgenti luminose allontanandosi man mano da una lampadina accesa. La luminosità intrinseca della lampadina non cambia, ma la sua luce apparirà sempre più debole.

### Cosa deve spiegare la risposta

La luminosità osservata dipende anche dalla distanza; distinguere luminosità intrinseca e apparente.

### Limiti da controllare

Non ricavare distanze quantitative senza altre informazioni. Per A usare il caso della lampadina.

**Revisione indipendente:** da svolgere.

## 4. Pianeti erranti

**Domanda proposta:** Come si può rilevare un pianeta che non orbita intorno a una stella?

**Livelli candidati:** B, C

**Fonte:** Astrofisica per ansiosi (Licia Troisi)

PDF: `data/raw/TOPIC 4 - Evoluzione stellare e supernovae/C - Astrofisica per ansiosi (Licia Troisi).pdf`

Chunk: `TOPIC 4 - Evoluzione stellare e supernovae\C - Astrofisica per ansiosi (Licia Troisi).jsonl`, riga 86; ID `8ed63ed2cf3c7125d4c126c2`.

### Contesto da leggere

Un pianeta senza una stella è sostanzialmente un pianeta che non emette luce, se non quel po’ di calore residuo che ancora mantiene dalla sua formazione, e che causa una debole emissione infrarossa. Questo, in effetti, è uno dei sistemi con cui possiamo vedere indirettamente un pianeta errante.

### Cosa deve spiegare la risposta

Il calore residuo della formazione può produrre una debole emissione infrarossa.

### Limiti da controllare

Non affermare che ogni pianeta errante sia rilevabile. Spiegare infrarosso senza introdurre strumenti o meccanismi assenti.

**Revisione indipendente:** da svolgere.

## 5. Massa ed evoluzione stellare

**Domanda proposta:** Perché una stella più massiccia può raggiungere temperature adatte a ulteriori reazioni di fusione?

**Livelli candidati:** C, D

**Fonte:** Astrofisica per ansiosi (Licia Troisi)

PDF: `data/raw/TOPIC 4 - Evoluzione stellare e supernovae/C - Astrofisica per ansiosi (Licia Troisi).pdf`

Chunk: `TOPIC 4 - Evoluzione stellare e supernovae\C - Astrofisica per ansiosi (Licia Troisi).jsonl`, riga 98; ID `f3605615087a7d08df857f33`.

### Contesto da leggere

Stelle più grandi, invece, sono capaci di bruciare progressivamente i prodotti delle precedenti fasi evolutive. Questo è possibile proprio grazie alla loro grande massa, che significa anche maggiore forza di gravità. Le varie reazioni di fusione, infatti, richiedono via via quantitativi di energia, e quindi temperature, sempre più elevate. Questa energia è proprio fornita dalla gravità, che tende a far contrarre le parti centrali della stella causando l’innalzamento della densità e della temperatura.

### Cosa deve spiegare la risposta

Maggiore gravità, contrazione delle parti centrali, incremento di densità e temperatura.

### Limiti da controllare

Non dire che tutte le stelle seguano lo stesso destino; non introdurre soglie di massa o reazioni non presenti.

**Revisione indipendente:** da svolgere.
