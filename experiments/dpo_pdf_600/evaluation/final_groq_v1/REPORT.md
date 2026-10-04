# AstroTutor: confronto finale esplorativo

**Valutazione automatica con openai/gpt-oss-120b (groq); nessuna validazione umana indipendente.**

Sei modelli, 600 coppie sintetiche di training, 20 domande di test a quattro livelli: 80 prompt e 160 risposte per modello. Le varianti non sono osservazioni indipendenti.

| Modello | Corrette C base /80 | Corrette C DPO /80 | Delta punti % | Preferenze DPO/base/parita* |
|---|---:|---:|---:|---:|
| HuggingFaceTB/SmolLM3-3B | 69 | 66 | -3.75 | 10/12/58 |
| Qwen/Qwen2.5-1.5B-Instruct | 40 | 42 | +2.50 | 25/18/37 |
| Qwen/Qwen2.5-3B-Instruct | 63 | 67 | +5.00 | 18/18/44 |
| google/gemma-3-1b-it | 38 | 47 | +11.25 | 28/21/31 |
| meta-llama/Llama-3.2-3B-Instruct | 50 | 63 | +16.25 | 26/21/33 |
| mistralai/Mistral-7B-Instruct-v0.3 | 73 | 79 | +7.50 | 7/21/52 |

*Preferenza derivata dai voti, in ordine: correttezza, completezza, adeguatezza, chiarezza. Non e una seconda valutazione indipendente.

## Interpretazione e limiti

I numeri stimano la qualita delle risposte secondo un singolo giudice IA. Non dimostrano efficacia didattica sugli studenti o utilita generale del DPO. La prima prova locale con Qwen 7B e stata fermata per giudizi inaffidabili; quei sei voti non sono inclusi nella valutazione Groq.

I dati di training sono scritti dall'assistente: 75 domande, quattro livelli e due risposte rifiutate per prompt. Le 600 coppie non sono 600 domande indipendenti. I negativi includono errori fattuali e risposte fuori tema: il test non isola l'adattamento al livello. Non e stato eseguito un braccio SFT in questo confronto.

Il test usa contesti italiani riformulati dall'assistente, provenienti da documenti tenuti separati dal training. Non misura il recupero RAG. I dettagli sono nel protocollo originale. Non sono stati modificati prompt, training o risposte dopo il test.

Sono incluse tutte le risposte, comprese quelle al limite di token. I controlli elementari del giudice non costituiscono una validazione della sua affidabilita su queste 960 risposte. Un campione di 24 coppie e predisposto per revisione umana; finche non compilato i risultati restano automatici.

Intervalli esplorativi: bootstrap di dieci gruppi di contesto; non coprono errore del giudice, dipendenze fra brani dello stesso PDF o variabilita fra seed di training. Nessuna correzione per confronti multipli; nessuna dichiarazione automatica di significativita.

## HuggingFaceTB/SmolLM3-3B

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 69/8/3 | 1.925 | 1.900 | 1.900 | 117.4 | 10 | 0 |
| dpo | 66/11/3 | 1.925 | 1.900 | 1.913 | 83.6 | 2 | 0 |

Delta correttezza: -3.75 punti percentuali; intervallo bootstrap esplorativo 95%: [-16.25, 10.0].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 17/16 | 1.95/1.80 |
| B | 18/17 | 1.90/1.95 |
| C | 17/16 | 1.90/1.90 |
| D | 17/17 | 1.85/1.95 |

## Qwen/Qwen2.5-1.5B-Instruct

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 40/22/18 | 1.438 | 1.475 | 1.500 | 76.3 | 2 | 0 |
| dpo | 42/18/20 | 1.475 | 1.488 | 1.625 | 52.0 | 0 | 0 |

Delta correttezza: +2.50 punti percentuali; intervallo bootstrap esplorativo 95%: [-10.0, 16.25].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 8/8 | 1.50/1.30 |
| B | 10/12 | 1.45/1.75 |
| C | 11/9 | 1.20/1.30 |
| D | 11/13 | 1.75/1.60 |

## Qwen/Qwen2.5-3B-Instruct

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 63/9/8 | 1.863 | 1.837 | 1.825 | 103.0 | 2 | 0 |
| dpo | 67/13/0 | 1.762 | 1.788 | 1.863 | 48.0 | 0 | 0 |

Delta correttezza: +5.00 punti percentuali; intervallo bootstrap esplorativo 95%: [-5.0, 15.0].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 16/16 | 1.85/1.95 |
| B | 17/16 | 1.85/1.65 |
| C | 17/17 | 1.80/1.70 |
| D | 13/18 | 1.85/1.85 |

## google/gemma-3-1b-it

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 38/22/20 | 1.450 | 1.375 | 1.525 | 89.4 | 5 | 0 |
| dpo | 47/19/14 | 1.413 | 1.413 | 1.613 | 54.8 | 0 | 0 |

Delta correttezza: +11.25 punti percentuali; intervallo bootstrap esplorativo 95%: [0.0, 23.75].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 12/13 | 1.60/1.60 |
| B | 13/12 | 1.50/1.35 |
| C | 6/10 | 1.05/1.20 |
| D | 7/12 | 1.35/1.50 |

## meta-llama/Llama-3.2-3B-Instruct

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 50/18/12 | 1.663 | 1.725 | 1.625 | 146.3 | 15 | 0 |
| dpo | 63/11/6 | 1.675 | 1.712 | 1.850 | 63.3 | 1 | 0 |

Delta correttezza: +16.25 punti percentuali; intervallo bootstrap esplorativo 95%: [3.75, 27.5].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 11/18 | 1.70/2.00 |
| B | 16/15 | 1.85/1.55 |
| C | 9/12 | 1.55/1.65 |
| D | 14/18 | 1.80/1.65 |

## mistralai/Mistral-7B-Instruct-v0.3

| Condizione | C/P/I | Completezza 0-2 | Adeguatezza 0-2 | Chiarezza 0-2 | Parole medie | Limite token | Giudizi incerti |
|---|---|---:|---:|---:|---:|---:|---:|
| base | 73/5/2 | 1.950 | 1.950 | 1.950 | 86.4 | 3 | 0 |
| dpo | 79/1/0 | 1.800 | 1.837 | 1.950 | 43.6 | 0 | 0 |

Delta correttezza: +7.50 punti percentuali; intervallo bootstrap esplorativo 95%: [2.5, 13.75].

| Livello | C base/DPO | Adeguatezza base/DPO |
|---|---:|---:|
| A | 19/20 | 2.00/2.00 |
| B | 17/20 | 1.90/1.65 |
| C | 19/20 | 2.00/1.80 |
| D | 18/19 | 1.90/1.90 |
