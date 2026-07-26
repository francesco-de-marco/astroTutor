# TODO — AstroTutor (Progetto IR)

 Pipeline completa

PDF + API  →  parsed  →  chunks  →  ChromaDB  →  retrieval  →  generation  →  UI
                                                      ↑                ↑
                                              valutazione IR    modello allineato

┌─────┬─────────────────┬──────────────────────────────────┬────────────────────────────────────┬──────────────────────────┬───────────────────────┐
│  #  │     Stadio      │               File               │           Input → Output           │        Obiettivo         │         Stato         │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 0   │ Acquisizione    │ src/ingest_api_data.py           │ API Vikidia/Wikipedia/EduINAF →    │ Coprire i livelli A e B, │ ✅                    │
│     │                 │                                  │ data/processed/parsed/             │  che i PDF non coprono   │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 1   │ Parsing         │ src/parsing.py (+ varianti       │ data/raw/*.pdf →                   │ Estrarre testo pulito    │ ✅                    │
│     │                 │ Colab/Kaggle/MinerU)             │ data/processed/parsed/             │ dai libri, con Docling   │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│     │                 │                                  │ parsed/ →                          │ Spezzare in blocchi con  │                       │
│ 2   │ Chunking        │ src/chuncking.py                 │ data/processed/chunks/*.jsonl      │ metadati: titolo, fonte, │ ✅                    │
│     │                 │                                  │                                    │  livello                 │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 3   │ Indicizzazione  │ src/indexing.py                  │ chunks/ → data/vector_db/          │ Embedding bge-m3 →       │ ✅                    │
│     │                 │                                  │                                    │ ChromaDB                 │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│     │                 │                                  │                                    │ Multi-query IT/EN,       │                       │
│ 4   │ Recupero        │ src/retrieval.py                 │ query → 3 chunk                    │ filtro di livello con    │ ✅                    │
│     │                 │                                  │                                    │ fallback, bonus,         │                       │
│     │                 │                                  │                                    │ re-ranker                │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 5   │ Generazione     │ src/generation.py                │ chunk + livello → risposta         │ Prompt per livello,      │ ⚠️ manca best-of-3 e  │
│     │                 │                                  │                                    │ guardrail sul registro   │ soglia OOD            │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 6   │ Interfaccia     │ main.py                          │ CLI                                │ Provare il sistema       │ ⚠️ manca Streamlit    │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 6b  │ Profilazione    │ (assente)                        │ intervista → livello A/B/C/D       │ Fase 2 della specifica   │ ❌ mai fatta          │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 7   │ Dati insegnante │ src/alignment.py                 │ topic → data/alignment_data.json   │ Risposte ideali del 70B  │ ✅ (da rigenerare le  │
│     │                 │                                  │                                    │ sui prompt RAG reali     │ D)                    │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│     │                 │                                  │ alignment_data.json →              │ Filtrare le ~423         │                       │
│ 8   │ Dataset SFT     │ src/sft_dataset.py               │ data/sft_data.json                 │ risposte che passano i   │ ➕ nuovo              │
│     │                 │                                  │                                    │ guardrail                │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 9   │ Training SFT    │ src/alignment_dpo_colab.ipynb (2 │ sft_data.json → adapter LoRA       │ Trasferire il registro   │ ➕ da adattare        │
│     │                 │  celle)                          │                                    │ nei pesi                 │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 10  │ DPO opzionale   │ stesso notebook, 1 riga          │ adapter SFT → adapter DPO          │ Solo se resta un difetto │ 🔄                    │
│     │                 │                                  │                                    │  specifico               │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 11  │ Export          │ stesso notebook                  │ adapter → GGUF Q4 + Modelfile →    │ Rendere il modello       │ ✅                    │
│     │                 │                                  │ Ollama                             │ usabile in locale        │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│     │ Valutazione     │                                  │ alignment_data.json →              │ Recall@k, MRR, nDCG +    │                       │
│ 12  │ retrieval       │ src/retrieval_eval.py            │ data/retrieval_eval.json           │ ablazione re-ranker /    │ ❌ il buco più grave  │
│     │                 │                                  │                                    │ query expansion / bonus  │                       │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│     │ Valutazione     │ src/evaluation.py,               │                                    │ Gulpease, faithfulness,  │ ⚠️ metrica di rifiuto │
│ 13  │ generazione     │ evaluation_colab.ipynb           │ domande → eval_results.json        │ rifiuto OOD              │  da correggere, manca │
│     │                 │                                  │                                    │                          │  il braccio no-RAG    │
├─────┼─────────────────┼──────────────────────────────────┼────────────────────────────────────┼──────────────────────────┼───────────────────────┤
│ 14  │ Analisi         │ src/analysis.py                  │ risultati → report/figures/        │ Grafici e tabelle del    │ ✅ (4 grafici in      │
│     │                 │                                  │                                    │ report                   │ attesa di dati)       │
└─────┴─────────────────┴──────────────────────────────────┴────────────────────────────────────┴──────────────────────────┴───────────────────────┘


> Aggiornato: 26/07/2026 · Dettagli e motivazioni: [`report/report_2026_07_26.md`](report/report_2026_07_26.md)

**Legenda** — 🟢 si può fare subito · ⛔ bloccato da un'altra voce · 🔥 impatto alto · 💤 in attesa di hardware/training

---

## ⚡ Prossime 3 azioni *(riallineate il 26/07 sera, dopo la run Colab)*

1. ~~**#1 + #15**~~ ✅ **fatto** — valutazione IR del retrieval completata su 172 query, 6 configurazioni: vedi §2️⃣. Il documento giusto è nei primi 3 nell'**80%** dei casi
2. **Fix rapidi sul sistema** — metrica OOD letterale+semantica (`evaluation.py:77`), soglia di rifiuto sulla scala giusta [0,1] (`generation.py:132`), `level_match` passato al prompt, **best-of-3 sul Gulpease** nei guardrail. Ora si aggiunge **P7** (togliere la query expansion: l'ablazione dice che non serve)
3. **#4** — braccio no-RAG nella prossima run di valutazione (una riga: `generate_without_rag` esiste già). Nella stessa run, se possibile, braccio `qwen2.5:7b` come riferimento superiore

La tesi si basa sulla **run Colab** (`results/eval_qwen2.5_14b-instruct_20260726_1039/`, vedi `run_meta.json`); la run locale in `data/` è superata (vedi `data/run_meta.json`). L'alignment DPO va presentato come **ablazione a esito nullo con diagnosi** (autori diversi ai due lati); l'eventuale riallenamento on-policy sul registro (`alignment_register.py`, best-of-N) è opzionale e viene **dopo** i tre punti sopra.

---

## 1️⃣ Sblocco e misura

*Non dipendono da nulla, abilitano tutto il resto.*

- [ ] 🟢 **P0** — Strumentare con `perf_counter` i 3 stadi (traduzione / retrieval / generazione) in `generation.py` e misurare su 5 domande
  → oggi **non esiste nessuna misura di latenza**: senza, ogni ottimizzazione è a caso
- [ ] 🟢 **#15** — `_translate_query` (`generation.py:64`) usa `self.model_name`: puntarlo su un modello base fisso
  → con `LLM_MODEL = "astrotutor-dpo"` a tradurre è il modello allineato, addestrato a rifiutare fuori dominio
  → ✅ **risolto lato valutazione**: `retrieval_eval.py` usa un traduttore fisso (`qwen2.5:3b`, `temperature=0.0`) con cache in `data/query_translations.json`, quindi l'ablazione #2 è pulita
  → ⚠️ **in `generation.py` il difetto resta**, ma diventa irrilevante se si esegue **P7** (rimozione della query expansion): niente traduzione, niente problema. Fare P7 *prima*, e riaprire #15 solo se si decide di tenerla

---

## 2️⃣ Valutazione del retrieval ✅ *(fatta il 26/07 sera)*

*Era il buco più grave rispetto ai requisiti del corso (Lezione 4). `src/retrieval_eval.py`, tutto offline.*

- [x] ✅ **#1** — Gold set da `data/alignment_data.json`: **172 query** con `source_chunk_file` (domanda generata *da* un chunk di quel PDF). Le triplette topic-based sono escluse perché il loro campo `sources` è l'output del retriever stesso → circolare. Silver-standard a granularità di **documento**: i valori assoluti sono un limite inferiore, conta il confronto fra configurazioni
- [x] ✅ **#2** — Ablazione su **6** configurazioni, n=172 (A 40 / B 42 / C 35 / D 55)

  | Configurazione | R@1 | R@3 | R@10 | MRR | nDCG |
  |---|---|---|---|---|---|
  | BM25 | 0.180 | 0.221 | 0.244 | 0.206 | 0.214 |
  | BM25 + expansion | 0.308 | 0.436 | 0.605 | 0.406 | 0.447 |
  | solo bi-encoder | 0.576 | 0.733 | 0.884 | 0.674 | 0.725 |
  | + re-ranker | 0.523 | 0.762 | 0.884 | 0.651 | 0.708 |
  | + query expansion | 0.523 | 0.767 | 0.890 | 0.656 | 0.713 |
  | **+ bonus livello** (produzione) | **0.593** | **0.797** | **0.895** | **0.705** | **0.751** |

  **Tre risultati da riportare in tesi:**
  1. **BM25 raddoppia con la traduzione** (0.221 → 0.436 R@3): il lessicale fallisce per la **lingua** (corpus in inglese, query in italiano), non per l'approccio. Risposta diretta alla critica di AstroLLM-Eval
  2. **La query expansion non aggiunge nulla** (+0.005 R@3, +0.005 MRR): bge-m3 è già multilingue → **sblocca P7**
  3. **Il bonus di livello è il componente più utile** (+0.030 R@3, +0.049 MRR) e recupera esattamente ciò che il re-ranker perde in cima. ⚠️ Il re-ranker **peggiora R@1** (0.576 → 0.523) pur migliorando R@3: riordina bene il podio, sbaglia più spesso il primo posto — da indagare

  Per livello (R@3, pipeline completa): A **0.700** · B 0.857 · C 0.714 · D 0.873. Il livello A è il più debole, coerente con la copertura del corpus (252 chunk A contro 10.547 D)

- [x] ✅ Grafici 7 e 8 generati: `report/figures/07_recall_at_k.png`, `08_mrr_ndcg.png`
- [ ] 🟢 Indagare il calo di R@1 del re-ranker con `data/retrieval_eval_details.jsonl` (contiene il rank del gold per ogni query × configurazione)

---

## 3️⃣ Velocità — interventi sicuri

*Non cambiano né i documenti recuperati né le risposte: non invalidano nessuna valutazione già fatta.*

| ID | Azione | Dove | Guadagno |
|---|---|---|---|
| **P1** | Re-ranker su GPU (`device="cpu"` → `"cuda"`) | `retrieval.py:45` | 🔥 da secondi a decine di ms |
| **P2** | Embedder su GPU **solo se avanza VRAM** | `retrieval.py:33` | basso (2 stringhe corte) — su GPU da 4 GB lasciarlo su CPU |
| **P3** | Traduzione: cache query→traduzione, o `qwen2.5:0.5b` dedicato | `generation.py:64` | 🔥 1-3 s per query |
| **P5** | `keep_alive` sulle chiamate Ollama | `generation.py` | evita ricaricamenti del modello |
| **P6** | Loggare quanto spesso scattano i guardrail | `generation.py:87` | diagnostico — quando scattano **raddoppiano** la latenza |

- [ ] 🟢 P1 · [ ] 🟢 P2 · [ ] 🟢 P3 · [ ] 🟢 P5 · [ ] 🟢 P6

> **Perché il re-ranker è il sospetto n.1**: BGE-m3 e `bge-reranker-v2-m3` hanno la stessa taglia (~568M) e girano entrambi su CPU, ma l'embedder processa **2 stringhe corte** mentre il re-ranker fa un forward pass **per ogni coppia** (domanda, chunk) — fino a ~40 coppie da ~400-500 token. A VRAM limitata: re-ranker su GPU, embedder su CPU.

---

## 4️⃣ Fattualità del dataset

*⏸️ **Sospeso** (report 26/07, seconda parte).*

- [ ] ⏸️ **#3** — Rescoring di fattualità delle 623 triplette col giudice RAGAS (30-50 h)
  → era motivato dal calo di faithfulness a livello A (0.657 → 0.498), che **non replica** nella run Colab: non è chiaro che il problema esista. Da riconsiderare solo se un rigiudizio incrociato lo riapre

---

## 5️⃣ Deliverable mancanti

### Fase 2 — Individuazione del livello utente *(#5)*

**Meccanismo**: intervista in linguaggio naturale → LLM come **parser** verso JSON → **regola deterministica** verso A/B/C/D → override manuale sempre disponibile

- [ ] 🟢 **5.1** — Progettare le 5-6 domande con **effetto imbuto**: prima quelle che partizionano di più (età, percorso di studi), poi la rifinitura (matematica, stile)
- [ ] 🟢 **5.2** — Definire lo schema JSON con **enum chiusi** (`eta`, `percorso`, `fisica`, `matematica`, `stile`) e `null` esplicito
- [ ] 🟢 **5.3** — Prompt di estrazione + `response_format={"type":"json_object"}` + `temperature=0.0`
- [ ] 🟢 **5.4** — Regola deterministica profilo → livello: **età fino ai 18 anni, poi background**, correzione ±1 dalla matematica
  → è il pezzo che fissa il soffitto di qualità: nessun modello più grande corregge una regola sbagliata
- [ ] 🟢 **5.5** — Validazione + fallback: JSON non parsabile o valore fuori enum → `null`, mai improvvisare
- [ ] 🟢 **5.6** — Domanda di chiarimento su bassa confidenza (campi critici `null` o segnali contraddittori)
- [ ] 🟢 **5.7** — Aggiungere `PROFILER_MODEL` a `config.py`, distinto da `LLM_MODEL`
- [ ] 🟢 **5.8** — Test a due bracci su 20-30 persona sintetiche: `qwen2.5:3b` vs `qwen2.5:7b-instruct` → accuratezza per campo, accuratezza livello, JSON malformati
  → guardare **dove** sbaglia: B↔C è quasi innocuo (i `LEVEL_FALLBACK` si sovrappongono), A↔D è grave (insiemi disgiunti) → **matrice di confusione**, non una percentuale
- [ ] 🟢 **5.9** — Verificare VRAM e configurare `OLLAMA_MAX_LOADED_MODELS` / `keep_alive` per tenere tutor e profilatore residenti insieme

⚠️ **Mai usare `astrotutor-dpo` come profilatore**: è addestrato a rifiutare fuori dominio, rischia di rispondere con la frase di rifiuto invece del JSON.

### UI e valutazione *(#6, #4)*

- [ ] 🟢 **6.1** — UI Streamlit: intervista iniziale, **livello sempre visibile**, selettore manuale A/B/C/D sempre in sidebar
  → il livello filtra il corpus (`retrieval.py:56`): un errore di classificazione è altrimenti invisibile all'utente
- [ ] 🟢 **6.2** — Bottoni "troppo difficile / troppo facile" → ±1 livello e rigenerazione (~10 righe, loop dinamico + dati etichettati)
- [ ] ⛔ **P4** — Streaming della risposta *(dipende da 6.1)* → 🔥 altissimo sul **percepito**, nullo sul totale
- [ ] 🟢 **#4** — Aggiungere il braccio **no-RAG** in `evaluation.py` (`generate_without_rag` esiste già ma non è mai chiamato)
  → l'ipotesi centrale del progetto non è mai stata misurata. Una riga di configurazione

---

## 6️⃣ Velocità — a rischio qualità

*⛔ Bloccati fino ai risultati di #2. Sono i più allettanti, ed è proprio per questo che serve il blocco esplicito.*

- [ ] 🟢 **P7** — **SBLOCCATO dall'ablazione #2: si può togliere.** La query expansion vale +0.005 R@3 e +0.005 MRR, cioè nulla — BGE-m3 è multilingua nativo e la traduzione esplicita è ridondante. Rimuoverla elimina 🔥 una generazione LLM per query e dimezza i candidati da riordinare
  → attenzione: il **bonus di livello** va tenuto (è il componente più utile), quindi togliere solo la variante EN, non il resto della pipeline
- [ ] 🟢 **P8** — `initial_k` da 20 a 10 (`retrieval.py:126`) → costo del re-ranking lineare nei candidati. Con la expansion rimossa i candidati sono già la metà: rimisurare prima di ridurre ancora

---

## 7️⃣ Qualità del sistema e report

*In parallelo a tutto il resto.*

- [ ] 🟢 **#9** — Promuovere l'avviso di bassa pertinenza (`generation.py:132`, `score < -5.0`) a **rifiuto vero**, previa calibrazione della soglia
  → oggi stampa solo un warning. Trasforma il rifiuto OOD da giudizio del modello a garanzia di sistema
- [ ] 🟢 **#10** — Sostituire il Gulpease medio con l'**aderenza alla banda target** (% dentro banda + deviazione media)
  → ri-lettura di `eval_results.json`, nessuna rigenerazione. Una media di 57.97 non distingue un modello tarato da uno sregolato
- [ ] 🟢 **#11** — Asse **fedeltà delle citazioni**: verificare che le fonti appese da `generation.py:151` siano quelle davvero usate
- [ ] 🟢 **#16** — Separare "profondità concettuale" da "registro linguistico" in `_get_system_instructions`
  → un adulto principiante finisce correttamente a livello A per contenuto, ma riceve il tono da "bambino di 6-10 anni". Impatta anche i `ResponseGuardrails`
- [ ] 🟢 **#7** — Sezione **etica e discussione critica**: allucinazioni, bias del corpus, tutoring adattivo su minori, dipendenza da modelli proprietari
- [ ] 🟢 **#8** — Scheletro del report: introduzione, related work, architettura, metodologia
  → la struttura non dipende dai numeri, restano da riempire solo le tabelle dei risultati

---

## 💤 In attesa

- [ ] **#13** — Completare il training DPO su 623 triplette e rilanciare `evaluation.py` sul nuovo modello
- [ ] **#12** — Verificare se "Bollo Nucleare nel Buco Nero" ricompare nel nuovo modello
  → se ricompare è un pattern appreso in training, se sparisce era rumore
- [ ] **#14** — Igiene finale: cancellare `apikey.txt` e `scripts_tmp_bulk_wrong_register.py`, pinnare le versioni nel notebook Kaggle, allineare README e struttura repo alla specifica

---

## 📚 Da citare nel report

⚠️ La wiki in `paper/wiki/` è generata da LLM: **verificare ogni numero e ogni metadato sul PDF originale** prima di citarlo.

| Fonte | Usare per |
|---|---|
| **F-DPO** | Spiegazione del calo di faithfulness a livello A + metodo del rescoring (#3) |
| **AstroLLM-Eval** | Rubrica di valutazione a 4 assi (#11) + critica alla ricerca vettoriale pura (#2) |
| **ReadCtrl** | Fondamento teorico del Gulpease + metrica di aderenza al target (#10) |
| **PersonaRAG** | Formalizza l'`EXACT_LEVEL_BONUS` già implementato come reranking persona-pesato |
| **RAG-PRISM** | Related work più vicino; profilo statico vs dinamico (#6.2) |
| **MAS2S / ClariT** | Framing della Fase 2 + ablazione senza profilo utente (BLEU 0.315 → 0.256) |
| **MathDial** | Evidenza esterna: piccolo fine-tuned > grande zero-shot sulla qualità pedagogica |
| **How Learning Works** | Cornice didattica generale per l'asse "qualità pedagogica" |

---

## ❌ Valutato e scartato

| Cosa | Perché |
|---|---|
| **Speculative decoding** con modello draft | Agisce solo sul decoding, richiederebbe di uscire da Ollama, e ottimizzerebbe uno stadio che non è il collo di bottiglia (i due encoder da 568M sono su CPU) |
| Inferenza implicita del livello dalla prima domanda | Segnale insufficiente e ingannevole: un fisico che chiede "cos'è un buco nero?" verrebbe classificato A |
| RAG agentico ibrido (Knowledge Graph + routing) | Progetto a sé, fuori scope |
| Stima di incertezza epistemica via log-prob | Supporto ai logprobs non affidabile con Ollama |
| Elicitazione preferenze ispirata alla diffusione | Metodo di training sproporzionato per un'intervista di 5-6 domande |
| Loss F-DPO custom (margine γ·ΔF) | Richiederebbe di modificare `DPOTrainer` e un riallenamento in più; il rescoring del dataset ottiene l'essenziale senza toccare l'infrastruttura |
