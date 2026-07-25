# Risultati della valutazione

## Faithfulness media per livello

| Livello | Baseline qwen2.5:3b | DPO 378 triplette | DPO 623 triplette |
|---|---|---|---|
| A | 0.657 (n=10) | 0.498 (n=10) | 0.686 (n=10) |
| B | 0.687 (n=10) | 0.847 (n=10) | 0.798 (n=10) |
| C | 0.806 (n=10) | 0.796 (n=10) | 0.865 (n=10) |
| D | 0.568 (n=10) | 0.645 (n=10) | 0.563 (n=10) |
| **Media** | **0.679** | **0.697** | **0.728** |

## Gulpease medio per livello

| Livello | Banda attesa | Baseline qwen2.5:3b | DPO 378 triplette | DPO 623 triplette |
|---|---|---|---|---|
| A | 55-75 | 58.0 — 80% in banda | 57.4 — 80% in banda | 59.5 — 80% in banda |
| B | 45-65 | 52.3 — 90% in banda | 53.6 — 100% in banda | 51.2 — 100% in banda |
| C | 35-55 | 47.7 — 100% in banda | 49.3 — 90% in banda | 47.3 — 100% in banda |
| D | 25-45 | 46.6 — 40% in banda | 46.5 — 20% in banda | 46.8 — 60% in banda |

## Rifiuto fuori dominio

| Modello | Rifiuti corretti | Tasso |
|---|---|---|
| qwen2.5:3b | 10/20 | 50% |
| astrotutor-dpo | 9/20 | 45% |
| astrotutor-dpo-v2 | 14/20 | 70% |

> Nota: con n=10 domande per livello, differenze di faithfulness inferiori a ~0,10 non sono distinguibili dal rumore campionario.
