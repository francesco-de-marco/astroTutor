# Esito facts-first: cinque contesti

20 richieste, 5 contesti completati, 2 accettazioni automatiche (A e B), 3 rifiuti didattici (C, C, D). Nessuno scarto fattuale registrato dal giudice. Nessuna chiamata nuova per questa analisi locale.

Il 40% è il tasso di accettazione di questo lotto, non una misura di accuratezza e non confrontabile direttamente con il 25% della precedente prova: contesti, dimensione del campione e metodo sono diversi. Non è stato eseguito alcun nuovo training DPO.

## Cosa abbiamo appreso

La procedura esegue correttamente selezione delle frasi, due riscritture separate e controllo per frase. Su questi esempi le risposte conservano più visibilmente un nucleo comune. Non possiamo concludere che il problema delle allucinazioni sia risolto: il giudice accetta anche formulazioni imprecise.

La principale differenza tra risposte è ora sintattica: dividere una spiegazione in più frasi. Questo aiuta talvolta la leggibilità ma non dimostra una forte calibrazione dei prerequisiti e della profondità per livello scolastico. Richiedere esattamente gli stessi fatti e vietare ogni spiegazione aggiuntiva restringe deliberatamente il tipo di adattamento osservabile.

## Revisione locale dell’assistente (non indipendente)

### 4b1fced439ffbe5f199f3de1

Contenuto molto simile: preferenza motivata soprattutto da frasi separate. Entrambe usano lunazioni e piano terrestre senza chiarirli per B; il fatto 5 selezionato è una domanda, non una proposizione fattuale autonoma.

### 6b263d14d56e8a7287840924

Entrambe riportano la stessa spiegazione con minime differenze di organizzazione. Il rifiuto non è un guasto da eliminare.

### 8733473b5275d518d00e1f84

La prima è più accessibile per A. Tuttavia solo apparente può suggerire irrealtà e cioè dipende dalla distanza non è una definizione completa di luminosità apparente. Il contenuto principale è riconoscibile, ma la coppia non va chiamata validata.

### 8ed63ed2cf3c7125d4c126c2

Le risposte differiscono quasi soltanto per la divisione in frasi. La contrapposizione luce/infrarosso riprende inoltre una formulazione ambigua della fonte: la fedeltà non basta a garantire precisione.

### f3605615087a7d08df857f33

Nessuna differenza didattica sostanziale. Il giudice approva temperature forniscono energia pur riconoscendo nella motivazione che la formulazione è imprecisa. La verifica resta permissiva.

## Decisione operativa

Conservare questa prova come diagnostica e non avviare le 600 coppie né training sulle due accettazioni. Non rigenerare questi stessi cinque contesti. Le tre equivalenze sono risultati utili e non vanno trasformate artificialmente in preferenze.

Prima di una raccolta estesa serve fissare l’obiettivo: qui stiamo misurando principalmente leggibilità a contenuto costante. Per il tutor adattivo originale servono contesti più ricchi con definizioni e passaggi causali espliciti, da cui produrre risposte con spiegazioni diverse ma affermazioni tutte supportate. Il vincolo da mantenere è la correttezza/supporto, non l’identità di tutti i dettagli. Questa revisione metodologica deve essere dichiarata, non nascosta come semplice correzione tecnica.

Gli output originali e le etichette restano invariati. Nessuna coppia è stata promossa a validazione umana o a test finale.
