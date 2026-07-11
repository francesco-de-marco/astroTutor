# -*- coding: utf-8 -*-
"""
ingest_api_data.py — Scarica contenuti educativi per livelli A e B da API pubbliche
================================================================================
Interroga le API di:
1. Vikidia (Italiano) — Enciclopedia per bambini 8-13 anni (Livello A)
2. Simple English Wikipedia — Wikipedia in inglese semplice (Livello A)
3. EduINAF (Italiano) — Portale di divulgazione didattica dell'INAF (Livello B)
4. astroEDU (Italiano) — Attività didattiche IAU (Livello A)

Formatta i dati in JSON compatibili con la pipeline RAG e li salva in:
data/processed/parsed/[TOPIC_FOLDER]/
"""

import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Errore: librerie 'requests' e 'beautifulsoup4' richieste. Installa con: pip install requests beautifulsoup4")

# ─── Configurazione Percorsi ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "parsed"

TOPIC_MAPPING = {
    1: "TOPIC 1 - Black Hole",
    2: "TOPIC 2 - Wormhole, viaggi nel tempo e spazio-tempo",
    3: "TOPIC 3 - Altri oggetti compatti e contesto cosmologico",
    4: "TOPIC 4 - Evoluzione stellare e supernovae",
    5: "TOPIC 5 - Galassie, ammassi e struttura a grande scala",
    6: "TOPIC 6 - Cosmologia Big Bang, espansione, materia oscura, energia oscura",
    7: "TOPIC 7 - Onde gravitazionali e astronomia multi-messaggero"
}

