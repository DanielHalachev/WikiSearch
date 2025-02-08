import logging
import os
from pathlib import Path

import lmdb
import tomli
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wikisearch.autocomplete.autocompletion_service import AutocompletionService
from wikisearch.db.database_connection import DatabaseConnectionService
from wikisearch.document.document_service import DocumentService
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.usearch_semantic_index import USearchIndexService
from wikisearch.spell.hunspell_checker import HunSpellChecker

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WikiSearch')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000"]
)

path_to_config = Path("./config.toml")
with open(path_to_config, "rb") as f:
    config = tomli.load(f)

CRAWLER_CONFIG = {
    "domain": config["Crawler"].get("Domain", "bg.wikipedia.org"),
    "seed_urls": config["Crawler"].get("SeedURLs", "root"),
    "crawl_limit": config["Crawler"].get("CrawlLimit", ""),
}

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
}

LMDB_CONFIG = {
    "path": config["FileDatabase"].get("Path"),
    "size": config["FileDatabase"].get("Size", 10**9)
}

USEARCH_CONFIG = {
    "path": config["USearchIndex"].get("Path", "/data/WikiSearchData/SemanticIndex/usearch.index"),
    "dimension": config["USearchIndex"].get("Dimension", 768)
}

FAISS_CONFIG = {
    "path": config["FAISSIndex"].get("Path", "/data/WikiSearchData/SemanticIndex/faiss.index"),
    "dimension": config["FAISSIndex"].get("Dimension", 768)
}

SPELL_CONFIG = {
    "aff": config["SpellChecker"].get("AffPath"),
    "dic": config["SpellChecker"].get("DicPath"),
    "custom_path": config["SpellChecker"].get("CustomDicPath"),
}

AUTOCOMPLETION_CONFIG = {
    "word-completion-dawg": config["Autocompletion"].get("WordCompletionDAWG"),
    "next-word-dawg": config["Autocompletion"].get("NextWordDAWG"),
}

if not os.path.exists(LMDB_CONFIG["path"]):
    os.makedirs(LMDB_CONFIG["path"])
lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=int(LMDB_CONFIG["size"]))

with DatabaseConnectionService(DB_CONFIG) as connection:
    # add crawler service, if you want to add documents in runtime
    inverted_index_service = InvertedIndexService(connection)
    semantic_index_service = USearchIndexService(
        Path(USEARCH_CONFIG["path"]),
        int(USEARCH_CONFIG["dimension"]), 10)
    spell_checker_service = HunSpellChecker(
        Path(SPELL_CONFIG["aff"]),
        Path(SPELL_CONFIG["dic"]))
    autocompletion_service = AutocompletionService(
        AUTOCOMPLETION_CONFIG["word-completion-dawg"],
        AUTOCOMPLETION_CONFIG["next-word-dawg"], 10)
    document_service = DocumentService(connection, lmdb_env)


@app.get("/")
async def root():
    return {"message": "Welcome to WikiSearch"}


@app.get("/autocomplete")
async def autocomplete(q: str):
    if not q:
        return []
    else:
        return autocompletion_service.suggest(q)


@app.get("/search")
async def search(q: str, index: str = "inverted", limit: int = 20, offset: int = 0, spellcheck: bool = True):
    q = q.lower()
    old_q: str = q
    if spellcheck:
        q = spell_checker_service.spellcheck(q).lower()

    if index == "semantic":
        documents = semantic_index_service.search(q, limit, offset)
    else:
        documents = inverted_index_service.search(q, limit, offset)

    results = []
    for doc_id, score in documents:
        document = document_service.fetch_document(doc_id, score)
        results.append(document)

    return {
        "query": q,
        "index": index,
        "limit": limit,
        "offset": offset,
        "correction": (q != old_q),
        "results": results
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="localhost", port=8080)
