# Materiale trasferito nel repository

Questa cartella raccoglie la campagna finale prima conservata in outputs/dpo_pdf_600.
I dati, i giudizi e i log non sono stati ricalcolati. I percorsi assoluti nei manifest
sono provenienza storica e possono riferirsi al PC originario. Gli hash degli script
nei manifest identificano le versioni usate nei run, non necessariamente le ricette
di avvio rese portabili successivamente.

## Percorso consigliato

1. `relazione_approfondita/AstroTutor_relazione_esame.pdf`: relazione da leggere (14 pagine).
2. `evaluation/final_groq_v1/REPORT.md`: riepilogo quantitativo finale.
3. `PROTOCOLLO_TEST_COMUNE.md`: condizioni del confronto.
4. `dataset_consegna/`: 600 coppie sintetiche, 75 domande e provenienza.
5. `runs/`: configurazioni e log; pesi degli adapter esclusi da Git.
6. `streamlit_app/`: interfaccia locale; istruzioni portabili nel README_COLLEGA.md alla radice.

Le cartelle automatico, facts_first, rich_contexts e dataset_v* documentano tentativi
precedenti, non il dataset finale. Le copie estese contexts_*.json di tali tentativi,
ridondanti con il corpus locale, sono escluse. Sono esclusi cache, pesi, checkpoint,
errori API con identificativi dell’account, file temporanei e ZIP duplicati.

Il corpus PDF e l’indice Chroma restano locali, come nel progetto originale.
Gli adapter sono necessari per la demo DPO: si possono trasferire separatamente
dal PC originario nelle corrispondenti cartelle runs/*/adapter oppure rigenerare.
I risultati si possono leggere senza GPU, pesi, chiavi API o nuovi training.

Il campione human_review.md va letto senza consultare human_review_key.json o
private_mapping.json prima di annotare i voti. Le valutazioni finali sono IA,
non una validazione umana indipendente.
