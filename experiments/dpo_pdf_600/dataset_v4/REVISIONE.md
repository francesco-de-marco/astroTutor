
## Revisione attiva: dataset_v4

Il lanciatore usa dataset_v4. dataset_v3 resta archiviato con snapshot del generatore. Conteggi: {"context_unsuitable": 3, "evidence_not_in_context": 6, "accepted": 2, "judge_quality_rejection": 1}. Le due accettazioni automatiche non sono importate: risposte artificiali e prerequisiti non spiegati nel campione.

Contesti e split invariati. Il modello sceglie evidence_ids; il codice estrae i passaggi originali. Il giudice verifica anche adeguatezza della preferita, naturalezza, domanda concettuale e supporto delle evidenze a entrambe le risposte. Lo screening non e indipendente e non certifica la correttezza. Nuovo smoke necessario prima della produzione.
