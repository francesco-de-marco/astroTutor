from src.generation import RAGGenerator

BASE_MODEL = "qwen2.5:3b"
DPO_MODEL = "astrotutor-dpo"

def main():
    print(f"Avvio del Test Comparativo ({BASE_MODEL} vs {DPO_MODEL}, entrambi con RAG)...\n")
    gen_base = RAGGenerator(model_name=BASE_MODEL)
    gen_dpo = RAGGenerator(model_name=DPO_MODEL)

    while True:
        try:
            query = input("\n🧐 Fai una domanda (es. 'Cosa succede se cado in un buco nero?'): ").strip()
            if not query: continue
            if query.lower() in ['esci', 'exit', 'quit']: break

            livello = input("🎓 Livello (A=Bambini, B=Medie, C=Superiori, D=Uni) [B]: ").strip().upper()
            if livello not in ['A', 'B', 'C', 'D']: livello = 'B'

            # VERSIONE 1: MODELLO BASE
            print("\n" + "="*60)
            print(f"1️⃣ VERSIONE 1: {BASE_MODEL} + RAG")
            print("="*60)
            risposta_base = gen_base.generate(query, user_level=livello)
            print(risposta_base)

            # VERSIONE 2: MODELLO DPO
            print("\n" + "="*60)
            print(f"2️⃣ VERSIONE 2: {DPO_MODEL} + RAG")
            print("="*60)
            risposta_dpo = gen_dpo.generate(query, user_level=livello)
            print(risposta_dpo)
            print("\n" + "-"*60)

        except KeyboardInterrupt:
            print("\nUscita in corso...")
            break

if __name__ == "__main__":
    main()
