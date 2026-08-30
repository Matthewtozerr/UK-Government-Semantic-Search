import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import fitz
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin

from src.data.config.config import main_config

cfg = main_config()

input_dir = Path(cfg["metadata_dir"])
output_dir = Path(cfg["text_dir"])
output_dir.mkdir(parents=True, exist_ok=True)
pdf_cache_dir = Path(cfg["cache_dir"]) / "pdf"
pdf_cache_dir.mkdir(parents=True, exist_ok=True)
html_cache_dir = Path(cfg["cache_dir"]) / "html"
html_cache_dir.mkdir(parents=True, exist_ok=True)

log_file = output_dir / "extract_text.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

request_delay = cfg["request_delay"]

def create_session():

    session = requests.Session()
    # 429 = rate limited
    # 500 = server error
    # 502 = bad gateway
    # 503 = service unavailable
    # 504 = gateway timeout
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": "UK-Government-Semantic-Search/1.0"
    })

    return session

session = create_session()

def full_url(url):
    if not url:
        return None
    
    return cfg["doc_url_prefix"] + url

def get_html(url, id):

    cache_file = html_cache_dir / f"{id}.html"

    if cache_file.exists():
        logger.info(f"Using cached HTML for {id}")

        return cache_file.read_text(encoding="utf-8")

    response = session.get(url)
    response.raise_for_status()

    html = response.text

    cache_file.write_text(html, encoding="utf-8")

    time.sleep(request_delay)

    return html

def find_pdf_link(soup, page_url):

    pdf_links = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        full_url = urljoin(page_url, href)

        if ".pdf" in href.lower():
            pdf_links.append(full_url)
    
    return pdf_links

def extract_html_text(soup):

    main = soup.find("main")

    if not main:
        return None
    
    for element in main.find_all(["script", "style", "nav"]):
        element.decompose()

    text = main.get_text(separator="\n", strip=True)

    return text
        
def get_pdf(url, id):

    filename = f"{id}.pdf"
    cache_file = pdf_cache_dir / filename

    if cache_file.exists():
        logger.info(f"Using cached PDF for {id}")

        return cache_file
    
    response = session.get(url)
    response.raise_for_status()

    cache_file.write_bytes(response.content)

    time.sleep(request_delay)

    return cache_file

def extract_pdf_text(pdf_path):
    
    document = fitz.open(pdf_path)

    pages = []

    for page in document:
        text = page.get_text()

        if text:
           pages.append(text)

    document.close()

    return "\n".join(pages)

def process_documnet(document):

    title = document.get("title")
    url = document.get("link")
    id = document.get("id")

    if not url:
        logger.warning(f"No URL found for document '{title}'")
        return None
    
    url = full_url(url)
    logger.info(f"Processing document '{title}' [{id}]")

    try:
        html = get_html(url, id)

        soup = BeautifulSoup(html, "html.parser")

        pdf_links = find_pdf_link(soup, url)
        if pdf_links:
            logger.info(f"Found {len(pdf_links)} PDF link(s) for document '{title}' [{id}]")
            for link in pdf_links:
                pdf_path = get_pdf(link, id)
                text = extract_pdf_text(pdf_path)
                source_type = "pdf"
                source_url = link

        else:
            text = extract_html_text(soup)
            source_type = "html"
            source_url = url
            if not text or len(text.strip()) < 100:
                logger.warning(f"Insufficient text extracted for document '{title}' [{id}]")
                return None
        
        return {
            "id": id,
            "title": title,
            "source_url": source_url,
            "source_type": source_type,
            "text": text
        }
    
    except Exception as e:
        logger.exception(f"Failed to process document '{title}' [{id}]: {e}")
        return None
                
def main():

    all_documents = []

    seen_urls = set()

    json_files = list(input_dir.glob("*.json"))

    for file in json_files:
        field = file.stem

        with open(file, encoding="utf-8") as f:
            documents = json.load(f)

        success_count = 0
        failure_count = 0   
        duplicate_count = 0

        for document in documents:
            url = document.get("link")
            title = document.get("title")
            id = document.get("id")
            if url in seen_urls:
                duplicate_count += 1
                logger.info(f"Skipping duplicate document '{title}' [{id}]")
                continue
            
            seen_urls.add(url)

            processed_doc = process_documnet(document)

            if processed_doc:
                success_count += 1
                all_documents.append(processed_doc)
            else:
                failure_count += 1
        
        logger.info(f"Field '{field}':\n"
                    f"{success_count} documents processed successfully,"
                    f"{failure_count} failures,"
                    f"{duplicate_count} duplicates")
    
    with open(output_dir / "documents.json", "w", encoding="utf-8") as f:
        json.dump(all_documents, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Total unique documents: {len(all_documents)}")

if __name__ == "__main__":
    main()