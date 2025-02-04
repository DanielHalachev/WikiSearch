import logging
import os
from pathlib import Path

import lmdb
import tomli
from fastapi import FastAPI

from wikisearch.db.DatabaseConnection import DatabaseConnectionService
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.semantic_index import SemanticIndexService
from wikisearch.nlp.nlp import NLPService
from wikisearch.spell.spellchecker_service import SpellCheckerService

logging.config.fileConfig('logging.conf')

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

app = FastAPI()

path_to_config = Path("./../../config.toml")
with open(path_to_config, "rb") as f:
    config = tomli.load(f)

CRAWLER_CONFIG = {
    "domain": config["Crawler"].get("Domain", "bg.wikipedia.org"),
    "seed_urls": config["Crawler"].get("SeedURLs", "root"),
    "crawl_limit": config["Crawler"].get("CrawlLimit", ""),
}

DB_CONFIG = {
    "host": config["Database"].get("Host", "localhost"),
    "user": config["Database"].get("User", "root"),
    "password": config["Database"].get("Password", ""),
    "database": config["Database"].get("Name", "crawler")
}

LMDB_CONFIG = {
    "path": config["FileDatabase"].get("Path", "./lmdb_store"),
    "size": config["FileDatabase"].get("Size", 10**9)
}

SEMANTIC_CONFIG = {
    "path": config["SemanticIndex"].get("Path", "/data/WikiSearchData/SemanticIndex"),
    "dimension": config["SemanticIndex"].get("Dimension", 768)
}

db_connection_service = DatabaseConnectionService(DB_CONFIG)
if not os.path.exists(LMDB_CONFIG.path):
    os.makedirs(LMDB_CONFIG.path)
lmdb_env = lmdb.open(LMDB_CONFIG.path, map_size=LMDB_CONFIG.size)

with db_connection_service.get_connection() as connection:
    inverted_index_service = InvertedIndexService(connection)
    semantic_index_service = SemanticIndexService(
        SEMANTIC_CONFIG.path, SEMANTIC_CONFIG.dimension, connection)
    spell_checker_service = SpellCheckerService(connection)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/search")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
