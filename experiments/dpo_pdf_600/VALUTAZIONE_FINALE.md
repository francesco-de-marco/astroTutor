# Valutazione finale — istruzioni

I sei training e i 960 output del test sono completi. Nessun nuovo training o download e richiesto.

## Stato del giudice

La prova locale con Qwen 2.5 7B ha superato sei controlli elementari ma ha fallito la successiva ispezione qualitativa dell'assistente: motivazioni scientifiche errate, mancato riconoscimento di una relazione causale invertita e voti di adeguatezza troppo generosi. La prova e stata fermata dopo sei giudizi, conservati con `manual_quality_review.json`; NON sono risultati finali e NON si mescolano con quelli Groq. Questo controllo e dell'assistente, non umano indipendente.

La procedura successiva usa `openai/gpt-oss-120b` su Groq, con output strutturato. I testi delle domande, i contesti, i punti di riferimento e le risposte vengono inviati a Groq. Le etichette del modello e base/DPO non vengono inviate. Non vengono inviate chiavi in file o argomenti della riga di comando. Si applicano le quote e gli eventuali costi del proprio account API.

## Comandi PowerShell

Controllo locale senza chiave e senza richieste Groq:

```powershell
& "C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\run_final_evaluation.ps1" -Mode check
```

Valutazione completa (chiave Groq richiesta nel terminale con input nascosto):

```powershell
& "C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\run_final_evaluation.ps1" -Mode all
```

Prima esegue nove controlli di correttezza e adeguatezza; se non passano, si ferma. Poi valuta 952 risposte uniche in 160 lotti fino a sei risposte. Otto copie identiche per lo stesso prompt riutilizzano il voto. Una risposta identica a un livello diverso NON riutilizza il voto. Le risposte del lotto vengono valutate separatamente; il raggruppamento puo comunque introdurre effetti di confronto e non li elimina del tutto.

La procedura registra ogni giudizio, hash dei dati, impostazioni, identificativo del modello restituito dal servizio e token consumati. Ritenta limiti brevi e problemi transitori; si ferma sui limiti giornalieri o dopo errori ripetuti. Rilanciare lo stesso comando riprende i giudizi mancanti. Tetto persistente: 650 richieste, inclusi tentativi falliti. Non aumentarlo alla cieca.

`-Mode smoke` limita la prova a tre lotti, oltre ai controlli iniziali; `-Mode summary` ricrea il report dai giudizi salvati senza chiamare Groq. Nessun modello viene scaricato. Il processo deve restare aperto e il PC non deve sospendersi.

## Output

Cartella `evaluation/final_groq_v1`:

- `progress.json`: avanzamento, distinto da completamento.
- `api_usage.json`: richieste e token conteggiati sulle risposte API ricevute; errori senza risposta possono non avere consumo noto.
- `judgments/`: voti e motivazioni del giudice, riprendibili.
- `summary.json`, `REPORT.md`, `REPORT.html`, `correctness.png`: prodotti SOLO a valutazione completa.
- `human_review.md`: 24 coppie per una revisione umana cieca, con contesto e fonte originale. Non e una revisione gia effettuata.
- `human_review_key.json`: chiave da consultare soltanto dopo i giudizi umani.

La preferenza base/DPO e derivata dai voti in ordine lessicografico: correttezza, completezza, adeguatezza, chiarezza. Non e un voto separato del giudice. Le parita sono mantenute. Gli intervalli bootstrap raggruppano per dieci contesti, non per 960 risposte indipendenti.

## Cosa possiamo concludere

Questa e una stima automatica con un solo giudice: controlli iniziali superati non garantiscono affidabilita scientifica o pedagogica. Verificare almeno un campione prima di presentare conclusioni forti. Gli output sono tutti conservati, anche al limite token. Non selezionare solo i miglioramenti.

Il confronto riguarda base vs DPO, non SFT vs DPO. Le 600 coppie sintetiche derivano da 75 domande; le risposte rifiutate includono errori e fuori tema. Il test non isola l'adattamento pedagogico, non misura retrieval RAG e non misura apprendimento degli studenti. Nessuna ottimizzazione sui risultati del test.

Fonte tecnica per gli output strutturati: https://console.groq.com/docs/structured-outputs
