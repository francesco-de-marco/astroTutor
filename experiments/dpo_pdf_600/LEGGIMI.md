# DPO dai PDF di AstroTutor

Richiesta recepita: tornare a domande fondate sui PDF gia presenti nella base documentale, con circa 600 coppie comuni ai modelli. Il lotto NASA e la sua revisione non sono prerequisiti di questa raccolta.

## Cosa viene prodotto

- 600 triplette di TRAIN: 150 per livello A/B/C/D, con domanda, contesto originale, chosen e rejected.
- 80 triplette separate di sviluppo: 20 per livello, aggiuntive alle 600.
- Contesti PDF riservati al test; le domande finali e il relativo runner devono ancora essere costruiti. Non sono gia un test completo.
- Titolo e percorso PDF, file e riga del chunk, hash, autore, evidenze testuali, motivo della preferenza, controllo automatico e log degli scarti.

Le 600 sono l'obiettivo delle coppie accettate automaticamente, non il numero di coppie gia create. Se i candidati non bastano, il programma si ferma sotto quota e lo dichiara. Non replica esempi per raggiungere il numero.

Il dataset salva messaggi di conversazione neutri. Ciascun modello applichera il proprio tokenizer/chat template in training; nessun token speciale di Qwen e inserito nei testi comuni. Lo stesso export congelato sara riusato per tutte le famiglie. Gli script del vecchio pilot vanno ancora adattati al nuovo schema e ai nuovi percorsi: non passare direttamente l'export al vecchio trainer assumendo compatibilita completa.

## Coerenza col progetto originale

Si riutilizzano corpus, chunk e metadati. La domanda viene costruita dal contesto del PDF, come richiesto. In questa raccolta il contesto viene selezionato PRIMA della domanda e mantenuto fisso; non si riesegue il retrieval globale dopo la domanda, per evitare di pescare documenti degli split riservati. La valutazione end-to-end del retrieval rimane un esperimento distinto.

Il vecchio generatore piu recente costruiva invece domande da topic e poi cercava documenti. Mischiava coppie di registro, allucinazione e fuori dominio. Qui la raccolta principale isola l'adeguatezza al livello: entrambe le alternative devono essere corrette e supportate. Non si inventano 120 domande fuori dominio dentro le 600 basate sui PDF. Un eventuale benchmark di rifiuto va conservato separatamente.

Chosen e rejected vengono scritte dallo stesso teacher per evitare che autore e qualita coincidano sistematicamente. Una seconda chiamata, con ordine delle risposte randomizzato, controlla sufficienza del contesto, correttezza, grounding e presenza di una differenza didattica sostanziale. Il generatore rifiuta anche risposte identiche, citazioni di evidenza assenti dal brano e domande esattamente duplicate. I pareggi e i disaccordi non entrano nell'export.

Questo screening usa lo stesso modello che ha scritto gli esempi: NON e una revisione indipendente e NON certifica la correttezza. Gli esempi restano etichettati auto_screened_not_human_validated. Per la discussione scientifica va controllato anche un campione; non viene qui imposto un ulteriore blocco legato alle vecchie 12 coppie.

## Separazione delle fonti

Il piano verificato contiene 17.743 righe PDF prima dei filtri e 31 gruppi di libri dopo deduplicazione e filtri: 20 train, 5 sviluppo, 6 test. Libri duplicati con lo stesso titolo e le traduzioni riconosciute di George sono raggruppati; chunk testuali identici presenti in libri diversi sono esclusi. Il controllo non riconosce automaticamente tutte le traduzioni o parafrasi. La separazione e per documento, non una promessa di generalizzazione a temi sconosciuti.

I livelli richiesti sono assegnati separatamente dal livello del PDF: una fonte avanzata puo contenere concetti semplici. Il teacher deve scartare i brani inadatti. La quantita di materiale per livello e argomento nel corpus e sbilanciata; i riepiloghi devono renderlo visibile.

## Stato del 25 settembre

La prima prova locale su Qwen2.5 7B ha esaminato 10 candidati: 0 accettati. Gli scarti sono conservati in dataset_v1, una prova preliminare da non usare per training. Il nuovo piano dataset_v3 corregge anche l'assegnazione dei livelli, che ora varia casualmente fra chunk anziche dipendere dalla posizione del libro nel giro di campionamento.

Non e stata inviata alcuna richiesta ai servizi cloud durante questa preparazione. Per la generazione su vasta scala serve scegliere un teacher adeguato: endpoint compatibile OpenAI (come Groq, usato originariamente) oppure il modello cloud gia disponibile in Ollama, con consenso all'invio dei contesti. Il percorso locale resta disponibile, ma il primo esito non giustifica una produzione massiva senza ulteriori prove.

