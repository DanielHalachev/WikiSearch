import os
from pathlib import Path

import lmdb
import tomli
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from wikisearch.db.database_connection import DatabaseConnectionService
from wikisearch.eval.elastic.evaluator import BatchEvaluator


def add_to_es_index(db_connection, lmdb_env, es_client, index_name):
    cursor = db_connection.cursor()
    cursor.execute(
        """
    SELECT id, title FROM document
    WHERE id IN (SELECT * FROM usearch)
    """)
    for doc_id, title in cursor.fetchall():
        with lmdb_env.begin(write=True) as txn:
            text = txn.get(str(doc_id).encode()).decode()
            es_client.index(index=index_name, id=doc_id, document={
                            "title": title, "content": text})


if __name__ == "__main__":
    load_dotenv()
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE"),
    }

    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)
    EVAL_CONFIG = {
        "num_batches": config["Evaluator"].get("NumBatches", 5),
        "queries_per_batch": config["Evaluator"].get("QueriesPerBatch", 30),
        "results_per_query": config["Evaluator"].get("ResultsPerQuery", 20),
        "inverted_results": config["Evaluator"].get(
            "InvertedResults", "/data/WikiSearchData/Stats/inverted_results.json"),
        "semantic_results": config["Evaluator"].get(
            "SemanticResults", "/data/WikiSearchData/Stats/semantic_results.json"),
        "inverted_metrics": config["Evaluator"].get(
            "InvertedMetrics", "/data/WikiSearchData/Stats/inverted_results.json"),
        "semantic_metrics": config["Evaluator"].get(
            "SemanticMetrics", "/data/WikiSearchData/Stats/semantic_results.json"),
        "es_host": config["Evaluator"].get(
            "ElasticSearchHost", "http://localhost:9200"),
        "es_index": config["Evaluator"].get(
            "ElasticSearchIndex", "wiki"),
    }

    LMDB_CONFIG = {
        "path": config["FileDatabase"].get("Path"),
        "size": config["FileDatabase"].get("Size", 10**9)
    }

    es_client = Elasticsearch(EVAL_CONFIG["es_host"], basic_auth=("elastic", "22092001"));
    lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=int(LMDB_CONFIG["size"]))

    with DatabaseConnectionService(DB_CONFIG) as connection:
        # if not es_client.indices.exists(index=EVAL_CONFIG["es_index"]):
        # add_to_es_index(connection,
        #                 lmdb_env,
        #                 es_client,
        #                 EVAL_CONFIG["es_index"])

        evaluator = BatchEvaluator(connection,
                                   lmdb_env,
                                   Path(
                                       "/data/WikiSearchData/SemanticIndex/index.usearch"),
                                   int(EVAL_CONFIG["num_batches"]),
                                   int(EVAL_CONFIG["queries_per_batch"]),
                                   5,
                                   es_client,
                                   EVAL_CONFIG["es_index"],
                                   Path(EVAL_CONFIG["inverted_results"]),
                                   Path(EVAL_CONFIG["semantic_results"]),
                                   Path(EVAL_CONFIG["inverted_metrics"]),
                                   Path(EVAL_CONFIG["semantic_metrics"]))
    evaluator.run_evaluation()
