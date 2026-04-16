import json
import hashlib
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

# Configurazione percorsi (coerente con i tuoi script)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_DIR = PROJECT_ROOT / "data" / "processed" / "chunks"
DB_PATH = PROJECT_ROOT / "data" / "vector_db"

def initialize_indexing():
    # 1. Inizializziamo il client Chroma (persistente su disco)
    client = chromadb.PersistentClient(path=str(DB_PATH))
    
    # 2. Carichiamo BGE-m3 come funzione di embedding
    bge_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-m3",
        device="cuda" # o "cpu" se non hai una GPU
    )
    
    # 3. Creiamo o recuperiamo la collezione
    collection = client.get_or_create_collection(
        name="rag_knowledge_base",
        embedding_function=bge_ef,
        metadata={"hnsw:space": "cosine"} # BGE-m3 lavora bene con cosine similarity
    )
    return collection

def index_chunks(collection):
    # Trova tutti i file .jsonl generati da chunking.py
    jsonl_files = list(CHUNKS_DIR.rglob("*.jsonl"))
    
    for file_path in jsonl_files:
        print(f"Indicizzando: {file_path.name}")
        
        # Usiamo un dizionario per evitare ID duplicati nello STESSO batch.
        # Se c'è un duplicato nello stesso file, sovrascriverà semplicemente la chiave.
        batch_data = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                chunk = json.loads(line)
                testo = chunk['content']
                
                # Creiamo un ID univoco basato sull'HASH DEL TESTO
                chunk_id = hashlib.md5(testo.encode('utf-8')).hexdigest()
                
                # Salviamo nel dizionario
                batch_data[chunk_id] = {
                    "document": testo,
                    "metadata": chunk['metadata']
                }
        
        # Estraiamo i dati dal dizionario per passarli a ChromaDB
        ids = list(batch_data.keys())
        documents = [item["document"] for item in batch_data.values()]
        metadatas = [item["metadata"] for item in batch_data.values()]
        
        # Caricamento a batch nel vector store
        if ids:
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
    print("\nIndexing completato con successo! 🎉")
    print("Il database è ora deduplicato alla perfezione.")

if __name__ == "__main__":
    coll = initialize_indexing()
    index_chunks(coll)