import requests
import json
from pathlib import Path

API_URL = "https://www.gov.uk/api/search.json"

fields = [
    "energy",
    "health",
    "transport",
    "education",
    "environment",
    "treasury",
    "defence",
    "business",
    "housing",
    "science",
    "technology",
    "climate"]

formats = {
    "research",
    "independent_report",
    "policy_paper",
    "official_statistics",
    "national_statistics",
    "statistical_data_set",
    "guidance",
    "statutory_guidance",
    "regulation",
    "manual",
    "manual_section",
    "decision",
    "transparency",
    "correspondence",
    "speech",
    "press_release",
    "news_story",
    "corporate_report",
    "guide",
    "detailed_guide",
}

target = 100
batch = 20

OUTPUT_DIR = Path("./data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for field in fields:
    docs = []
    start = 0

    while len(docs) < target:

        params = {
            "q": field,
            "count": batch,
            "start": start,
            "order": "-public_timestamp",
        }

        response = requests.get(API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        if not results:
            print(f"No more results for field '{field}' after {len(docs)} documents.")
            break

        for item in results:
            if item.get("format") not in formats:
                continue

            filtered_results = {
                "id": f"{field}_{len(docs)}",
                "title": item.get("title"),
                "link": item.get("link"),
                "description": item.get("description"),
                "format": item.get("format"),
                "document_type": item.get("document_type"),
                "organisations": item.get("organisations"),
                "public_timestamp": item.get("public_timestamp")
            } 

            docs.append(filtered_results)

            if len(docs) >= target:
                break

        start += batch

    docs = docs[:target]

    with open(f"{OUTPUT_DIR}/{field}.json", "w") as f:
        json.dump(docs, f, indent=4)


