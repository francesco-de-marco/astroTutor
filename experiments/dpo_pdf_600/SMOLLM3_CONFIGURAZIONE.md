# Terzo modello: HuggingFaceTB/SmolLM3-3B

Scelto per includere una famiglia diversa da Qwen, dimensione circa 3B e supporto dichiarato per l'italiano. Selezione effettuata senza leggere le risposte dei test finali di Qwen. Documentazione: https://huggingface.co/HuggingFaceTB/SmolLM3-3B

Si usa la modalità senza extended thinking, tramite `enable_thinking=False` nel chat template, sia per i dati di training sia per l'inferenza base e DPO. Il flag viene registrato nei manifest. Non vengono alterati i file congelati di training e test. È una configurazione del template specifica del modello, da dichiarare nel confronto; non si sta valutando la sua modalità di ragionamento esteso.

Trainer e confronto sono copie separate degli script precedenti, con questa opzione aggiunta. Restano invariati epoche, learning rate, beta, LoRA, quantizzazione, seed e decoding. La versione Transformers installata contiene l'implementazione SmolLM3 e le proiezioni q/k/v/o usate da LoRA. Sintassi e integrazione del flag sono state controllate; il caricamento dei pesi e il training effettivo sulla GPU vengono verificati dallo smoke, non sono ancora attestati per questo modello.

`run_smollm3.ps1 -Mode all` esegue smoke, training e test in sequenza; si ferma al primo errore. Dopo un test interrotto, `-Mode test` riprende le risposte mancanti. Non riprende automaticamente un training incompleto: in quel caso occorre diagnosticare l'errore senza cancellare i risultati.

I risultati dei due Qwen sono conservati. Per Qwen 1.5B: 300 aggiornamenti, due epoche, 160 record di test, due segnalazioni di limite token. Questi controlli attestano completamento e integrità, non qualità delle risposte.
