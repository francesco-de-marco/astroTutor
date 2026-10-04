# Decisione sulle tre coppie recuperabili

Revisione locale dell’assistente del 26 settembre 2026. Nessuna nuova richiesta Groq. Non è una verifica umana o indipendente, né un certificato di correttezza scientifica.

| Coppia | Decisione | Motivo |
|---|---|---|
| Hawking e segnali alieni (B) | Scartare dal lotto didattico | Il confronto è soprattutto ricostruzione di un’opinione e completezza dell’analogia storica. Non emerge una differenza di prerequisiti abbastanza solida. |
| Nube di Oort (C) | Riscrivere come esempio di riferimento | La domanda originale introduce la classe “lungo periodo” non nominata nel brano; una risposta aggiunge orbite “molto ellittiche” e l’altra contiene marcatori di evidenza. La nuova domanda riguarda soltanto perturbazione e avvicinamento descritti dalla fonte. |
| Fossa gravitazionale (D) | Scartare | Entrambe sviluppano l’analogia divulgativa senza fornire una spiegazione universitaria fondata. La preferenza per l’analogia non basta a stabilire migliore adeguatezza al livello D. |

## Esito

Nessuna delle tre coppie originali è promossa automaticamente a training. È disponibile un esempio riscritto, ancora etichettato come bozza dell’assistente. L’esperimento originale e le sue etichette restano intatti.

## Esempio riscritto: nube di Oort

Come può il passaggio di una stella portare un oggetto della nube di Oort vicino al Sole?

### Risposta proposta come preferita per C

La nube di Oort è una riserva di antichi oggetti ghiacciati che orbitano lontano dal Sole, vicino al limite della sua sfera di influenza: la regione in cui la sua gravità può mantenere oggetti in orbita. A quelle distanze, la gravità di una stella di passaggio può perturbare, cioè modificare, la loro orbita. Alcune delle nuove orbite portano gli oggetti molto più vicino al Sole, dove possiamo osservarli come comete. Non tutti hanno questo destino: altri possono essere allontanati definitivamente dal sistema solare.

### Alternativa

La gravità di una stella di passaggio può cambiare il percorso di un oggetto ghiacciato della nube di Oort. Il nuovo percorso può portarlo vicino al Sole, dove possiamo vederlo come cometa. Altri oggetti possono invece lasciare il sistema solare.

### Motivazione proposta

La prima esplicita il ruolo della posizione periferica e definisce sfera di influenza e perturbazione; la seconda riporta solo la sequenza essenziale. Preferenza proposta per C, non misurata.

## Implicazione operativa

Non avviare produzione massiva. La prova ha identificato problemi nel generatore e nel giudice; non ha valutato il DPO. La verifica delle affermazioni separata richiede ancora un verificatore semantico: quality_gate.py ne controlla soltanto lo schema, le citazioni letterali e la copertura del testo, non sa dimostrare che una citazione sostenga l’affermazione. Non presentare tale controllo come soluzione già completa.
