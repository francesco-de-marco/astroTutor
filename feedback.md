# Valutazione Qualità di `alignment_data.json` per DPO Training

## Panoramica Dataset

| Metrica | Valore |
|---|---|
| Esempi totali | **379** |
| ID unici | 379/379 ✅ |
| Domande uniche | 332/379 (47 duplicati, tutti OOD cross-livello) |
| Fonti uniche referenziate | 60 |
| Formato | JSON Lines (1 oggetto per riga) |

---

## 1. Struttura e Formato — ✅ Eccellente

Il formato è **perfettamente compatibile** con il notebook DPO:

| Check | Risultato |
|---|---|
| `prompt[0].role == "system"` | ✅ 379/379 |
| `prompt[-1].role == "user"` | ✅ 379/379 |
| `chosen[0].role == "assistant"` | ✅ 379/379 |
| `rejected[0].role == "assistant"` | ✅ 379/379 |
| Messaggi per prompt | Sempre 2 (system + user) |
| Messaggi per chosen/rejected | Sempre 1 |

Il sanity check del notebook (cella 3) passerà senza problemi:
```python
assert isinstance(example["prompt"], list) and example["prompt"][0]["role"] == "system"
assert example["chosen"][0]["role"] == "assistant"
```

> [!TIP]
> Il formato conversazionale `[{"role": ..., "content": ...}]` è esattamente quello atteso da `DPOTrainer` di TRL. Nessuna trasformazione necessaria.

---

## 2. Distribuzione Strategie — ✅ Buona, con riserva

| Strategia | Count | % |
|---|---|---|
| `hallucination` | 164 | 43.3% |
| `wrong_register` | 149 | 39.3% |
| `ood` | 66 | 17.4% |

### Cross-tabella Strategia × Livello Utente

| Strategia | A | B | C | D | Tot |
|---|---|---|---|---|---|
| `hallucination` | 38 | 40 | 33 | 53 | 164 |
| `wrong_register` | 32 | 44 | 30 | 43 | 149 |
| `ood` | 19 | 16 | 18 | 13 | 66 |
| **Totale** | **89** | **100** | **81** | **109** | **379** |

> [!NOTE]
> La distribuzione è ragionevolmente bilanciata tra livelli utente (81–109 per livello). Le strategie `hallucination` e `wrong_register` sono dominanti, il che è corretto: sono i failure mode principali da correggere. L'OOD è minoritario (~17%) ma sufficiente per insegnare il rifiuto.

> [!IMPORTANT]
> **Possibile sbilanciamento OOD**: con soli 66 esempi OOD (vs. 313 non-OOD), il modello potrebbe non apprendere abbastanza bene il pattern di rifiuto. Tuttavia, il fatto che **66/66 chosen OOD contengano la frase esatta di rifiuto** è un segnale molto positivo — il segnale è pulito e coerente.

---

## 3. Qualità dei Contenuti — ✅ Molto Buona

### Chosen (risposte corrette)
- **Lunghezza media**: 860 caratteri (concise, mirate)
- **Range**: 82–2462 chars
- Le risposte sono ancorate al contesto, usano il registro appropriato al livello utente, e le OOD rifiutano correttamente

### Rejected (risposte errate)
- **Lunghezza media**: 1788 caratteri (2x più lunghe delle chosen)
- **Range**: 244–4047 chars
- I rejected sono volutamente verbosi, con allucinazioni, registro sbagliato, o informazioni inventate

### Segnale di preferenza

| Metrica | Valore |
|---|---|
| Chosen più corto di rejected | **86.8%** (329/379) |

> [!WARNING]
> **Rischio di length bias**: nel **86.8%** dei casi il chosen è più corto del rejected. Il DPO potrebbe imparare un proxy spurio ("rispondi corto = buono") invece della vera policy desiderata. Questo è un problema comune nei dataset DPO. 
> 
> **Mitigazione possibile**: 
> - Aggiungere alcuni esempi dove il chosen è più lungo e dettagliato del rejected (es. rejected troppo superficiale/vago)
> - Oppure fidarsi del fatto che il segnale semantico (allucinazione vs. fedeltà) è abbastanza forte da dominare — nei 3 esempi ispezionati la differenza qualitativa è enorme

### Ispezione qualitativa (campioni letti)

Ho esaminato in dettaglio i primi 6 esempi. Feedback:

1. **Hallucination (Esempio 1, D-level)**: Il chosen spiega rigorosamente il principio di stazionarietà citando l'equazione 324 dal contesto. Il rejected inventa terminologia ("trasformata quadratura", "sincronizzazione nella fisica classica"), usa formule sbagliate, e mescola concetti inesistenti. **Contrasto eccellente ✅**

2. **Wrong_register (Esempio 2, A-level)**: Il chosen risponde a livello bambino ("23 volte più luminosa, come 23 candele") — corretto e fedele. Il rejected risponde con tono accademico e **inventa un dato (8200x)** confondendo il rapporto Sirius/Sole con il rapporto Sirius/companion. **Doppio errore (registro + hallucination) nel rejected ✅**

