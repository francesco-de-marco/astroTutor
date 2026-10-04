# AstroTutor — dataset DPO sintetico dai PDF, versione 1

Questo pacchetto permette di iniziare un esperimento riproducibile senza altre chiamate Groq. Le domande e le risposte sono state scritte dall'assistente sulla base di estratti dei PDF già elaborati dal progetto. Non sono state validate da un revisore umano indipendente.

## Che cosa contiene

| Quantità | Significato |
|---|---|
| 600 | Confronti DPO: prompt, risposta preferita, risposta rifiutata |
| 75 | Domande distinte, raggruppate in 25 nuclei tematici |
| 300 | Prompt distinti: ogni domanda ai livelli A, B, C, D |
| 150 per livello | Coppie DPO per ciascun livello |
| 300 | Negativi con errore fattuale intenzionale |
| 300 | Negativi corretti nel proprio argomento, ma estranei alla domanda |
| 6 | Documenti sorgente del corpus di training |

Le 600 coppie NON sono 600 domande indipendenti. Ogni domanda compare a quattro livelli; ogni prompt ha due risposte negative e una sola risposta preferita. Non sommare questi numeri per descrivere la diversità del dataset.

Gli argomenti comprendono eclissi, luce e distanze, spettroscopia, esopianeti, nascita ed evoluzione stellare, pulsar, galassie, materia oscura, espansione, lenti gravitazionali, abitabilità, nube di Oort, pianeti erranti e metodo osservativo.

## File da usare

- `train_dpo.jsonl`: 600 righe, formato conversazionale TRL con `prompt`, `chosen`, `rejected`. Il prompt contiene il profilo dello studente, un estratto documentale e la domanda. Le risposte sono messaggi `assistant`. Non contiene token specifici di Qwen o di altri modelli.
- `train_sft.jsonl`: 300 conversazioni `messages` con le sole risposte preferite, deduplicate rispetto ai due negativi. Consente un eventuale confronto SFT sugli stessi contenuti.
- `provenance.jsonl`: una riga per ogni riga DPO, nello stesso ordine. Contiene identificativi, fonte, famiglia di domanda, livello, criterio di preferenza e hash. Conservare questo abbinamento quando si rimescolano i dati.
- `contexts.json`: brani usati nei prompt, percorso del PDF nel progetto, file/riga del chunk e intervalli di caratteri nell'originale.
- `source_snapshot.json`: copia dei 25 chunk sorgente e identificativi delle fonti riservate. Permette la ricostruzione offline. Contiene anche testo NON selezionato per i prompt: non usarlo automaticamente come risposta corretta.
- `questions.json` e `content.py`: contenuti delle 75 domande; il campo `wrong` contiene errori VOLUTI, da non usare come riferimento scientifico.
- `LEGGIMI_DOMANDE.md`: elenco leggibile di domande e risposte semplici.
- `validation_report.json`: controlli strutturali; `manifest.json`: hash dei file.
- `build.py`: ricostruisce il pacchetto senza rete o chiavi API, con `python build.py` dalla sua cartella. Richiede soltanto Python e i file del pacchetto.

## Come sono costruite le preferenze

La risposta preferita risponde alla domanda e riprende il contenuto pertinente del brano. La versione A è accessibile e breve; B aggiunge una spiegazione; C combina terminologia precisa e spiegazione; D è più sintetica e tecnica. Questa trasformazione è controllata e limitata: non garantisce un adattamento perfetto a ogni età, né una profondità universitaria per tutte le domande elementari.

Il primo negativo introduce un errore intenzionale. Il secondo usa una risposta pertinente a una domanda di un altro nucleo tematico, allo stesso livello. Il suo argomento di origine è tracciato nei metadati. Non è un confronto tra due risposte equivalenti per correttezza e pertinenza che differiscono soltanto nello stile didattico.

Di conseguenza l'obiettivo principale è **correttezza e pertinenza in presenza di un contesto e di un profilo**. Il dataset non permette, da solo, di isolare il contributo del DPO all'adattamento al livello. Molti errori sono evidenti e alcuni negativi usano negazioni o affermazioni assolute: sono possibili scorciatoie stilistiche. Questo è un dataset sintetico controllato per il primo confronto, non un benchmark difficile o una prova di efficacia educativa.

## Fonti e verifiche

I brani sono selezionati come sottostringhe esatte dei chunk dei PDF già presenti nel corpus. Non sono state aggiunte fonti web né usati i candidati precedentemente scartati dai generatori Groq. Alcuni estratti sono in inglese; le risposte sono in italiano. Gli offset si riferiscono al chunk, non alla pagina del PDF: il pacchetto non inventa numeri di pagina.

I testi originali possono contenere semplificazioni, refusi OCR o affermazioni datate. La selezione e la scrittura delle risposte hanno evitato diversi passaggi problematici, ma il controllo esatto delle citazioni NON equivale a una verifica scientifica indipendente. Il report distingue esplicitamente i due aspetti.

Sono controllati conteggi, unicità delle coppie, differenza chosen/rejected, corrispondenza dei brani ai chunk e assenza di sovrapposizione fra le fonti usate e quelle riservate nel precedente split per documento. Le sei fonti usate sono elencate in `validation_report.json`.

## Uso nel confronto fra modelli

1. Congelare questi file e conservare `manifest.json`. Usare le stesse 600 righe per ciascun modello, applicando il rispettivo chat template una sola volta. Non concatenare i messaggi con marcatori proprietari prima di passarli al trainer.
2. Fare un controllo della lunghezza tokenizzata con OGNI tokenizer e un breve test di training. Non troncare alla cieca contesto o risposta. Questa consegna non ha ancora eseguito i training sui diversi modelli.
3. Per studiare il DPO, confrontare ogni modello iniziale con il suo adattamento DPO. Se si include SFT, distinguere base, SFT, DPO diretto e SFT+DPO: per attribuire un guadagno al DPO dopo SFT, il confronto è SFT contro SFT+DPO.
4. Costruire sviluppo e test separatamente dalle fonti riservate. Questo pacchetto contiene SOLO training. Non dividere casualmente le 600 righe: copie per livello e per negativo renderebbero la valutazione contaminata. Non usare i vecchi prompt del pilot ripetutamente osservati come test finale.
5. Valutare risposte generate dai modelli, con gli stessi contesti e condizioni, su domande nuove. Misurare separatamente correttezza, pertinenza e adeguatezza al livello; mantenere cieca l'identità del modello nel giudizio. Riportare variabilità e numerosità delle domande indipendenti, non soltanto medie.

Non è corretto concludere che il DPO sia universalmente utile o inutile da questo solo esperimento. Un risultato nullo documenta il comportamento dei modelli, dati e impostazioni provati. Miglioramenti dell'apprendimento degli studenti richiederebbero uno studio dedicato.

## Condivisione

Il pacchetto incorpora estratti dei PDF del progetto: verificare i relativi diritti prima di pubblicarlo in una repository pubblica. Per la riproducibilità interna conservare anche il corpus e la sua versione originale.
