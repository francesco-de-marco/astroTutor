# Estensione a sei modelli

Richiesta dell'utente: aggiungere Llama, Gemma e Mistral, senza eseguire Phi. I modelli già completati sono Qwen2.5-3B-Instruct, Qwen2.5-1.5B-Instruct e SmolLM3-3B. Non sono stati selezionati i nuovi modelli sulla base dei risultati di qualità del test finale.

| Runner | Modello | Note |
|---|---|---|
| run_llama.ps1 | meta-llama/Llama-3.2-3B-Instruct | Accesso gated Hugging Face |
| run_gemma.ps1 | google/gemma-3-1b-it | Accesso gated; versione testuale piccola |
| run_mistral.ps1 | mistralai/Mistral-7B-Instruct-v0.3 | 7B, maggior carico GPU; fattibilità da verificare nello smoke |

Ogni runner accetta `-Mode all`, `smoke`, `train`, `test`. `all` esegue le fasi in sequenza e si ferma al primo errore. I file completi nella cache non vanno cancellati in caso di problemi di download. È supportato il rilancio di un run fermo con il solo manifest prima della creazione del trainer. Un training già avviato non viene sovrascritto automaticamente. Il test salva ogni risposta e può riprendere quelle mancanti.

Restano invariati dataset, test, epoche, learning rate, beta, rank LoRA, seed, quantizzazione e limite di generazione. Le dimensioni dei modelli e il numero di parametri LoRA risultante possono differire: non si tratta di un confronto a uguale capacità o costo. Per Gemma e Mistral il testo del messaggio system è anteposto al primo messaggio user, in modo identico nel training e nell'inferenza; Llama mantiene i ruoli nativi. Questa differenza di serializzazione viene registrata come `message_policy` nei manifest. I file congelati non vengono modificati.

Controllati sintassi, dati, conservazione delle istruzioni e identità della trasformazione fra training e inferenza. Le implementazioni installate includono le proiezioni q/k/v/o e il supporto logits_to_keep. Nessun training di queste tre famiglie è ancora stato eseguito. Gli smoke devono verificarne il funzionamento effettivo; in particolare non si garantisce a priori la memoria sufficiente per Mistral.

Accesso: effettuare personalmente la richiesta/accettazione dei termini sulle pagine ufficiali Llama e Gemma. Autenticarsi localmente con `hf auth login` usando un token autorizzato a leggere i modelli gated. Non inserire token negli script o nella documentazione. Non sono necessarie chiavi Groq.

Fonti:
- https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
- https://huggingface.co/google/gemma-3-1b-it
- https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3

Con tutti e sei i modelli completati: 6 confronti base/DPO, 80 prompt per confronto, 960 risposte complessive. Il test resta composto da 20 domande, non da 960 osservazioni indipendenti.
