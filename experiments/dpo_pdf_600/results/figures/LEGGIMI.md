# Grafici per la relazione AstroTutor

18 figure in PNG (220 dpi) e SVG vettoriale. Fascicolo PDF con didascalie. Nessuna nuova chiamata API.

## Figure consigliate nel corpo della relazione
01 loss; 07 correttezza; 09 dimensioni qualitative; 10 adeguatezza per livello; 13 lunghezza; 15 incertezza. Le altre figure sono adatte ad approfondimenti o appendici.

## Conclusione prudente
La correttezza stimata migliora in cinque modelli su sei, mentre l'adeguatezza al livello non migliora uniformemente. Le risposte diventano più brevi e talvolta meno complete. I dati non sostengono una conclusione generale di inutilità del DPO, né provano efficacia nell'apprendimento.

## Limiti da mantenere nelle didascalie
Un giudice IA, nessuna revisione umana indipendente, un seed per training. 600 coppie derivano da 75 domande; il test ha 20 domande su 10 brani. Le varianti non sono indipendenti. Non ci sono curve di validation né un confronto SFT in questa fase.

## 01_training_loss - Loss DPO durante il training
La loss misura l'obiettivo di preferenza sul training. Una loss più bassa non prova correttezza, qualità didattica o generalizzazione; le scale tra modelli non costituiscono una classifica di qualità. Linea tenue: dati grezzi; linea piena: media mobile retrospettiva di 20 step (finestra ridotta all'inizio). Linea verticale: fine prima epoca.

## 02_training_preference_accuracy - Accuratezza delle preferenze sul training
Quota di esempi per cui il reward implicito della risposta preferita supera quello della rifiutata. Non è accuratezza scientifica sul test. Linea tenue: dati grezzi; linea piena: media mobile retrospettiva di 20 step (finestra ridotta all'inizio). Linea verticale: fine prima epoca.

## 03_training_margin - Margine di preferenza durante il training
Il margine confronta i reward impliciti rispetto al modello di riferimento. Valori positivi indicano maggiore preferenza per chosen; non sono voti di un docente. Linea tenue: dati grezzi; linea piena: media mobile retrospettiva di 20 step (finestra ridotta all'inizio). Linea verticale: fine prima epoca.

## 04_training_gradients - Norma dei gradienti registrata
Diagnostica dell'ottimizzazione: non è una misura di qualità delle risposte. Il valore registrato può precedere il clipping e superarne la soglia. Linea tenue: dati grezzi; linea piena: media mobile retrospettiva di 20 step (finestra ridotta all'inizio). Linea verticale: fine prima epoca.

## 05_training_rewards - Reward impliciti: chosen e rejected
Dati grezzi e media mobile di 20 step. Reward relativi al riferimento, non giudizi esterni di correttezza.

## 06_learning_rate - Learning rate: controllo della configurazione
Il learning rate è uguale e costante nei sei run. Non è stata effettuata una ricerca degli iperparametri separata per ciascun modello.

## 07_correctness - Correttezza stimata: base e DPO
80 risposte per condizione e modello. C indica nucleo corretto e assenza di errori sostanziali secondo il giudice IA. Non sono 80 domande indipendenti.

## 08_correct_partial_incorrect - Distribuzione dei giudizi C / P / I
Altezza delle barre in percentuale; numeri interni = conteggi su 80. Le piccole categorie senza etichetta restano incluse.

## 09_quality_dimensions - Qualità delle risposte oltre la correttezza
Medie descrittive di voti ordinali da 0 a 2. Correttezza e adattamento didattico sono dimensioni diverse: un miglioramento della prima non implica quello della seconda.

## 10_adequacy_by_level - Adeguatezza per livello scolastico
A: primaria; B: medie; C: superiori; D: università. 20 risposte per cella. A destra differenza dei voti medi (scala 0-2); non è una misura di apprendimento.

## 11_correctness_by_level - Correttezza per livello scolastico
Percentuale di risposte C su 20 per cella. A destra differenza in punti percentuali. Le quattro versioni della stessa domanda sono dipendenti.

## 12_preferences - Preferenze derivate dai voti
Regola lessicografica: correttezza, completezza, adeguatezza, chiarezza. Non è una seconda valutazione indipendente; sono mantenute le parità.

## 13_response_length - Distribuzione della lunghezza delle risposte
Box: quartili 25-75%; linea: mediana; baffi: 1,5 IQR; punti: valori esterni. Sono incluse le risposte al limite di token. La brevità non è di per sé un miglioramento.

## 14_token_limits - Risposte che raggiungono il limite di token
Flag limite_token_senza_EOS: possibile troncamento, non certezza di errore. Limite comune: 384 nuovi token. Tutti questi casi sono inclusi nella valutazione.

## 15_correctness_uncertainty - Differenze di correttezza e incertezza esplorativa
Intervalli bootstrap percentili al 95%, 5.000 ricampionamenti di 10 brani. Non includono errore del giudice, variabilità tra seed o dipendenze tra brani dello stesso PDF. Nessuna correzione per confronti multipli: non etichettare come prova definitiva di significatività.

## 16_training_resources - Risorse registrate durante il training
Tempi del trainer: escludono download e possono escludere preparazione/precalcolo. VRAM allocata da PyTorch, non memoria totale della GPU. Stessa RTX 4070 Laptop, ma condizioni operative non controllate: confronto descrittivo, non benchmark di velocità.

## 17_correctness_transitions - Come cambiano i giudizi sulle stesse domande
Conteggi appaiati su 80 prompt per modello. Righe: base; colonne: DPO. La diagonale indica classe invariata; C/P/I indicano corretto/parziale/errato secondo il giudice.

## 18_topic_differences - Variazioni di correttezza per argomento
Solo 8 risposte per condizione e argomento: due domande a quattro livelli. Un singolo caso vale 12,5 punti percentuali. Usare per descrivere eterogeneità, non per classificare la competenza su interi argomenti.
