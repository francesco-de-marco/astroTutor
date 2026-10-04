# Esito: nucleo comune e approfondimenti

5 casi, 16 richieste, 1 accettazione automatica (B), 2 rifiuti didattici e 2 rifiuti fattuali. Nessuna richiesta aggiuntiva per questa lettura dell’assistente.

- Metodo osservativo: candidato conservato. Il giudice preferisce la risposta generata per il profilo alternativo, che esplicita il confronto fra previsioni e osservazioni. La preferenza inversa ora è gestita correttamente. Le risposte sono comunque vicine; la preferenza non prova calibrazione dei quattro livelli. Stato: candidato sintetico, non validato da esseri umani.
- Eclissi solare: contenuti e profondità molto simili. Rifiuto didattico ragionevole; non forzare una differenza.
- Stelle circumpolari: una risposta aggiunge una regola sulla declinazione assente dai fatti. Il giudice la rifiuta per supporto insufficiente, ma ne approva la correttezza: il suo controllo scientifico non va considerato affidabile solo perché il rifiuto finale è corretto.
- Metodi per fusioni: differenze prevalentemente sintattiche; una risposta include (ID 1), (ID 2), (ID 4) nel testo, l’altra manca della punteggiatura fra frasi. Non pronta per training, oltre al mancato contrasto didattico.
- Ultravioletto: una risposta aggiunge composizioni chimiche e fenomeni energetici non presenti nel contesto. L’altra parla dell’intero spettro UV, più forte di quanto sostenga il brano. Non recuperare la coppia semplicemente invertendo chosen/rejected.

## Conclusione limitata

La pipeline completa la prova e separa alcuni difetti fattuali dai pareggi didattici. Non è ancora dimostrata una resa sufficiente per 600 coppie di adattamento al livello. Il 20% riguarda solo questo piccolo campione selezionato e non è confrontabile direttamente con il 40% precedente. Non sono misure dell’efficacia del DPO.

Il candidato accettato è salvato separatamente in candidati_didattici.json con training_ready=false; nessun training è partito e gli output originali restano intatti. Non classificare i rifiuti fattuali come coppie di preferenza didattica. Un eventuale dataset che insegni anche correttezza/supporto è un obiettivo distinto, da dichiarare e valutare separatamente.

Non è stato preparato un altro smoke né aumentato il budget. Prima di una produzione più ampia occorre fissare una resa minima e un tetto di spesa, oppure ridurre la numerosità finale dichiarando il limite. Non raggiungere quota 600 duplicando o allentando retroattivamente i criteri.
