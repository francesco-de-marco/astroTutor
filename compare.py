from src.generation import RAGGenerator

def main():
    print("Avvio del Test Comparativo (Baseline vs RAG)...\n")
    generator = RAGGenerator(model_name="qwen2.5:3b") 

    while True:
        try:
            query = input("\n🧐 Fai una domanda (es. 'Cosa succede se cado in un buco nero?'): ").strip()
            if not query: continue
            if query.lower() in ['esci', 'exit', 'quit']: break
            
            livello = input("🎓 Livello (A=Bambini, B=Medie, C=Superiori, D=Uni) [B]: ").strip().upper()
            if livello not in ['A', 'B', 'C', 'D']: livello = 'B'
                
            # TEST 1: SENZA RAG (Baseline)
            print("\n" + "="*60)
            print("❌ VERSIONE 1: SENZA RAG (Solo memoria di Qwen2.5)")
            print("="*60)
            risposta_base = generator.generate_without_rag(query, user_level=livello)
            print(risposta_base)
            
            # TEST 2: CON RAG
            print("\n" + "="*60)
            print("✅ VERSIONE 2: CON RAG (Basato sui tuoi PDF)")
            print("="*60)
            risposta_rag = generator.generate(query, user_level=livello)
            print(risposta_rag)
            print("\n" + "-"*60)
            
        except KeyboardInterrupt:
            print("\nUscita in corso...")
            break

if __name__ == "__main__":
    main()