3. **Hallucination (Esempio 3, C-level)**: Il chosen estrae correttamente dal contesto (i rilevatori si saturano di fotoni). Il rejected inventa completamente ("processo di Compton", "onde infrarosse dai neutrini"). **Contrasto chiarissimo ✅**

4. **Wrong_register (Esempio 4, D-level)**: Chosen rigoroso e accademico. Rejected usa tono da bambino ("minuscolo schizzo di inchiostro sul muro") per un livello D. **Registro completamente sbagliato nel rejected ✅**

5. **Hallucination (Esempio 5, A-level)**: Chosen calcola correttamente 570.000 miliardi di km. Rejected inventa numeri deliranti ("93 milioni di km per 1 anno luce", "59 milioni di miliardi di km"). **Contrasto fortissimo ✅**

6. **OOD (Esempio 6, A-level)**: Chosen = frase di rifiuto esatta. Rejected inventa completamente una risposta sull'influenza stagionale senza alcun supporto dal contesto. **Perfetto ✅**

> [!TIP]
> La qualità del contrasto chosen/rejected è **molto alta**. Il segnale DPO è chiaro e non ambiguo in tutti i campioni analizzati. Questo è il fattore più importante per il successo del training.

---

## 4. Dimensionamento e Tokenizzazione — ⚠️ Adeguato ma al limite

| Metrica | Valore |
|---|---|
| Avg chars per esempio (prompt+chosen+rejected) | ~7229 |
| Stima avg tokens per esempio | ~2065 |
| Prompt avg/min/max length | 4580 / 2335 / 5642 chars |

### Compatibilità con i parametri del notebook

Il notebook imposta:
- `max_prompt_length = 3072` tokens
- `max_length = 3584` tokens

> [!WARNING]
> I prompt contengono 3 chunk RAG completi + system prompt → in media ~4580 caratteri → ~1300 tokens. I prompt più lunghi (5642 chars → ~1600 tokens) rientrano nel limite di 3072, ma **lo spazio residuo per le risposte è solo ~1500-2000 tokens** (`max_length - prompt_length`). Le rejected più lunghe (4047 chars → ~1150 tokens) dovrebbero rientrare, ma monitorare i troncamenti durante il training.

### Volume dataset

Con **379 esempi** e 2 epoche → il modello vedrà ~758 coppie di preferenza. Per un modello 3B in QLoRA questo è:
- ✅ **Sufficiente** per insegnare pattern chiari (rifiuto OOD, stile di registro)
- ⚠️ **Al limite** per generalizzare bene su tutti i 60 source documents

---

## 5. Duplicati — ✅ Non problematico

Le 47 domande duplicate sono **tutte OOD** ripetute su livelli utente diversi (es. "Quali sono i sintomi dell'influenza stagionale?" × A, B, C). Questo è **corretto e intenzionale**: la stessa domanda OOD con system prompt di livello diverso genera rejected diversi. L'ID è sempre unico.

---

## 6. Metadati extra — ✅ Non interferiscono

I campi `id`, `strategy`, `user_level`, `sources`, `context_levels`, `source_chunk_file`, `created_at` sono presenti ma il notebook li ignora correttamente con:
```python
dataset = raw.select_columns(["prompt", "chosen", "rejected"])
```

---

## Verdetto Finale

| Criterio | Voto | Note |
|---|---|---|
| **Compatibilità formato** | 🟢 10/10 | Perfettamente allineato con DPOTrainer/TRL |
| **Qualità segnale DPO** | 🟢 9/10 | Contrasto chosen/rejected fortissimo e non ambiguo |
| **Copertura strategie** | 🟢 8/10 | Buon bilanciamento, OOD leggermente sottorappresentato |
| **Bilanciamento livelli** | 🟢 8/10 | 81–109 per livello, accettabile |
| **Rischio length bias** | 🟡 6/10 | 86.8% chosen più corti — proxy spurio possibile |
| **Volume dati** | 🟡 7/10 | 379 è sufficiente per QLoRA su 3B, ma non abbondante |
| **Lunghezza prompt** | 🟢 8/10 | Rientra nei limiti, monitorare troncamenti |

### ✅ Valutazione complessiva: **BUONO — pronto per il training**

Il dataset è ben costruito, il formato è corretto, e la qualità del segnale di preferenza è alta. I due aspetti da tenere d'occhio sono:

1. **Length bias**: se dopo il training noti che il modello tende a dare risposte troppo corte indipendentemente dal contesto, valuta di aggiungere ~20-30 coppie dove il chosen è più lungo/dettagliato del rejected
2. **OOD coverage**: con 66 esempi la policy di rifiuto dovrebbe essere appresa (il segnale è pulitissimo), ma se il tasso di rifiuto in produzione è basso, aggiungi altri esempi OOD
