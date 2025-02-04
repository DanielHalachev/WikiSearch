import logging
import os
from pathlib import Path

import lmdb
import tomli
from dotenv import load_dotenv
from tqdm import tqdm

from wikisearch.db.database_connection import DatabaseConnectionService
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.usearch_semantic_index import SemanticIndexService

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('WikiSearch')
    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)

    load_dotenv()
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE"),
    }

    LMDB_CONFIG = {
        "path": config["FileDatabase"].get("Path", "./lmdb_store"),
        "size": int(config["FileDatabase"].get("Size", 10**9))
    }

    SEMANTIC_CONFIG = {
        "path": config["SemanticIndex"].get("Path", "/data/WikiSearchData/SemanticIndex"),
        "dimension": config["SemanticIndex"].get("Dimension", 768)
    }

    if not os.path.exists(LMDB_CONFIG["path"]):
        os.makedirs(LMDB_CONFIG["path"])
    lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=LMDB_CONFIG["size"])

    with DatabaseConnectionService(DB_CONFIG) as connection:
        semantic_index = SemanticIndexService(
            Path(SEMANTIC_CONFIG["path"]), int(SEMANTIC_CONFIG["dimension"]), connection)
        inverted_index = InvertedIndexService(connection)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM document")
        total_docs = cursor.fetchone()[0]

        cursor.execute("SELECT id, title FROM document LIMIT 1")
        for doc_id, title in tqdm(cursor.fetchall(), total=total_docs, desc="Indexing documents"):
            with lmdb_env.begin(write=True) as txn:
                body = txn.get(str(doc_id).encode())
            if body:
                body = body.decode('utf-8')
                body = "\n".join(
                    line for line in body.splitlines()
                    if line.strip() and not line.startswith("Категория:")
                )
                semantic_index.store_document(doc_id, body)
                inverted_index.update_index(doc_id, title, body)
