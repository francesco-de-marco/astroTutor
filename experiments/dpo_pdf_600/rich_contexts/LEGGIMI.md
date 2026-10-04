# Nucleo comune e approfondimenti supportati

Il filtro locale ha individuato 121 candidati nello split TRAIN con indicatori di definizioni e relazioni causali. Il primo lotto di dodici conteneva ancora didascalie e passaggi inadatti: non va considerato validato. Dopo lettura dell'assistente è stato preparato selected_pack.json con cinque casi. Questa selezione è dell'assistente, non umana indipendente, e non prova la correttezza dei libri.

I cinque casi riguardano metodo osservativo, eclissi solare, stelle circumpolari, metodi per studiare le fusioni di oggetti compatti e osservazioni ultraviolette. La provenienza conserva i topic originali, che non sempre corrispondono al contenuto effettivo del chunk. Non usare i numeri di topic come prova di diversità tematica.

Per ogni domanda sono stati selezionati passaggi letterali dal PDF, con ID. Il nucleo obbligatorio deve essere conservato da entrambe le risposte; i passaggi facoltativi consentono definizioni e approfondimenti diversi. Nessuna aggiunta scientifica non supportata è autorizzata. Il nucleo è un requisito di contenuto, non un vincolo sulla lunghezza.

Il generatore riceve lo stesso insieme di fonti in due chiamate separate, con profili diversi. Il giudice diverso dal generatore controlla ogni frase, la conservazione del nucleo e poi la preferenza per il profilo obiettivo. Può vincere qualunque risposta. Un dettaglio in più o una diversa suddivisione in frasi non bastano da soli a rendere sostanziale la preferenza.

La verifica degli ID e della presenza delle citazioni è deterministica. Supporto semantico, correttezza scientifica e adeguatezza rimangono giudizi fallibili del modello. La selezione di contesti ricchi può essere distorta rispetto al corpus completo e non garantisce preferenze utili. I cinque casi sono diagnostici, non un test finale e non un campione rappresentativo.

## Prova limitata

Tre chiamate per caso (due risposte e un giudizio): massimo 15 richieste normali, tetto di 30 HTTP complessive inclusi errori/retry, persistente dopo riavvio. Cache e attese 429/503 riusano il componente della prova precedente. Nessuna produzione di 600 coppie o esportazione per training viene avviata automaticamente.

Usare run_rich_contexts.ps1 nella cartella superiore, -Mode smoke. -Mode summary non richiede la chiave. Le prove precedenti restano congelate. results.jsonl, summary.json, requests.jsonl e usage.jsonl descrivono questa prova separata.
