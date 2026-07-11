# Information Retrieval

Created: October 1, 2025 11:40 PM

[Documenti](https://app.notion.com/p/Documenti-32958f4a445b8030b28cda627f4d36b7?pvs=21)

[Domande](https://app.notion.com/p/Domande-37758f4a445b80b7a166c00e72cfaf25?pvs=21)

[Da studiare](https://app.notion.com/p/Da-studiare-32e58f4a445b80359aedf935500038b1?pvs=21)

# 🔭 Progetto Information Retrieval — RAG Adattivo e Allineato su Oggetti Cosmici

**L'obiettivo non è costruire un modello che sa rispondere — è costruire i metodi per farlo rispondere bene, alla persona giusta, con le fonti giuste e con un comportamento rigoroso.**

## 📌 Idea del progetto

Un sistema basato su RAG (Retrieval-Augmented Generation) capace di rispondere a domande su buchi neri, wormhole e altri oggetti cosmici, adattando il livello di risposta al profilo dell'utente.

Il sistema raccoglie documenti da fonti eterogenee (libri scientifici, articoli di Hawking, riviste divulgative, riferimenti cinematografici come Nolan) e le usa come base di conoscenza. Prima di rispondere, pone 5–6 domande all'utente per capire la sua età, il background e il livello di conoscenza, costruendo un profilo che guiderà sia la ricerca nei documenti sia la generazione della risposta. A differenza di un semplice RAG basato su prompt, il sistema prevede una fase di **allineamento (DPO)** su un modello open-source per fissare in modo nativo il comportamento adattivo e l'aderenza stretta alle fonti.

## 💡 Intuizioni chiave emerse

- **Il LLM è un "Motore di Ragionamento", non un'Enciclopedia:** Anche se modelli esperti (GPT-4, Claude) conoscono già l'astrofisica, la loro memoria interna è un "frullato statistico" che mischia paper scientifici a forum di fantascienza. Il RAG serve a forzare il modello a ignorare la sua conoscenza pregressa e a usare le sue altissime capacità linguistiche *esclusivamente* per analizzare e tradurre i documenti che gli vengono forniti in quel momento.
- **Behavioral Steering vs. Allineamento Reale:** Inizialmente si pensava di usare solo il System Prompt per guidare il tono ("Sei un astrofisico che parla a un bambino"). Tuttavia, il prompting è fragile (soffre di *Lost in Persona* su contesti lunghi). Per un progetto robusto, serve l'**Allineamento**. Tramite DPO (Direct Preference Optimization), si scolpisce nel modello una policy ferrea: *"Ancorati ciecamente al testo recuperato e adatta il linguaggio al profilo utente"*.
- **Gestione dell'Out-of-Domain (OOD):** Regola d'oro del RAG. Se la risposta non è nei documenti recuperati, il modello allineato deve esplicitamente dichiarare: *"Non ho informazioni sufficienti nelle mie fonti per rispondere a questa domanda"*, azzerando le allucinazioni.
- **Retrieve & Re-rank:** I modelli di embedding vettoriale (Bi-Encoders) sono veloci ma meno precisi semanticamente. È necessario un approccio a due fasi: recuperare i top 20 chunk dal Vector Store e poi passarli a un *Cross-Encoder* (Re-ranker) che li riordina assegnando uno score di pertinenza molto più accurato prima di fornirli al LLM.

## 🏗️ Architettura del sistema e Flusso di Sviluppo

Il progetto non segue un flusso lineare, ma un approccio iterativo in cui il RAG base serve a generare i dati per allineare il modello finale.

### Fase 1: Indicizzazione dei documenti (Knowledge Base)

- **Parsing & Pulizia:** Estrazione testo dai PDF (PyMuPDF).
- **Chunking:** Divisione in blocchi (300–500 token) con overlap.
- **Metadati:** Arricchimento di ogni chunk con fonte, tipo (scienza/fantascienza), livello difficoltà.
- **Embedding & Vector Store:** Vettorizzazione (sentence-transformers) e salvataggio in ChromaDB.

### Fase 2: Profilazione Utente (Session Iniziale)

- **Intervista:** 5-6 domande diagnostiche (età, background, scopo).
- **Estrazione:** LLM come parser per generare un JSON di stato statico per la sessione:
    
    ```json
    {
      "livello": "principiante",
      "eta": 12,
      "background": "non-scientifico",
      "stile": "analogie",
      "interesse": ["buchi neri", "Interstellar"]
    }
    ```
    

### Fase 3: RAG Base (Il Prototipo per Validazione)

- Sviluppo del motore di ricerca vettoriale + Re-ranker.
- Utilizzo di un modello API (es. GPT-4o o Claude) tramite System Prompt per validare che i documenti recuperati siano quelli corretti e che la pipeline funzioni.

### Fase 4: Creazione Dataset "RAG-Aware" (Preparazione Allineamento)

- Utilizzo del RAG Base per generare un dataset sintetico di triplette per il fine-tuning.
- Ogni record contiene: **Prompt** (Domanda + Profilo JSON + Chunk RAG), **Chosen** (Risposta ideale, adattata e fedele ai chunk), **Rejected** (Risposta complessa per un bambino, o allucinata fuori dai chunk).

### Fase 5: Allineamento e Robustezza (DPO)

- Scelta di un modello open-source leggero (es. *Llama-3-8B-Instruct* o *Mistral-7B*).
- Ottimizzazione tramite DPO (usando la libreria TRL) sul dataset RAG-Aware. Il modello impara a interiorizzare il comportamento adattivo senza dipendere da prompt chilometrici.

### Fase 6: RAG Adattivo (Integrazione Finale)

- Sostituzione del modello API con il modello allineato in locale.
- Flusso di produzione: Query -> Vector Store -> Re-ranker -> Prompt Costruito -> Modello Allineato (che genera la risposta con citazione delle fonti).

## 🧠 Concetti teorici del corso

### Fondamentali — non si può fare il progetto senza

| Lezione | Concetto | Perché serve |
| --- | --- | --- |
| 1.4 | Inverted Index | Base di qualsiasi sistema di recupero. Il vector store è la sua evoluzione semantica |
| 1.6 | Term Relevance Weighting | TF-IDF spiega perché si è passati agli embedding: pesare i termini non basta |
| 2 | Probabilistic IR | Base teorica di BM25, l'alternativa al dense retrieval. Serve per giustificare la scelta |
| 4 | IR Evaluation Criteria | Precision, recall, F1, MAP, NDCG — servono per misurare se il retrieval funziona |
| 6.1 | Word Embeddings | Il cuore concettuale del progetto. Word2Vec, GloVe, geometria dello spazio vettoriale |
| 6.6 | Attention | Spiega perché il modello capisce il significato e non solo le parole |
| 6.7 | Transformers | L'architettura del modello usato. Encoder, decoder, differenza tra BERT e GPT |
| 6.9 | Model Pretraining | Spiega come il modello acquisisce conoscenza — e perché non devo addestrare niente io |
| 6.11 | Prompting | Strumento principale per guidare il comportamento: zero-shot, few-shot, chain of thought |
| 6.12 | Evaluation and Ethical Remarks | Valutazione del sistema + discussione critica richiesta in ogni progetto accademico |

### Utili — danno profondità e contesto

| Lezione | Concetto | Perché serve |
| --- | --- | --- |
| 1.1 / 1.2 / 1.3 | Intro IR, Vocabolario, Modello Booleano | Contesto storico — utile per l'introduzione del progetto |
| 1.5 | Scalable Indexing | Spiega i limiti pratici dell'indicizzazione e perché i vector store usano indici approssimati |
| 6.8 | Subword Tokenization | Implicazioni dirette sul chunking e sul calcolo del context window |
| 6.10 | Natural Language Generation | Come il modello genera testo, temperature, sampling — utile per controllare la variabilità |

### Da studiare più leggermente — contesto evolutivo

| Lezione | Concetto | Cosa tenere |
| --- | --- | --- |
| 6.2 | RNN | Capire perché è stato superato dai transformer |
| 6.3 | LSTM | Idem — il problema del long-range dependency che LSTM risolve parzialmente |
| 6.4 | Advanced RNN | Varianti — basta l'intuizione generale |
| 6.5 | Sequence-to-sequence | Modello encoder-decoder — precursore diretto dei transformer |
| 7 | Ethical Considerations | Non sottovalutarlo nella presentazione: allucinazioni, bias, dipendenza da modelli proprietari |

### Ordine di studio consigliato

Seguire la logica del sistema, non il numero delle lezioni:

1. **Cosa significa recuperare informazione** → 1.1, 1.2, 1.3, 1.4, 1.6, 2, 4
2. **Come il testo diventa significato** → 6.1, 6.6, 6.7, 6.8
3. **Come si usa un modello** → 6.9, 6.11, 6.10
4. **Valutazione ed etica** → 6.12, 7
5. **Contesto evolutivo (ponte)** → 6.2, 6.3, 6.4, 6.5

---

## 🛠️ Stack tecnologico

| Componente | Strumento | Note |
| --- | --- | --- |
| **Parsing PDF** | PyMuPDF o pdfplumber | Estrazione testo grezzo |
| **Embedding** | sentence-transformers | Modelli Bi-Encoder open source |
| **Re-Ranker** | BGE-Reranker (o simili) | Modello Cross-Encoder per riordinare i chunk |
| **Vector Store** | ChromaDB | Database vettoriale per similarità semantica |
| **LLM (Prototipo)** | API Claude / GPT-4o | Per la generazione del dataset e test RAG base |
| **LLM (Produzione)** | Llama-3-8B o Mistral-7B | Modello locale da allineare |
| **Allineamento** | TRL (Hugging Face) + LoRA | Libreria per Direct Preference Optimization (DPO) |
| **Valutazione** | RAGAS / LLM-as-a-Judge | Misurazione di *faithfulness*, *relevance* e aderenza al profilo |
| **Interfaccia** | Streamlit | UI rapida per il prototipo e l'intervista |

## ❓ Domande aperte per future iterazioni

- **Gestione Terminologia Multipla:** I *dense embeddings* gestiscono bene i sinonimi semantici, ma per discrepanze estreme (es. "collasso gravitazionale" vs "morte stellare") potrebbe servire integrare tecniche di *Query Expansion* o *HyDE* prima del retrieval.
- **Evoluzione del Profilo:** Per la V1 il profilo utente è statico post-intervista. In una V2, si potrebbe implementare un Agent Loop che aggiorna i pesi delle preferenze dell'utente analizzando il sentiment delle sue domande successive.
- **Valutazione Umana:** Oltre a RAGAS e LLM-as-a-Judge, sarà utile organizzare un blind-test con utenti reali (es. un bambino e uno studente di fisica) per valutare l'effettiva qualità percepita dell'adattamento?

---

```json
progetto_IR/
├── data/
│   ├── raw/                
│   ├── processed/          
│   └── alignment_data/     Dataset JSONL con le coppie (chosen/rejected) per il DPO
│
├── src/
│   ├── alignment/          Script per addestrare e salvare il modello con DPO
│   ├── parsing/            
│   ├── chunking/     # divisione in chunks con metadati
│   ├── indexing/     # embedding e caricamento nel vector store
│   ├── retrieval/    # ricerca per similarità
│   ├── profiling/    # profilazione utente
│   ├── generation/   # costruzione prompt e chiamata LLM
│   └── evaluation/   # script di valutazione con RAGAS
│
├── notebooks/        # esperimenti e analisi esplorative
├── tests/            # test sui singoli moduli
├── [config.py](http://config.py/)         # parametri centralizzati (chunk size, top-k, ecc.)
└── [main.py](http://main.py/)           # entry point dell'applicazione
```

---

### Parsing

- **PyMuPDF (fitz):** Il misuratore. Legge solo quante pagine ha il PDF in una frazione di secondo.
- **Docling:** Il cervello visivo. Guarda le pagine, ricostruisce l'ordine di lettura, traduce le formule in LaTeX e usa l'OCR per leggere il testo intrappolato nelle immagini.
- **PyTorch:** Il motore. È il framework di intelligenza artificiale che fa fisicamente girare le reti neurali di Docling.
- **CUDA (Hardware Nvidia):** L'acceleratore. Permette a PyTorch di scaricare miliardi di calcoli matematici direttamente sulla GPU (scheda video) anziché ingolfare il processore.

### Chunking

- **BeautifulSoup (Il Filtro HTML-Matematico):** Prima che il testo entri nel framework, viene pulito tramite `BeautifulSoup` (`html.parser`). Questo passaggio rimuove la "sporcizia" HTML (tag residui generati da Docling o dalle chiamate API). La sua importanza è cruciale: rispetto a una banale pulizia RegEx, BeautifulSoup è "strutturalmente consapevole". Sa che i segni relazionali della fisica e della matematica (es. `massa < 10 kg`) non sono tag HTML, salvando così le formule scientifiche dalla distruzione.
- **RegEx (Il Chirurgo):** Le espressioni regolari di Python (`re`). Sono regole di ricerca avanzate usate come "bisturi" per pre-processare il testo affiancando BeautifulSoup. Servono specificamente per la "de-hyphenation" (ovvero ricongiungere le frasi spezzate a metà riga dai PDF originali) e per far sparire in sicurezza artefatti visivi come i link delle immagini Markdown.
- **LangChain (Il Framework):** È la libreria standard dell'industria per costruire sistemi RAG. Fornisce gli strumenti (gli *Splitter*) già pronti e ottimizzati per affettare il testo destinato all'Intelligenza Artificiale.
- **MarkdownHeaderTextSplitter (Il Taglio Semantico):** È il primo livello di divisione. Invece di tagliare le parole a caso, "legge" la struttura del documento. Cerca i titoli e i sottotitoli (`#`, `##`, `###`) e raggruppa il testo in base al senso logico e ai capitoli.
- **RecursiveCharacterTextSplitter (Il Taglio di Sicurezza):** Interviene se un capitolo è troppo lungo per l'LLM. Taglia il testo esattamente a 1500 caratteri, ma lo fa in modo "educato": cerca di tagliare sui punti fermi o sugli a capo per non spezzare le parole, mantenendo una sovrapposizione di 200 caratteri tra un blocco e l'altro per non far perdere il contesto al bot.
- **JSONL (Il Vettore di Consegna):** JSON Lines. Invece di un unico file gigante, salvi un oggetto JSON per ogni riga. È il formato più efficiente e digeribile in assoluto per passare i chunk ai modelli di Embedding e ai database vettoriali.

### Indexing

Usiamo BGE-m3 per la trasformazione in vettori numerali dei chunk, molto utile perchè “tiene conto” dei significati delle parole oltre che le parole stesse.

- **Multi-linguality (Multilingua):** Supporta oltre 100 lingue. Nel tuo dataset hai libri in italiano (es. Margherita Hack) e paper in inglese (es. David Tong). BGE-m3 è in grado di capire che "Buco nero" e "Black hole" sono lo **stesso identico concetto** e assegnerà loro coordinate matematiche quasi identiche. Non devi tradurre i libri!
- **Multi-granularity (Multigranularità):** I modelli vecchi andavano in crisi se gli davi in pasto una frase corta ("Cos'è la gravità?") e poi un paragrafo lunghissimo di 1000 parole. BGE-m3 è addestrato per mantenere il significato preciso indipendentemente da quanto sia lungo il chunk che gli passi.
- **Multi-functionality (Multifunzionalità):** È in grado di fare ricerca semantica (per significato) ma ricorda anche le parole chiave esatte. Se uno studente cerca "Raggio di Schwarzschild", il modello sa che deve cercare sia il concetto di orizzonte degli eventi, sia esattamente quel nome proprio.

O eventualmente **I modelli Locali (es. `Nomic-embed-text` o `Mistral-embed`):** Nomic è fantastico, ma è ottimizzato quasi solo per l'inglese. Mistral richiede schede video enormi.

Mentre come DB usiamo ChromaDB che è un DB vettoriale perfetto per il nostro obiettivo di ricerca

- **Ottimizzazione del Database: Deduplicazione tramite Hashing**
Per evitare che ChromaDB si riempia di documenti duplicati (situazione molto comune se, ad esempio, lo stesso libro o capitolo è presente in più cartelle "Topic" diverse), abbiamo implementato un sistema di deduplicazione alla fonte.
    
    Invece di assegnare a ogni chunk un ID basato sul nome del file, il sistema calcola un **Hash crittografico (MD5)** basato esclusivamente sul testo del paragrafo. Questa stringa alfanumerica diventa l'ID univoco del chunk. In questo modo:
    
    - **Zero Ridondanza:** Se il sistema legge lo stesso identico testo in due file diversi, genererà lo stesso identico ID.
    - **Upsert Intelligente:** Quando ChromaDB riceve un ID che possiede già, non crea un nuovo clone vettoriale, ma si limita ad aggiornare il record esistente (sovrascrivendone i metadati).
    - **Ricerca più efficiente:** Questo approccio mantiene il database vettoriale estremamente leggero e garantisce che la ricerca (Retrieval) non venga "cannibalizzata" da risultati identici, offrendo all'LLM un contesto sempre vario e informativo.

### **Retrieval**

- **Stadio 1: Ricerca Estesa (Query Expansion + Bi-Encoder + ChromaDB)** Invece di usare una singola domanda, l'architettura prende in ingresso una **lista di varianti della domanda** dell'utente (ad esempio, la versione originale in italiano e la sua traduzione in inglese). Tutte le varianti vengono date in pasto al modello multilingua **BGE-m3**, che le trasforma in vettori. Chiediamo a ChromaDB di trovare i primi **20 frammenti** (`initial_k=20`) matematicamente più vicini per le query, applicando subito il filtro del livello di difficoltà (es. `user_level`). Infine, i risultati provenienti da tutte le varianti di ricerca vengono uniti e **de-duplicati** in un'unica lista di documenti candidati.
    - *Pro:* Usando diverse varianti (e lingue) il sistema è molto più robusto e recupera frammenti che la singola domanda utente originale avrebbe completamente fallito.
    - *Contro:* Aumentando il bacino di candidati si pescano inevitabilmente anche frammenti che condividono solo il campo semantico, ma non la risposta esatta.
- **Stadio 2: Riordino di Precisione e Filtraggio (Cross-Encoder / Re-Ranker)** Prendiamo l'insieme unico di frammenti grezzi (dei 20 candidati de-duplicati) e li passiamo a un secondo modello, chiamato **Re-Ranker** (`BAAI/bge-reranker-v2-m3`). Questo modello non usa vettori spaziali astratti; legge fisicamente la **domanda originale dell'utente** accoppiata uno a uno con ogni singolo frammento e dà un punteggio di precisione (score) che valuta quanto quel chunk risponde *esattamente* a quella domanda. Alla fine, teniamo solo i **3 chunk** (`final_k=3`) con il voto più alto.
    - *Il ruolo del giudice:* Se ChromaDB da solo si fa ingannare da concetti simili, il `CrossEncoder` rilegge tutto linearmente e agisce da giudice severo: penalizza duramente i falsi positivi ottenuti dalle traduzioni o dai testi generici.
- **Query Expansion Multilingua** *(in alternativa alla classica Ricerca Ibrida BM25)* Invece di affiancare ChromaDB a un motore a parole chiave esatte (Hybrid Search BM25), questo sistema supera i limiti semantici sfruttando la **Multi-Query Expansion esplorativa**. Dato che il modello vettoriale BGE-m3 eccelle nel collegare lingue diverse, fornire in parallelo la domanda in inglese e in italiano (es. "Cos'è un orizzonte degli eventi?" / "What is an event horizon?") permette al sistema vettoriale di comportarsi quasi come se avesse due reti da pesca: se nel testo italiano l'autore usa una parola insolita che il vettore italiano manca, la query speculare in inglese spesso "intercetta" il vettore matematicamente affine aggirando l'ostacolo terminologico. Lo Stadio 2 si occupa poi di pulire eventuali distorsioni create da reti troppo larghe.

### **Generation**

- **Fase 1: Preparazione della Query (Zero-Shot Translation)** Prima di inoltrare la richiesta di ricerca al database, il modulo di generazione interroga brevemente il modello linguistico locale (`qwen2.5:3b` eseguito tramite Ollama) usandolo come traduttore. Chiede al modello di trasformare la domanda dell'utente nella lingua opposta (da Italiano a Inglese o viceversa). Questa chiamata usa creatività azzerata (`temperature=0.0`) per garantire una traduzione letterale e pulita. Produce così la "lista di query" che abbiamo visto essere il carburante della Multi-Query Expansion dello Stadio 1 del Retrieval.
- **Fase 2: Controlli di Sicurezza e Analisi Pertinenza** Dopo aver ricevuto i frammenti riordinati (Re-Ranked) dal modulo di Retrieval, il RAG Generator fa un rapido controllo di sicurezza: ispeziona il punteggio matematico del frammento migliore. Se questo score in logit cade sotto una certa soglia di allerta (es. `< -5.0`), significa che i concetti estratti sono forzatamente incollati e marginalmente collegati alla domanda. A questo punto il sistema sa in anticipo che la generazione rischia di fallire e può generare avvisi di bassa pertinenza.
- **Fase 3: Costruzione del Prompt e Regole Anti-Allucinazione** A questo punto si assembla il `System Prompt` (il pacchetto di istruzioni severe che governerà il comportamento dell'Intelligenza Artificiale). Questa fase fa due cose fondamentali:
    1. **Adattamento Didattico:** Inietta istruzioni stilistiche radicalmente diverse in base al pubblico (Livello A, B, C, D). Se l'utente è "A", forza l'IA a un tono dolce e all'uso di analogie infantili; se "D", esige rigore fisico-matematico universitario.
    2. **Muri di Contenimento (Anti-Hallucination):** Inserisce regole inviolabili che vietano all'IA di usare conoscenze pregresse esterne ai PDF caricati. Impone, se la risposta non è rintracciabile nei frammenti incollati, di "arrendersi" scrivendo *esplicitamente* che i documenti forniti non contengono quell'informazione, chiudendo le porte alle invenzioni narrative dell'IA.
- **Fase 4: Generazione Controllata e Citazione Trasparente** L'Intelligenza Artificiale produce la risposta finale leggendo la domanda, le regole di stile e i riassunti trovati. L'operazione avviene a bassissima temperatura (`temperature=0.1`) per favorire spiegazioni razionali, ancorate ai fatti e stabili. A risposta conclusa, il sistema estrae in automatico i metadati dei frammenti effettivamente inseriti nel prompt e appende in calce un blocco riassuntivo delle **fonti utilizzate**, indicando chiaramente i titoli dei testi e i nomi dei file originali consultati. Questo dona totale tracciabilità ai risultati.

*(Nel modulo è prevista anche una modalità Baseline — `generate_without_rag` — che spegne tutto il Retrieval per misurare come avrebbe risposto il modello "da solo"; una tecnica usata per valutare l'effettivo salto di qualità e precisione portato dalla pipeline).*