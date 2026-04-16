import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
from pathlib import Path

# ─── Configurazione Percorsi ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "vector_db"

class AdvancedRetriever:
    def __init__(self):
        print("Inizializzazione Retriever Avanzato...")
        
        # --- STADIO 1: Inizializzazione Bi-Encoder (ChromaDB) ---
        self.client = chromadb.PersistentClient(path=str(DB_PATH))
        
        # Usiamo bge-m3 per la trasformazione della domanda in vettore
        self.bge_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3",
            device="cuda" # Metti "cpu" se non hai una GPU Nvidia
        )
        
        self.collection = self.client.get_collection(
            name="rag_knowledge_base",
            embedding_function=self.bge_ef
        )
        print("✓ Database Vettoriale connesso.")

        # --- STADIO 2: Inizializzazione Cross-Encoder (Re-Ranker) ---
        self.reranker = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            device="cuda" # Metti "cpu" se non hai una GPU Nvidia
        )
        print("✓ Re-Ranker caricato.\n")

    def search(self, user_query: str, user_level: str = None, initial_k: int = 20, final_k: int = 3):
        """
        Esegue la ricerca a due stadi:
        1. Recupera 'initial_k' frammenti grezzi filtrando per livello.
        2. Usa il re-ranker per scegliere i migliori 'final_k'.
        """
        print(f"🔍 Domanda: '{user_query}' | Filtro Livello: {user_level}")
        
        # ==========================================
        # STADIO 1: Ricerca Vettoriale Grezza (Fast)
        # ==========================================
        where_filter = {"difficulty_level": user_level} if user_level else None

        raw_results = self.collection.query(
            query_texts=[user_query],
            n_results=initial_k,
            where=where_filter
        )
        
        # Estraiamo i documenti trovati (se non trova nulla, esce)
        if not raw_results['documents'] or not raw_results['documents'][0]:
            print("Nessun documento trovato nello Stadio 1.")
            return []

        retrieved_texts = raw_results['documents'][0]
        retrieved_metadatas = raw_results['metadatas'][0]

        # ==========================================
        # STADIO 2: Re-Ranking di Precisione (Slow)
        # ==========================================
        # Prepariamo le coppie [Domanda, Testo] da dare in pasto al Re-ranker
        query_text_pairs = [[user_query, text] for text in retrieved_texts]
        
        # Il Re-ranker legge ogni coppia e assegna un punteggio matematico
        scores = self.reranker.predict(query_text_pairs)

        # Creiamo una lista di dizionari con tutte le info (Testo, Metadati, Punteggio)
        ranked_results = []
        for i in range(len(retrieved_texts)):
            ranked_results.append({
                "text": retrieved_texts[i],
                "source": retrieved_metadatas[i].get("source_file"),
                "title": retrieved_metadatas[i].get("title"),
                "score": float(scores[i]) # Punteggio assegnato dal re-ranker
            })

        # Ordiniamo i risultati dal punteggio più alto a quello più basso
        ranked_results.sort(key=lambda x: x["score"], reverse=True)

        # Restituiamo solo i top 'final_k' risultati
        return ranked_results[:final_k]


# ─── Esempio di Test ──────────────────────────────────────────────
if __name__ == "__main__":
    retriever = AdvancedRetriever()
    
    # Facciamo una prova con una domanda volutamente vaga
    domanda_test = "Spiegami il concetto di orizzonte degli eventi in modo semplice."
    
    # Chiediamo i top 3 risultati per un utente delle medie (Livello B)
    # Lo stadio 1 ne pescherà 20, lo stadio 2 li riordinerà e terrà i 3 migliori.
    risultati_finali = retriever.search(
        user_query=domanda_test, 
        user_level="D", 
        initial_k=20, 
        final_k=3
    )
    
    print("\n" + "="*50)
    print("🏆 RISULTATI FINALI (Dopo il Re-Ranking):")
    print("="*50)
    
    for i, res in enumerate(risultati_finali, 1):
        print(f"\n[{i}] Da: {res['title']} (File: {res['source']})")
        print(f"Re-ranker Score: {res['score']:.4f}")
        print("-" * 30)
        # Stampiamo solo le prime 200 lettere per non intasare il terminale
        print(f"{res['text'][:200]}...")