
## Revisione attiva: dataset_v5

V4: 12 tentativi, 1 accettato automaticamente. La revisione del record de49ef4d2eaca90567caced5 trova una spiegazione sul disturbo della misura assente dal contesto. Non promuovere quella coppia come validata. Tutti i log e lo snapshot del codice V4 sono conservati.

V5 cambia il metodo: prima chiamata domanda e risposta per il profilo richiesto; seconda chiamata risposta alla stessa domanda per un profilo diverso, senza mostrare la prima risposta o richiedere difetti. Mappa profili A->D, B->D, C->A, D->B. Terza chiamata: controllo e confronto in ordine randomizzato rispetto al profilo richiesto. Si accetta solo se il giudice conferma la prima risposta come preferita e tutti i criteri. Pareggi e disaccordi si scartano. Il contrasto salvato deriva dal giudizio, non da una presunta differenza inventata dal generatore.

Modello unico GPT-OSS 120B: chiamate separate NON significa valutazione indipendente. Le coppie cross-profile possono essere troppo facili: misurare questo limite e includere in futuro casi piu vicini tra livelli. Numero di chiamate fino a 3 per candidato, oltre eventuali retry. Contesti e split restano identici, nessuna coppia precedente importata. Le prime 12 domande sono diagnostiche, non test finale. Prima della produzione verificare altri candidati e un campione manualmente.
