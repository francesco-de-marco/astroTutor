# Test comune AstroTutor, versione 1

Congelato il 26 settembre 2026 prima di generare risposte su questi prompt. File: `test_common_v1.json`, checksum in `test_common_v1_manifest.json`.

## Campione e obiettivo

20 domande, due per ciascuno di dieci nuclei tematici, a quattro livelli: 80 prompt. Ogni modello viene confrontato prima e dopo DPO, per 160 risposte. Le quattro fonti documentali non appartengono né allo split train né allo sviluppo. Gli argomenti possono sovrapporsi a quelli del training: il test riguarda nuove domande e nuovi brani, non argomenti totalmente mai incontrati.

I contesti sono riformulazioni italiane dell'assistente, non citazioni letterali dei PDF. Gli estratti originali, il percorso sorgente e la riga del chunk sono conservati. Le riformulazioni eliminano passaggi estranei, refusi e alcune semplificazioni fuorvianti. Sono state controllate dall'assistente, non da un revisore indipendente. Gli stessi contesti italiani sono usati per ogni modello: questo distingue il test dal primo sviluppo, prevalentemente con contesti inglesi. Non confrontare direttamente le percentuali dei due insiemi come se fossero lo stesso test.

Si valuta la risposta con contesto controllato. Non si misura il recupero dei documenti del RAG, né il progresso dell'apprendimento degli studenti. Il campione resta piccolo e in parte composto da domande semplici di definizione o correzione di un equivoco.

## Condizioni fissate

- Identici dataset DPO e prompt fra modelli; chat template proprio di ogni modello.
- Training previsto: due epoche, beta 0,1, learning rate 0,000005, LoRA r=8/alpha=16, batch effettivo 4, seed 42. Revisioni dei pesi e configurazioni effettive registrate per ogni run.
- Inferenza: base e adapter sullo stesso modello NF4, BF16, greedy decoding, massimo 384 nuovi token, repetition penalty 1, nessun guardrail o retrieval variabile.
- Le risposte attese in `reference_points` aiutano la valutazione, ma NON vengono passate al modello: vengono inviate esclusivamente le liste `messages`.
- Nessun checkpoint selezionato, modifica del prompt o riaddestramento in base a questo test. Se si modifica la procedura a seguito degli output, il test diventa sviluppo e occorre un altro test.
- Le differenze necessarie per compatibilità di una famiglia di modelli devono essere documentate. Stesse epoche non significano identico costo computazionale o ricerca ottimale degli iperparametri.

## Rubrica da applicare prima di aprire la chiave

Valutare ciascuna risposta separatamente, senza dedurre la qualità dalla lunghezza o dal modello.

1. Correttezza: C = nucleo corretto e nessun errore sostanziale; P = parziale/ambiguo/imprecisioni rilevanti; I = nucleo errato o errore grave nella spiegazione.
2. Pertinenza e completezza: 0 = non risponde; 1 = risponde solo in parte; 2 = copre gli elementi essenziali della domanda. Non richiedere tutte le nozioni del contesto per una domanda specifica.
3. Adeguatezza al livello: 0 = fortemente inadatta; 1 = parzialmente adatta; 2 = adatta. A richiede parole accessibili e concetti spiegati; B meccanismo comprensibile e definizioni dei termini nuovi; C passaggi causali e terminologia pertinente; D precisione e limiti senza premesse superflue. Non imporre formule o maggiore lunghezza quando non aiutano la risposta.
4. Chiarezza: 0 = confusa/contraddittoria; 1 = comprensibile con difetti; 2 = chiara e coerente.

Registrare sempre una motivazione breve e gli errori concreti. Segnalare separatamente dettagli aggiunti non sostenuti dal brano, distinguendoli da informazioni scientificamente false. Una risposta scientificamente corretta può usare una formulazione diversa dai punti attesi. I punti attesi non sono un matching lessicale.

Preferenza complessiva: prima errori sostanziali, poi completezza/pertinenza, infine adeguatezza e chiarezza. Sono ammesse parità e casi in cui entrambe sono inadeguate. Una preferenza complessiva non è una misura isolata di adattamento didattico.

## Resoconto

Riportare conteggi C/P/I, punteggi per dimensione e livello, preferenze, parole medie e segnalazioni di troncamento. Conservare anche risposte vuote o troncate senza eliminarle selettivamente dal confronto. Segnalare eventuali regressioni.

Le 80 righe derivano da 20 domande e dieci brani: non sono 80 osservazioni indipendenti. Se si stimano intervalli d'incertezza, raggruppare almeno per domanda, preferibilmente per nucleo/brano, dichiarando il numero limitato di gruppi e di fonti. Non presentare differenze descrittive come significative senza un'analisi appropriata.

Una valutazione dell'assistente deve essere dichiarata IA e non indipendente, soprattutto perché lo stesso assistente ha scritto i dati. Il file cieco può essere revisionato da un'altra persona senza consultare `comparison_key.json`. L'assenza di tale revisione va riportata, non sostituita con una falsa etichetta di validazione umana.

## Comando per Qwen

```powershell
& "C:\Users\matti\Documents\astroTutor\.venv-gpu\Scripts\python.exe" "C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\compare_test_600.py"
```

Il programma salva dopo ciascuna risposta e riprende i record mancanti quando si rilancia con la stessa configurazione. L'output di Qwen è in `evaluation/qwen3b_test_v1`. Per altri modelli usare `--training-dir` e una `--output-dir` distinta; il run di training deve registrare il modello e la revisione corretti e lo stesso dataset.
