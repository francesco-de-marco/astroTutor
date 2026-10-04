# Qwen 3B: primo confronto di sviluppo dopo DPO su 600 coppie

Data: 26 settembre 2026. Training: 600 coppie sintetiche, 75 domande, due epoche, 300 aggiornamenti. Questa valutazione contiene 8 nuove domande a quattro livelli, da quattro brani di tre documenti esclusi dal training: 32 prompt e 64 risposte. È sviluppo, non test finale.

## Esito descrittivo

| Indicatore | Base NF4 | DPO NF4 |
|---|---:|---:|
| Risposte con nucleo corretto senza errori sostanziali individuati (C) | 6/32 | 13/32 |
| Parziali, ambigue o con imprecisioni rilevanti (P) | 13/32 | 12/32 |
| Nucleo errato o errore grave nella spiegazione (I) | 13/32 | 7/32 |
| Confronti preferiti | 1 | 14 |
| Parole medie, conteggio con split sugli spazi | 125,1 | 52,8 |
| Risposte vuote o interrotte per limite token segnalate dallo script | 0 | 0 |

I restanti 17 confronti sono parità. Parità non significa necessariamente buona risposta: comprende anche coppie con errori gravi in entrambe. La riduzione delle parole medie è circa il 58%; non è, da sola, un miglioramento didattico.

## Come è stato giudicato

L'assistente ha letto le 64 risposte presentate come Risposta 1 e Risposta 2, insieme alle domande e al contesto. Ha salvato `review_blind.json` prima di leggere `comparison_key.json`. Successivamente ha associato i giudizi alle condizioni base/DPO e prodotto `review_summary.json`.

Questa è una revisione qualitativa dell'IA, NON una valutazione umana indipendente. È lo stesso assistente coinvolto nella preparazione del dataset e delle domande. La cecità alla chiave riduce la conoscenza esplicita della condizione, ma non elimina la possibilità di riconoscerla dallo stile, né il bias dell'autore. Non è stato eseguito un ulteriore modello-giudice e non è stata effettuata una verifica scientifica esterna completa.

La rubrica C/P/I valuta il contenuto della risposta nel suo complesso, non soltanto la prima frase sì/no. Le motivazioni sono registrate per ciascun prompt. Le preferenze sono prudenti e privilegiano contenuto corretto e chiarezza. Non sono punteggi di efficacia educativa e non isolano la capacità di adeguarsi ai quattro livelli. Non confondere questi conteggi con metriche automatiche RAGAS dei vecchi esperimenti.

## Che cosa è cambiato e che cosa rimane problematico

Il DPO tende a produrre risposte più brevi, con meno ripetizioni e meno spiegazioni aggiuntive scorrette. Su alcune definizioni conserva meglio elementi essenziali come la caduta libera nei riferimenti inerziali locali e il significato di c nell'equazione massa-energia.

Rimangono fallimenti rilevanti. Sul paradosso dei gemelli, ai livelli A, C e D entrambe le condizioni sostengono erroneamente che i gemelli debbano aver vissuto lo stesso tempo. Al livello B il DPO apre correttamente, ma la spiegazione resta ambigua. Nelle risposte sulle maree gravitazionali compaiono termini inventati come accelerazione elettromagnetica o elettromotrice. Nei livelli alti la maggiore brevità può anche lasciare una spiegazione incompleta; nei livelli bassi persistono termini astratti non spiegati.

Il contesto stesso sull'equivalenza massa-energia contiene una formulazione impropria sulle stelle fin dall'inizio del tempo. Alcune risposte la ripetono. Fedeltà al documento e correttezza scientifica non coincidono sempre: il test definitivo deve usare contesti meglio controllati, conservando intatto questo risultato di sviluppo.

## Interpretazione e limiti

Il risultato sostiene questa affermazione limitata: su questo piccolo insieme di sviluppo, secondo la revisione dell'assistente, il DPO migliora diversi confronti e riduce la verbosità. Non sostiene che il DPO sia inutile, ma neppure dimostra un miglioramento robusto e generalizzabile.

Le 32 righe derivano da appena otto domande, correlate anche attraverso quattro brani e tre documenti. Non trattarle come 32 osservazioni indipendenti. Non sono stati calcolati test di significatività o intervalli di confidenza. I contenuti sono prevalentemente relativistici e tre dei quattro brani sono in inglese, mentre il tutor risponde in italiano. La difficoltà di questi temi per la primaria limita l'interpretazione dell'adeguatezza al livello.

Il training usa negativi sintetici evidenti e risposte preferite corte. Una parte del vantaggio può quindi derivare dal dire meno e limitare le occasioni di errore, anziché da una migliore comprensione. Per distinguere questi effetti servono valutazioni separate di correttezza, completezza e adattamento al livello.

## Passo successivo

Conservare questo run e questi giudizi. Preparare e congelare un insieme finale più ampio e rappresentativo prima di confrontare gli altri modelli; controllare contesti e risposte attese senza guardare gli output dei modelli. Usare gli stessi prompt, contesti e criteri per tutte le condizioni. Confrontare ogni modello base con il suo DPO; se si aggiunge SFT, trattarlo come condizione distinta.

Sul test finale riportare i risultati per domanda e livello, le regressioni e i limiti di una valutazione IA. Ottenere una revisione indipendente almeno su un campione se possibile. Le fonti del test finale non sono state usate in questo confronto.
