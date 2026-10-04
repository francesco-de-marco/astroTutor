# Prova: stessi fatti, spiegazioni diverse

Questa è una prova diagnostica limitata, non una produzione di 600 coppie.

1. GPT-OSS seleziona da una a quattro frasi originali del PDF e una domanda che sia risolvibile usando tali frasi. Le frasi sono estratte dal codice, mai ricopiate dal modello.
2. GPT-OSS risponde per il profilo richiesto usando solo i fatti selezionati. Ogni frase della risposta elenca gli ID che dovrebbero sostenerla.
3. Una chiamata distinta produce una risposta per un altro profilo, dagli stessi fatti, senza vedere la prima risposta.
4. Qwen controlla il supporto e la correttezza di ogni frase, la conservazione di tutti i fatti e poi l'adeguatezza didattica. Qualunque delle due risposte può vincere; i pareggi si scartano.

Il codice controlla identificativi, copertura e completezza delle valutazioni. La verifica semantica resta affidata a un modello: non è una prova di verità e può fallire. Non viene chiesta revisione umana all'utente. La denominazione corretta è dataset sintetico sottoposto a controllo automatico; mai validazione umana indipendente.

## Perimetro e budget

Cinque estratti già selezionati localmente, tutti dallo split TRAIN. Livelli B, C, A, C, D. La prova verifica il metodo e non è rappresentativa del corpus. I contenuti sono stati già osservati dall'assistente e non possono diventare test finale.

Al massimo 20 chiamate normali (quattro per contesto) e un tetto assoluto di 30 richieste HTTP totali, errori e retry inclusi. I riavvii non azzerano il contatore. Ogni richiesta ha un tetto di 4096 token di output: il limite di richieste non è un preventivo di costo. Il consumo riportato dal provider è in usage.jsonl; gli errori possono non riportarlo.

La cache permette di riprendere le fasi già completate senza rigenerarle. Attesa minima fra richieste di 12 secondi; retry limitati per 429 e 503. Un errore del servizio lascia il contesto incompleto e riprendibile; un difetto del contenuto viene registrato come scarto. Non esistono cicli automatici di riscrittura per forzare l'accettazione.

La configurazione e i moduli usati sono congelati con hash. I risultati delle prove precedenti non sono modificati né importati. results.jsonl contiene risposte, fatti, valutazioni e indice della preferita. summary.json riepiloga l'esito. Non viene creato automaticamente alcun export per training né avviata una produzione estesa.

## Esecuzione

Usare il nuovo lanciatore run_facts_first.ps1 nella cartella superiore con -Mode smoke. Chiede la chiave Groq nascosta e la conserva solo temporaneamente nell'ambiente del processo. -Mode summary mostra i conteggi senza chiedere la chiave. Non avviare più processi insieme. La presenza del modello nell'elenco del provider non garantisce disponibilità in tempo reale.
