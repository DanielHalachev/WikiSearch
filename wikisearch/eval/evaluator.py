import json
import math
import os
import random
import time
from pathlib import Path

import requests
import tomli
from dotenv import load_dotenv

from wikisearch.db.database_connection import DatabaseConnectionService
from wikisearch.eval.query_generator import QueryGenerator
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.usearch_semantic_index import USearchIndexService


def get_wikipedia_search_results(query, num_result=50):
    """
    Use Wikipedia’s search API to get up to num_result for the query.
    Returns a list of article titles.
    """
    url = "https://bg.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 0,
        "utf8": "",
        "format": "json"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    results = [item["title"]
               for item in data.get("query", {}).get("search", [])]
    return results[:num_result]

# Simulated search engine functions.


def search_inverted_index(query, r=50):
    """
    Simulated inverted-index search. Replace with your actual search.
    For simulation, we take the gold standard and remove some items.
    """
    gold = get_wikipedia_search_results(query, r)
    # For simulation: return the first half (if available)
    simulated = gold[: len(gold)//2] if gold else []
    return simulated


def search_semantic(query, r=50):
    """
    Simulated semantic search. Replace with your actual semantic search.
    For simulation: return the gold standard with 20% of results randomly dropped.
    """
    gold = get_wikipedia_search_results(query, r)
    simulated = [item for item in gold if random.random() > 0.2]
    return simulated


def compute_metrics(engine_results, gold_results):
    """
    Compute precision, recall, and f1 given two lists of article titles.
    """
    set_engine = set(engine_results)
    set_gold = set(gold_results)
    if not set_engine:
        precision = 0.0
    else:
        precision = len(set_engine & set_gold) / len(set_engine)
    if not set_gold:
        recall = 0.0
    else:
        recall = len(set_engine & set_gold) / len(set_gold)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


class BatchEvaluator:
    def __init__(self, db_connection,
                 path_to_semantic_index: Path,
                 num_batches: int,
                 queries_per_batch: int,
                 num_results_per_query: int,
                 output_results_inverted: Path,
                 output_results_semantic: Path,
                 output_metrics_inverted: Path,
                 output_metrics_semantic: Path):
        """
        m: number of batches.
        n: number of queries per batch.
        r: number of top results to fetch from Wikipedia's search API.
        The file paths for saving query-level results and batch metrics are provided.
        """
        self.num_batches = num_batches
        self.queries_per_batch = queries_per_batch
        self.num_results_per_query = num_results_per_query
        self.output_results_inverted = output_results_inverted
        self.output_results_semantic = output_results_semantic
        self.output_metrics_inverted = output_metrics_inverted
        self.output_metrics_semantic = output_metrics_semantic
        self.db_connection = db_connection
        self.cursor = self.db_connection.cursor()
        self.inverted_index = InvertedIndexService(self.db_connection)
        self.semantic_index = USearchIndexService(
            path_to_semantic_index, 768, 10)
        self.qgen = QueryGenerator()

    def run_evaluation(self):
        all_batch_metrics_inverted = []
        all_batch_metrics_semantic = []
        results_inverted = []
        results_semantic = []

        for batch in range(1, self.num_batches + 1):
            print(f"Processing batch {batch}...")
            queries = self.qgen.get_queries(
                total_queries=self.queries_per_batch)
            batch_metrics_inverted = []
            batch_metrics_semantic = []

            for query in queries:
                gold = get_wikipedia_search_results(
                    query, self.num_results_per_query)

                inv_results = self.inverted_index.search(
                    query, self.num_results_per_query)
                sem_results = self.semantic_index.search(
                    query, self.num_results_per_query)

                p_inv, r_inv, f1_inv = compute_metrics(inv_results, gold)
                p_sem, r_sem, f1_sem = compute_metrics(sem_results, gold)

                batch_metrics_inverted.append({"query": query,
                                               "precision": p_inv,
                                               "recall": r_inv,
                                               "f1": f1_inv})
                batch_metrics_semantic.append({"query": query,
                                               "precision": p_sem,
                                               "recall": r_sem,
                                               "f1": f1_sem})
                results_inverted.append({"batch": batch,
                                         "query": query,
                                         "engine_results": inv_results,
                                         "gold_results": gold})
                results_semantic.append({"batch": batch,
                                         "query": query,
                                         "engine_results": sem_results,
                                         "gold_results": gold})
                # Be polite to the API.
                time.sleep(1)

            # Compute batch-level averages.
            def average_metric(metric, batch_metrics):
                return sum(item[metric] for item in batch_metrics) / len(batch_metrics) if batch_metrics else 0.0

            avg_inv = {"batch": batch,
                       "precision": average_metric("precision", batch_metrics_inverted),
                       "recall": average_metric("recall", batch_metrics_inverted),
                       "f1": average_metric("f1", batch_metrics_inverted)}
            avg_sem = {"batch": batch,
                       "precision": average_metric("precision", batch_metrics_semantic),
                       "recall": average_metric("recall", batch_metrics_semantic),
                       "f1": average_metric("f1", batch_metrics_semantic)}
            all_batch_metrics_inverted.append(avg_inv)
            all_batch_metrics_semantic.append(avg_sem)

        with open(self.output_results_inverted, "w", encoding="utf-8") as f:
            json.dump(results_inverted, f, ensure_ascii=False, indent=2)
        with open(self.output_results_semantic, "w", encoding="utf-8") as f:
            json.dump(results_semantic, f, ensure_ascii=False, indent=2)

        with open(self.output_metrics_inverted, "w", encoding="utf-8") as f:
            json.dump(all_batch_metrics_inverted, f,
                      ensure_ascii=False, indent=2)
        with open(self.output_metrics_semantic, "w", encoding="utf-8") as f:
            json.dump(all_batch_metrics_semantic, f,
                      ensure_ascii=False, indent=2)

        def overall_stats(metric, batch_metrics):
            values = [bm[metric] for bm in batch_metrics]
            mean = sum(values) / len(values)
            std = math.sqrt(sum((x - mean) ** 2 for x in values) /
                            (len(values) - 1)) if len(values) > 1 else 0.0
            se = std / math.sqrt(len(values))
            ci = 1.96 * se
            return mean, ci

        stats_inverted = {}
        stats_semantic = {}
        for mkey in ["precision", "recall", "f1"]:
            mean_inv, ci_inv = overall_stats(mkey, all_batch_metrics_inverted)
            stats_inverted[mkey] = {"mean": mean_inv, "ci": ci_inv}
            mean_sem, ci_sem = overall_stats(mkey, all_batch_metrics_semantic)
            stats_semantic[mkey] = {"mean": mean_sem, "ci": ci_sem}

        print("\n=== Overall Evaluation Metrics ===")
        print("Inverted-Index Search:")
        for k, v in stats_inverted.items():
            print(f"{k.capitalize()}: {v['mean']:.3f} ± {v['ci']:.3f}")
        print("\nSemantic Search:")
        for k, v in stats_semantic.items():
            print(f"{k.capitalize()}: {v['mean']:.3f} ± {v['ci']:.3f}")

        return stats_inverted, stats_semantic


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
    }
    with DatabaseConnectionService(DB_CONFIG) as connection:
        evaluator = BatchEvaluator(connection,
                                   Path(
                                       "/data/WikiSearchData/SemanticIndex/index.usearch"),
                                   int(EVAL_CONFIG["num_batches"]),
                                   int(EVAL_CONFIG["queries_per_batch"]),
                                   int(EVAL_CONFIG["num_results"]),
                                   Path(EVAL_CONFIG["inverted_results"]),
                                   Path(EVAL_CONFIG["semantic_results"]),
                                   Path(EVAL_CONFIG["inverted_metrics"]),
                                   Path(EVAL_CONFIG["semantic_metrics"]))
    evaluator.run_evaluation()
