import logging
import os
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

import lmdb
import tomli
from dotenv import load_dotenv
from tqdm import tqdm

from wikisearch.db.database_connection import DatabaseConnectionService
from wikisearch.index.faiss_semantic_index import FAISSIndexService
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.usearch_semantic_index import USearchIndexService


def store_document_in_usearch(usearch_index, doc_id, body):
    usearch_index.store_document(doc_id, body)


def store_document_in_faiss(faiss_index, doc_id, body):
    faiss_index.store_document(doc_id, body)


def store_document_in_inverted(inverted_index, doc_id, title, body):
    inverted_index.store_document(doc_id, title, body)


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

    USEARCH_CONFIG = {
        "path": config["USearchIndex"].get("Path", "/data/WikiSearchData/SemanticIndex/index.usearch"),
        "dimension": config["USearchIndex"].get("Dimension", 768)
    }

    FAISS_CONFIG = {
        "path": config["FAISSIndex"].get("Path", "/data/WikiSearchData/SemanticIndex/index.faiss"),
        "dimension": config["FAISSIndex"].get("Dimension", 768)
    }

    if not os.path.exists(LMDB_CONFIG["path"]):
        os.makedirs(LMDB_CONFIG["path"])
    lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=LMDB_CONFIG["size"])

    with DatabaseConnectionService(DB_CONFIG) as connection:
        usearch_semantic_index = USearchIndexService(
            Path(USEARCH_CONFIG["path"]), int(USEARCH_CONFIG["dimension"]))
        faiss_semantic_index = FAISSIndexService(
            Path(FAISS_CONFIG["path"]), int(FAISS_CONFIG["dimension"]), connection)
        inverted_index = InvertedIndexService(connection)
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM document")
        # total_docs = cursor.fetchone()[0]
        total_docs = 500

        cursor.execute("SELECT id, title FROM document ORDER BY RAND() LIMIT 500")
        # with ThreadPoolExecutor() as executor:
        for doc_id, title in tqdm(cursor.fetchall(), total=total_docs, desc="Indexing documents"):
            with lmdb_env.begin(write=True) as txn:
                body = txn.get(str(doc_id).encode())
            if body:
                body = body.decode('utf-8')
                body = "\n".join(
                    line for line in body.splitlines()
                    if line.strip() and not line.startswith("Категория:")
                )
                # futures = [
                #     executor.submit(store_document_in_usearch,
                #                     usearch_semantic_index, doc_id, body),
                #     executor.submit(store_document_in_faiss,
                #                     faiss_semantic_index, doc_id, body),
                #     executor.submit(store_document_in_inverted,
                #                     inverted_index, doc_id, title, body)
                # ]
                store_document_in_usearch(usearch_semantic_index, doc_id, body)
                # wait(futures)