VIKIDIA_PAGES = [
    # NB: su Vikidia IT non esistono (verificato lug 2026): Wormhole, Onda gravitazionale,
    # Viaggio nel tempo, Supernova — i topic 2 e 7 sono coperti da Simple Wikipedia.
    {"page": "Buco nero", "topic": 1, "level": "A", "label": "bambini"},
    {"page": "Stella", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Galassia", "topic": 5, "level": "A", "label": "bambini"},
    {"page": "Sistema solare", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Gravità", "topic": 1, "level": "A", "label": "bambini"},
    {"page": "Stella di neutroni", "topic": 3, "level": "A", "label": "bambini"},
    {"page": "Sole", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Costellazione", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Via Lattea", "topic": 5, "level": "A", "label": "bambini"},
    {"page": "Big Bang", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Universo", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Pianeta", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Luna", "topic": 6, "level": "A", "label": "bambini"},
]

# Simple English Wikipedia: stessa API MediaWiki di Vikidia, inglese semplice per bambini.
# Copre i topic (2, 3, 7) dove Vikidia italiana non ha voci; bge-m3 è multilingue.
SIMPLEWIKI_PAGES = [
    {"page": "Black hole", "topic": 1, "level": "A", "label": "bambini"},
    {"page": "Gravity", "topic": 1, "level": "A", "label": "bambini"},
    {"page": "Wormhole", "topic": 2, "level": "A", "label": "bambini"},
    {"page": "Time travel", "topic": 2, "level": "A", "label": "bambini"},
    {"page": "Spacetime", "topic": 2, "level": "A", "label": "bambini"},
    {"page": "Neutron star", "topic": 3, "level": "A", "label": "bambini"},
    {"page": "White dwarf", "topic": 3, "level": "A", "label": "bambini"},
    {"page": "Pulsar", "topic": 3, "level": "A", "label": "bambini"},
    {"page": "Star", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Supernova", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Sun", "topic": 4, "level": "A", "label": "bambini"},
    {"page": "Galaxy", "topic": 5, "level": "A", "label": "bambini"},
    {"page": "Milky Way", "topic": 5, "level": "A", "label": "bambini"},
    {"page": "Big Bang", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Universe", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Dark matter", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Dark energy", "topic": 6, "level": "A", "label": "bambini"},
    {"page": "Gravitational wave", "topic": 7, "level": "A", "label": "bambini"},
    {"page": "LIGO", "topic": 7, "level": "A", "label": "bambini"},
]

EDUINAF_QUERIES = [
    {"query": "buco nero", "topic": 1, "level": "B", "label": "medie"},
    {"query": "wormhole", "topic": 2, "level": "B", "label": "medie"},
    {"query": "evoluzione stellare", "topic": 4, "level": "B", "label": "medie"},
    {"query": "galassia", "topic": 5, "level": "B", "label": "medie"},
    {"query": "materia oscura", "topic": 6, "level": "B", "label": "medie"},
    {"query": "onde gravitazionali", "topic": 7, "level": "B", "label": "medie"},
]

ASTROEDU_URLS = [
    {"url": "https://astroedu.iau.org/it/activities/costruisci-un-modello-di-buco-nero/", "page": "costruisci-buco-nero", "topic": 1, "level": "A", "label": "bambini"},
]

# ─── Utility Pulizia HTML ──────────────────────────────────────────────────
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.convert_charrefs = True
        self.text = []
    def handle_data(self, d):
        self.text.append(d)
    def get_data(self):
        return "".join(self.text)

def clean_html_content(html_content: str) -> str:
    # Rimuovi tag di stile, script e tag HTML non necessari
    html_content = re.sub(r'<(script|style).*?>.*?</\1>', '', html_content, flags=re.DOTALL|re.IGNORECASE)
    # Rimuovi link a categorie o template di Vikidia
    html_content = re.sub(r'<span class="mw-editsection">.*?</span>', '', html_content, flags=re.DOTALL)
    
    stripper = MLStripper()
    stripper.feed(html_content)
    text = stripper.get_data()
    
    # Pulizia spaziature e righe vuote multiple
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ─── Ingestion MediaWiki: Vikidia, Simple English Wikipedia (Livello A) ────
def fetch_mediawiki_page(api_url: str, page_title: str) -> str:
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "format": "json",
        "redirects": 1,
    }
    # Wikimedia richiede uno User-Agent descrittivo (altrimenti risponde 403)
    headers = {"User-Agent": "AstroTutor-RAG/1.0 (progetto didattico; demarcofrancesco02@gmail.com)"}
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if "parse" in data:
                return data["parse"]["text"]["*"]
            print(f"    [API] Pagina non trovata: '{page_title}' ({data.get('error', {}).get('code', '?')})")
        else:
            print(f"    [API] HTTP {response.status_code} per '{page_title}'")
    except Exception as e:
        print(f"Errore chiamata MediaWiki ({api_url}) per '{page_title}': {e}")
    return ""

def fetch_vikidia_page(page_title: str) -> str:
    return fetch_mediawiki_page("https://it.vikidia.org/w/api.php", page_title)

def fetch_simplewiki_page(page_title: str) -> str:
    return fetch_mediawiki_page("https://simple.wikipedia.org/w/api.php", page_title)

# Sezioni di servizio delle wiki: da questo titolo in poi il contenuto va scartato
WIKI_STOP_HEADINGS = {
    "references", "related pages", "other websites", "further reading", "sources",
    "note", "voci correlate", "collegamenti esterni", "bibliografia", "altri progetti",
}

def clean_wiki_html(html_content: str) -> str:
    """Pulizia specifica per pagine MediaWiki: rimuove infobox, tabelle, note
    e tronca alle sezioni di servizio (References, Voci correlate, ...)."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Elementi di puro rumore per il RAG
    for selector in ["table", "sup.reference", "span.mw-editsection", "div.navbox",
                     "div.thumb", "figure", "style", "script", "ol.references",
                     "div.reflist", "div.hatnote", "div.mw-references-wrap"]:
        for el in soup.select(selector):
            el.decompose()
    # Tronca il documento alla prima sezione di servizio
    for heading in soup.find_all(["h2", "h3"]):
        if heading.get_text(strip=True).lower().rstrip(":") in WIKI_STOP_HEADINGS:
            for el in list(heading.find_all_next()):
                el.decompose()
            heading.decompose()
            break
    # A capo solo alla fine dei blocchi (paragrafi, titoli, liste),
    # NON attorno ai link inline che spezzerebbero le frasi
    for block in soup.find_all(["p", "li", "h2", "h3", "h4"]):
        block.append("\n\n")
    text = soup.get_text()
    text = re.sub(r"\[\d+\]", "", text)  # eventuali marker di nota residui [1]
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ─── Ingestion EduINAF (Livello B) ─────────────────────────────────────────
def fetch_eduinaf_articles(query: str, max_articles: int = 2) -> list[dict]:
    url = "https://edu.inaf.it/wp-json/wp/v2/posts"
    params = {
        "search": query,
        "per_page": max_articles
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Errore chiamata EduINAF per '{query}': {e}")
    return []

# ─── Scraper astroEDU (Livello A/B) ────────────────────────────────────────
def scrape_astroedu(url: str) -> str:
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Cerchiamo la descrizione dell'attività (evitando footer e menu)
            content_div = soup.find('section', class_='activity-content') or soup.find('div', class_='activity') or soup.find('article')
            if content_div:
                return str(content_div)
            return response.text # Fallback
    except Exception as e:
        print(f"Errore scraping astroEDU per '{url}': {e}")
    return ""

# ─── Main Pipeline ─────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  INGESTION DATI DA API (EduINAF & Vikidia) - Avvio pipeline")
    print("=" * 70)
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. SCARICA DALLE WIKI (Livello A - Bambini): Vikidia + Simple English Wikipedia
    wiki_sources = [
        ("VIKIDIA", VIKIDIA_PAGES, fetch_vikidia_page, "vikidia", "Vikidia"),
        ("SIMPLE ENGLISH WIKIPEDIA", SIMPLEWIKI_PAGES, fetch_simplewiki_page, "simplewiki", "Simple Wikipedia"),
    ]
    for section_name, pages, fetch_fn, slug, source_label in wiki_sources:
        print(f"\n--- 1. SCARICAMENTO DA {section_name} (Livello A) ---")
        for item in pages:
            page = item["page"]
            topic_id = item["topic"]
            topic_folder = TOPIC_MAPPING[topic_id]

            dest_dir = PROCESSED_DIR / topic_folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / f"{item['level']} - api_{slug}_{page.lower().replace(' ', '_')}.json"

            if dest_file.exists():
                print(f"[{page}] File già presente, skip: {dest_file.name}")
                continue

            print(f"Scaricamento pagina {source_label}: '{page}' per {topic_folder}...")
            html_content = fetch_fn(page)

            if html_content:
                text = clean_wiki_html(html_content)

                # Formattazione JSON coerente con parsing.py
                output_data = {
                    "source_file": dest_file.name,
                    "topic_id": topic_id,
                    "topic_name": topic_folder.split(" - ", 1)[1],
                    "difficulty_levels": [item["level"]],
                    "difficulty_labels": [item["label"]],
                    "title": f"Spiegazione di {page} ({source_label})",
                    "num_pages": 1,
                    "text_markdown": f"# {page}\n\n{text}"
                }

                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                print(f"    -> Salvato in: {dest_file.name}")
            else:
                print(f"    [ERR] Fallito scaricamento '{page}'")
            
    # 2. SCARICA DA EDUINAF (Livello B - Medie)
    print("\n--- 2. SCARICAMENTO DA EDUINAF (Livello B) ---")
    for item in EDUINAF_QUERIES:
        query = item["query"]
        topic_id = item["topic"]
        topic_folder = TOPIC_MAPPING[topic_id]
        
        print(f"Ricerca articoli EduINAF per: '{query}' ({topic_folder})...")
        articles = fetch_eduinaf_articles(query, max_articles=2)
        
        if articles:
            for idx, art in enumerate(articles, 1):
                raw_title = art["title"]["rendered"]
                raw_html = art["content"]["rendered"]
                text = clean_html_content(raw_html)
                
                # Nome del file
                slug = art["slug"]
                filename = f"B - api_eduinaf_{slug}.json"
                
                dest_dir = PROCESSED_DIR / topic_folder
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / filename
                
                if dest_file.exists():
                    print(f"    -> [{idx}] Già presente, skip: {filename}")
                    continue
                
                # Formattazione JSON
                output_data = {
                    "source_file": filename,
                    "topic_id": topic_id,
                    "topic_name": topic_folder.split(" - ", 1)[1],
                    "difficulty_levels": [item["level"]],
                    "difficulty_labels": [item["label"]],
                    "title": raw_title,
                    "num_pages": 1,
                    "text_markdown": f"# {raw_title}\n\n{text}"
                }
                
                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                print(f"    -> [{idx}] Salvato in: {filename}")
        else:
            print(f"    [ERR] Nessun articolo trovato per '{query}'")

    # 3. SCARICA DA ASTROEDU (Livello A)
    print("\n--- 3. SCARICAMENTO DA ASTROEDU ---")
    for item in ASTROEDU_URLS:
        page = item["page"]
        topic_id = item["topic"]
        topic_folder = TOPIC_MAPPING[topic_id]
        
        dest_dir = PROCESSED_DIR / topic_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / f"A - api_astroedu_{page}.json"
        
        if dest_file.exists():
            print(f"[{page}] File già presente, skip: {dest_file.name}")
            continue
            
        print(f"Scraping astroEDU: '{page}' per {topic_folder}...")
        raw_html = scrape_astroedu(item["url"])
        
        if raw_html:
            text = clean_html_content(raw_html)
            output_data = {
                "source_file": dest_file.name,
                "topic_id": topic_id,
                "topic_name": topic_folder.split(" - ", 1)[1],
                "difficulty_levels": [item["level"]],
                "difficulty_labels": [item["label"]],
                "title": f"Attività astroEDU - {page}",
                "num_pages": 1,
                "text_markdown": f"# {page}\n\n{text}"
            }
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"    -> Salvato in: {dest_file.name}")
        else:
            print(f"    [ERR] Fallito scraping astroEDU '{page}'")
 
    print("\n" + "=" * 70)
    print("  Ingestion completata con successo! [OK]")
    print(f"  I file JSON sono pronti in: {PROCESSED_DIR}")
    print("  Ora esegui 'python src/chuncking.py' e 'python src/indexing.py' per aggiornare il RAG.")
    print("=" * 70 + "\n")
 
if __name__ == "__main__":
    main()
