from src.generation import RAGGenerator
try:
    from config import LLM_MODEL
except ImportError:
    LLM_MODEL = "qwen2.5:3b"

def main():
    print("Avvio del RAG Tester...\n")
    
    # Assicurati di aver scaricato il modello su Ollama (es. ollama run qwen2.5:1.5b)
    try:
        generator = RAGGenerator(model_name=LLM_MODEL) 
    except Exception as e:
        print(f"Errore di inizializzazione: {e}")
        return

    print("\n" + "="*60)
    print("🚀 RAG TESTER INTERATTIVO ATTIVO")
    print("Premi Ctrl+C o scrivi 'esci' per terminare.")
    print("="*60)

    while True:
        try:
            query = input("\n🧐 Fai una domanda ai tuoi PDF: ").strip()
            if not query:
                continue
            if query.lower() in ['esci', 'exit', 'quit']:
                break
            
            livello = input("🎓 Scegli il livello (A=Bambini, B=Medie, C=Superiori, D=Uni) [Premi Invio per B]: ").strip().upper()
            if livello not in ['A', 'B', 'C', 'D']:
                livello = 'B'
                
            print(f"\nGenerazione in corso (Livello {livello})... ⏳\n")
            risposta = generator.generate(query, user_level=livello)
            
            print("\n" + "-" * 60)
            print(risposta)
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\nUscita in corso... Ciao!")
            break
        except Exception as e:
            print(f"\nSi è verificato un errore: {e}")

if __name__ == "__main__":
    main()