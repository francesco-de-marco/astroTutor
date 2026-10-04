# Prova automatica limitata

Questa cartella contiene una prova su 20 nuovi contesti dello split TRAIN, non una produzione di 600 coppie. Nessuna annotazione umana richiesta per eseguirla.

- Generatore: openai/gpt-oss-120b su Groq.
- Giudice: qwen/qwen3.8-27b su Groq, senza accesso alla preferenza attesa, in ordine casuale.
- Il secondo autore riceve un profilo diverso e non vede la prima risposta. Il giudice valuta entrambe rispetto al profilo obiettivo.
- Sono usate solo evidenze estratte letteralmente dal contesto. Questo non certifica la correttezza del testo.
- Filtri locali: lunghezza, testo completo, formule/OCR frammentato, bibliografie, indizi di contenuto esplicativo. Il livello originale del documento guida l'assegnazione del profilo, ma resta una euristica.
- 5 contesti per livello, massimo 5 dallo stesso libro. Contesti gia provati esclusi. Nessun documento di sviluppo/test viene utilizzato.

## Limiti e ripresa

Massimo 20 candidati e 90 richieste HTTP complessive, inclusi errori e retry, anche dopo un riavvio. Questo e un limite di richieste, non una stima del costo in euro. Ogni richiesta limita l'output a 4096 token. I token riportati dal servizio sono registrati in usage.jsonl; richieste interrotte possono non fornire informazioni di consumo.

Un intervallo minimo di 12 secondi e i retry per HTTP 429 riducono le interruzioni. I limiti giornalieri possono comunque fermare la prova. La cache conserva le risposte per non ripagare le fasi gia completate. Non modificare codice o piano durante una prova: i relativi hash vengono verificati. Non cancellare il registro richieste per aggirare il budget.

Se dopo 10 candidati non ci sono accettazioni, viene scritto stopped.json e la prova si ferma definitivamente. Non parte automaticamente nessuna produzione estesa. Gli errori del servizio interrompono la prova; lo stesso comando permette la ripresa quando il problema esterno e risolto, entro il budget residuo.

## Esiti

summary.json riporta conteggi, livelli e richieste. attempts.jsonl conserva anche i rifiuti; accepted.jsonl contiene solo coppie che superano il controllo automatico. Le coppie sono sintetiche, non validate da esseri umani. Un giudice di famiglia diversa puo comunque condividere errori o introdurre preferenze proprie. Per il confronto futuro tra modelli, tenere conto anche del possibile favore del giudice verso la propria famiglia.

I 20 contesti sono diagnostici e non un test finale. Un buon tasso di accettazione non dimostra ne correttezza del dataset ne efficacia del DPO. Prima di scalare si devono esaminare gli esiti e i motivi degli scarti. Il vecchio lanciatore run_groq.ps1 resta in pausa; usare run_automatic.ps1.
