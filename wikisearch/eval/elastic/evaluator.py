import json
import math
from pathlib import Path

from wikisearch.eval.elastic.query_generator import QueryGenerator
from wikisearch.index.inverted_index import InvertedIndexService
from wikisearch.index.usearch_semantic_index import USearchIndexService


def search_elasticsearch(query, es_client, index_name, num_results=50):
    """
    Queries an Elasticsearch instance and returns a list of document IDs.
    """
    search_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "content"],
            }
        },
        "size": num_results
    }
    response = es_client.search(index=index_name, body=search_query)
    # Retrieve the _id field; note that _id is returned as a string.
    results = [hit["_id"] for hit in response["hits"]["hits"]]
    return results


def compute_metrics(engine_results, gold_results):
    """
    Compute precision, recall, and f1 given two lists of document IDs.
    Both engine_results and gold_results should be lists of comparable IDs.
    """
    set_engine = set(engine_results)
    set_gold = set(gold_results)

    # Calculate precision, recall, and f1 score.
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
                 lmdb_env,
                 path_to_semantic_index: Path,
                 num_batches: int,
                 queries_per_batch: int,
                 num_results_per_query: int,
                 es_client, index_name,
                 output_results_inverted: Path,
                 output_results_semantic: Path,
                 output_metrics_inverted: Path,
                 output_metrics_semantic: Path):
        """
        m: number of batches.
        n: number of queries per batch.
        r: number of top results to fetch.
        """
        self.num_batches = num_batches
        self.queries_per_batch = queries_per_batch
        self.num_results_per_query = num_results_per_query
        self.es_client = es_client
        self.es_index_name = index_name
        self.output_results_inverted = output_results_inverted
        self.output_results_semantic = output_results_semantic
        self.output_metrics_inverted = output_metrics_inverted
        self.output_metrics_semantic = output_metrics_semantic
        self.db_connection = db_connection
        self.cursor = self.db_connection.cursor()
        self.lmdb_env = lmdb_env
        self.inverted_index = InvertedIndexService(self.db_connection)
        self.semantic_index = USearchIndexService(
            path_to_semantic_index, 768, 10)
        self.qgen = QueryGenerator(self.db_connection, self.lmdb_env)

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
                # Get gold standard results (IDs) from Elasticsearch.
                gold = search_elasticsearch(
                    query, self.es_client, self.es_index_name, self.num_results_per_query)

                # Get results from your custom indexes.
                # Assume these functions return a list of tuples: (doc_id, distance).
                inv_raw = self.inverted_index.search(
                    query, self.num_results_per_query)
                sem_raw = self.semantic_index.search(
                    query, self.num_results_per_query, 0, "avg")

                # Extract the document IDs from the tuples.
                inv_results = [str(doc_id) for doc_id, _ in inv_raw]
                sem_results = [str(doc_id) for doc_id, _ in sem_raw]

                # If your ES _id's are strings, make sure both are comparable.
                # Alternatively, you can convert both to int if they are numeric:
                # inv_results = [int(doc_id) for doc_id, _ in inv_raw]
                # sem_results = [int(doc_id) for doc_id, _ in sem_raw]
                # gold = [int(doc_id) for doc_id in gold]

                # Compute metrics.
                p_inv, r_inv, f1_inv = compute_metrics(inv_results, gold)
                p_sem, r_sem, f1_sem = compute_metrics(sem_results, gold)

                batch_metrics_inverted.append({
                    "query": query,
                    "precision": p_inv,
                    "recall": r_inv,
                    "f1": f1_inv
                })
                batch_metrics_semantic.append({
                    "query": query,
                    "precision": p_sem,
                    "recall": r_sem,
                    "f1": f1_sem
                })

                results_inverted.append({
                    "batch": batch,
                    "query": query,
                    "engine_results": inv_results,
                    "gold_results": gold
                })
                results_semantic.append({
                    "batch": batch,
                    "query": query,
                    "engine_results": sem_results,
                    "gold_results": gold
                })

            # Compute overall averages per batch.
            def average_metric(metric, batch_metrics):
                return sum(item[metric] for item in batch_metrics) / len(batch_metrics) if batch_metrics else 0.0

            avg_inv = {
                "batch": batch,
                "precision": average_metric("precision", batch_metrics_inverted),
                "recall": average_metric("recall", batch_metrics_inverted),
                "f1": average_metric("f1", batch_metrics_inverted)
            }
            avg_sem = {
                "batch": batch,
                "precision": average_metric("precision", batch_metrics_semantic),
                "recall": average_metric("recall", batch_metrics_semantic),
                "f1": average_metric("f1", batch_metrics_semantic)
            }
            all_batch_metrics_inverted.append(avg_inv)
            all_batch_metrics_semantic.append(avg_sem)

        # Save results and metrics.
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

        # Compute overall stats (mean and confidence interval) for each metric.
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
