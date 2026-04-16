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
            device="cpu" # Metti "cpu" se non hai una GPU Nvidia
        )
        
        self.collection = self.client.get_collection(
            name="rag_knowledge_base",
            embedding_function=self.bge_ef
        )
        print("✓ Database Vettoriale connesso.")

        # --- STADIO 2: Inizializzazione Cross-Encoder (Re-Ranker) ---
        self.reranker = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            device="cpu" # Metti "cpu" se non hai una GPU Nvidia
        )
        print("✓ Re-Ranker caricato.\n")

    # In src/retrieval.py, aggiorna il metodo search:

    # Cambia user_query in una lista (es. [query_ita, query_eng])
    def search(self, user_queries: list, user_level: str = None, initial_k: int = 20, final_k: int = 3):
        where_filter = {"difficulty_level": user_level} if user_level else None

        # Passiamo l'intera lista di varianti a ChromaDB
        raw_results = self.collection.query(
            query_texts=user_queries, 
            n_results=initial_k,
            where=where_filter
        )
        
        # Uniamo tutti i documenti trovati (Chroma restituisce una lista di liste)
        all_texts = []
        all_metadatas = []
        for doc_list, meta_list in zip(raw_results['documents'], raw_results['metadatas']):
            all_texts.extend(doc_list)
            all_metadatas.extend(meta_list)

        if not all_texts:
            return []

        # Rimuoviamo eventuali duplicati (se sia la query ITA che ENG hanno pescato lo stesso chunk)
        unique_docs = []
        seen_texts = set()
        for t, m in zip(all_texts, all_metadatas):
            if t not in seen_texts:
                seen_texts.add(t)
                unique_docs.append({"text": t, "metadata": m})

        # Stadio 2: Re-Ranking
        # Usiamo la primissima query (quella originale dell'utente) per dare il voto finale
        original_query = user_queries[0] 
        query_text_pairs = [[original_query, doc["text"]] for doc in unique_docs]
        scores = self.reranker.predict(query_text_pairs)

        ranked_results = []
        for i, doc in enumerate(unique_docs):
            ranked_results.append({
                "text": doc["text"],
                "source": doc["metadata"].get("source_file"),
                "title": doc["metadata"].get("title"),
                "score": float(scores[i])
            })

        ranked_results.sort(key=lambda x: x["score"], reverse=True)
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