## Comandi (PowerShell)

Lo script usa la libreria standard: nessuna reinstallazione necessaria. Impostare i percorsi una volta:

```powershell
$dpoScript = 'C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\build_dataset.py'
$dpoData = 'C:\Users\matti\Documents\Codex\2026-09-09\com\outputs\dpo_pdf_600\dataset_v3'
```

Il piano dataset_v3 e gia preparato. Non rilanciare prepare sulla stessa cartella.

La prima prova del teacher scelto usa generate con --max-attempts 12. Dopo la verifica del campione si rilancia lo stesso comando senza --max-attempts, mantenendo modello e parametri. Riprende dai file salvati. Per lo sviluppo si aggiunge --split development.

Opzioni del servizio:

- Locale: `--provider ollama --model qwen2.5:7b --url http://localhost:11434`.
- Ollama cloud, solo dopo aver scelto questo servizio: `--provider ollama --model gpt-oss:120b-cloud --url http://localhost:11434 --allow-cloud`.
- Groq, dopo avere impostato ORACLE_API_KEY nel proprio ambiente: `--provider openai --model openai/gpt-oss-120b --url https://api.groq.com/openai/v1 --allow-cloud`. Non incollare la chiave in chat. Disponibilita e quote dell'account vanno verificate prima della produzione.

Non cambiare teacher nella stessa cartella: il manifest blocca la mescolanza di configurazioni. Per un teacher diverso preparare una nuova cartella con prepare, stesso seed e stesso corpus. Non avviare due generatori sullo stesso output. Una chiusura forzata del processo puo lasciare generation.lock: va rimosso soltanto dopo aver verificato che nessun generatore stia usando la cartella.

Quando train e sviluppo sono completi:

```powershell
python $dpoScript export --out $dpoData
```

Export non parte se mancano le quote per livello. Conservare manifest e log insieme ai dataset. Prima di pubblicare in una repository pubblica, ricordare che i record includono brani dei PDF originali: l'export locale non equivale a un'autorizzazione alla loro redistribuzione.

## Prova Groq e revisione del generatore

La prova Groq in dataset_v2 ha prodotto 8 scarti e 0 accettazioni, poi HTTP 429 (8000 TPM). I log e lo snapshot del generatore sono conservati. dataset_v3 mantiene identici contesti e split, ma riparte con istruzioni piu esplicite su citazioni letterali e rejected corrette. Il lanciatore usa GPT-OSS 120B. I controlli non sono stati allentati. Retry 429: massimo 5, rispettando retry-after numerico o attesa indicata nel messaggio; attese oltre 120 secondi interrompono per consentire una ripresa successiva. Lo screening resta non indipendente.

## Revisione attiva: dataset_v4

Il lanciatore usa dataset_v4. dataset_v3 resta archiviato con snapshot del generatore. Conteggi: {"context_unsuitable": 3, "evidence_not_in_context": 6, "accepted": 2, "judge_quality_rejection": 1}. Le due accettazioni automatiche non sono importate: risposte artificiali e prerequisiti non spiegati nel campione.

Contesti e split invariati. Il modello sceglie evidence_ids; il codice estrae i passaggi originali. Il giudice verifica anche adeguatezza della preferita, naturalezza, domanda concettuale e supporto delle evidenze a entrambe le risposte. Lo screening non e indipendente e non certifica la correttezza. Nuovo smoke necessario prima della produzione.

## Revisione attiva: dataset_v5

V4: 12 tentativi, 1 accettato automaticamente. La revisione del record de49ef4d2eaca90567caced5 trova una spiegazione sul disturbo della misura assente dal contesto. Non promuovere quella coppia come validata. Tutti i log e lo snapshot del codice V4 sono conservati.

V5 cambia il metodo: prima chiamata domanda e risposta per il profilo richiesto; seconda chiamata risposta alla stessa domanda per un profilo diverso, senza mostrare la prima risposta o richiedere difetti. Mappa profili A->D, B->D, C->A, D->B. Terza chiamata: controllo e confronto in ordine randomizzato rispetto al profilo richiesto. Si accetta solo se il giudice conferma la prima risposta come preferita e tutti i criteri. Pareggi e disaccordi si scartano. Il contrasto salvato deriva dal giudizio, non da una presunta differenza inventata dal generatore.

Modello unico GPT-OSS 120B: chiamate separate NON significa valutazione indipendente. Le coppie cross-profile possono essere troppo facili: misurare questo limite e includere in futuro casi piu vicini tra livelli. Numero di chiamate fino a 3 per candidato, oltre eventuali retry. Contesti e split restano identici, nessuna coppia precedente importata. Le prime 12 domande sono diagnostiche, non test finale. Prima della produzione verificare altri candidati e un campione manualmente.
