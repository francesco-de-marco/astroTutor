# TODO — AstroTutor (Progetto IR)

> Aggiornato: 25/07/2026 · Dettagli e motivazioni: [`report/report_2026_07_25.md`](report/report_2026_07_25.md)

**Legenda** — 🟢 si può fare subito · ⛔ bloccato da un'altra voce · 🔥 impatto alto · 💤 in attesa di hardware/training

---

## ⚡ Prossime 3 azioni

1. **P0** — strumentare la latenza dei 3 stadi (6 righe, sblocca tutte le ottimizzazioni)
2. **#15** — puntare `_translate_query` su un modello base fisso (prima dell'ablazione, altrimenti la falsa)
3. **#1** — costruire il gold set del retrieval da `alignment_data.json`

Tutte e tre sono offline e non dipendono dal training in corso.

---

## 1️⃣ Sblocco e misura

*Non dipendono da nulla, abilitano tutto il resto.*

- [ ] 🟢 **P0** — Strumentare con `perf_counter` i 3 stadi (traduzione / retrieval / generazione) in `generation.py` e misurare su 5 domande
  → oggi **non esiste nessuna misura di latenza**: senza, ogni ottimizzazione è a caso
- [ ] 🟢 **#15** — `_translate_query` (`generation.py:64`) usa `self.model_name`: puntarlo su un modello base fisso
  → con `LLM_MODEL = "astrotutor-dpo"` a tradurre è il modello allineato, addestrato a rifiutare fuori dominio. **Da fare prima di #2**, altrimenti l'ablazione confronta configurazioni con traduttori diversi

---

## 2️⃣ Valutazione del retrieval 🔥

*Il buco più grave rispetto ai requisiti del corso (Lezione 4). Tutto offline.*

- [ ] 🟢 **#1** — Costruire il gold set da `data/alignment_data.json` (campi `source_chunk_file` / `sources` → ~600 coppie query/chunk) e calcolare **Recall@k, MRR, nDCG**
  → il gold set esiste già: ogni domanda è stata generata *da* un chunk specifico. È un silver-standard, quindi i valori assoluti sono un limite inferiore — conta il confronto tra configurazioni
- [ ] ⛔ **#2** — Ablazione sulle 5 configurazioni *(dipende da #1 e #15)*

  | Configurazione | Cosa isola |
  |---|---|
  | solo bi-encoder BGE-m3 | baseline denso |
  | + re-ranker cross-encoder | guadagno dello Stadio 2 |
  | + query expansion multilingua | guadagno delle varianti IT/EN |
  | + `EXACT_LEVEL_BONUS` | costo/beneficio del bias di livello |
  | BM25 | risponde al finding di AstroLLM-Eval sulla terminologia esatta |

  → **sblocca anche P7 e P8**: se la query expansion aggiunge poco, toglierla elimina una generazione LLM e dimezza i candidati da riordinare

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

*Da fare **prima** del prossimo riallenamento.*

- [ ] 🟢 **#3** — Rescoring di fattualità delle 623 triplette col giudice RAGAS già scritto: scartare o invertire le coppie dove `F(rejected) > F(chosen)`, e riportare quante erano invertite
  → approccio F-DPO a livello di dataset (niente loss custom). Spiega il calo di faithfulness a livello A: 0.657 → 0.498

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

- [ ] ⛔ **P7** — Rimuovere la query expansion multilingua → 🔥 −1 generazione LLM, −50% candidati da riordinare
  → BGE-m3 è multilingua nativo: l'ablazione dirà se la traduzione esplicita aggiunge davvero valore
- [ ] ⛔ **P8** — `initial_k` da 20 a 10 (`retrieval.py:126`) → costo del re-ranking lineare nei candidati

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
