import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

INPUT_DIR = Path("./data/raw")

OUTPUT_DIR = Path("./data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_html(url):

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    main = soup.find("main")

    if main is None:
        return None

    return main.get_text(separator="\n", strip=True)

def process_documents(document):

    url = document.get("link")
    url = "https://www.gov.uk" + url

    try:
        text = extract_html(url)

        if not text:
            print(f"Failed to extract text from {document.get('title')}")
            return None
        
        return {
            "id": document.get("id"),
            "link": document.get("link"),
            "text": text
        }
    
    except Exception as e:
        print(f"  FAILED: {document['title']}")
        print(f"  {e}")

    return None

for file in INPUT_DIR.glob("*.json"):
    
    field = file.stem
    
    with open(file) as f:
        documents = json.load(f)

    processed_docs = []

    for document in documents:
        processed_doc = process_documents(document)
        if processed_doc:
            processed_docs.append(processed_doc)

    with open(OUTPUT_DIR / f"{field}.json", "w") as f:
        json.dump(processed_docs, f, indent=4)