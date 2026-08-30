import requests
import json
from pathlib import Path
from src.data.config.config import main_config

cfg = main_config()

api_url = cfg["api_url"]
output_dir = Path(cfg["metadata_dir"])
output_dir.mkdir(parents=True, exist_ok=True)

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

target = cfg["no_docs_per_field"]
batch = cfg["no_docs_batch"]

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

        response = requests.get(api_url, params=params)
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

    with open(f"{output_dir}/{field}.json", "w") as f:
        json.dump(docs, f, indent=4)


