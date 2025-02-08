import atexit
import logging
from itertools import groupby
from operator import itemgetter
from pathlib import Path
from typing import List, Tuple

import numpy as np
from usearch.index import Index

from wikisearch.index.embeddings_generator import EmbeddingsGenerator


class USearchIndexService:
    def __init__(self, path_to_index: Path, dimension: int, save_threshold: int = 10):
        self.logger = logging.getLogger(__name__)
        self.path_to_index = path_to_index
        self.dimension = dimension
        self.embeddings_generator = EmbeddingsGenerator(self.dimension)
        self.save_threshold = save_threshold
        self.document_save_count = 0

        self.index = self.load_or_create_index()
        atexit.register(self.save_index)

    def load_or_create_index(self) -> Index:
        """Load an existing Index or create a new one."""
        self.index = Index(ndim=self.dimension, metric="cos", multi=True)
        if self.path_to_index.is_file():
            self.logger.info(
                f"Loading UIndex from {self.path_to_index}")
            self.index.load(str(self.path_to_index))
        else:
            self.logger.info(
                f"Creating new UIndex with dimension {self.dimension}")
            self.save_index()
        return self.index

    def save_index(self):
        """Persist the index to disk."""
        if self.index is not None:
            self.logger.info(f"Saving index to {self.path_to_index}")
            try:
                self.index.save(str(self.path_to_index))
            except Exception as e:
                self.logger.error(f"Failed to save index: {e}")

    def store_document(self, doc_id: int, text: str):
        """Stores a document by splitting it into segments, embedding them, and indexing them."""
        self.logger.info(f"Storing document with ID {doc_id}")
        segments = self.embeddings_generator.split_text(text)

        try:
            embeddings = self.embeddings_generator.list_to_embeddings(
                segments)  # Shape: (num_segments, dimension)

            if not isinstance(embeddings, np.ndarray) or embeddings.shape[1] != self.dimension:
                raise ValueError(
                    "Embeddings must be a NumPy array of shape (num_segments, dimension)")

            for embedding in embeddings:
                self.index.add(doc_id, embedding)
            # this shit is broken:
            # keys = np.repeat(doc_id, embeddings.size)
            # self.index.add(keys, embeddings)

            self.document_save_count += 1
            if self.document_save_count % self.save_threshold == 0:
                self.logger.info(
                    f"Document save count reached {self.document_save_count}. Saving index.")
                self.save_index()

        except Exception as e:
            self.logger.error(f"Error storing document {doc_id}: {e}")

    def search(self, query: str, limit: int, offset: int = 0, strategy: str = "sum") -> List[Tuple[int, float]]:
        """Search for the closest documents to the query using the chosen aggregation strategy.

        :param query: The query string.
        :param limit: The number of results to return.
        :param offset: The offset into the results.
        :param strategy: The aggregation strategy ("sum", "min", or "avg").
        :return: A list of tuples (document_id, aggregated_score)
        """
        if strategy == "sum":
            return self.search_max_sim_sum(query, limit, offset)
        elif strategy == "min":
            return self.search_min_distance(query, limit, offset)
        elif strategy == "avg":
            return self.search_avg_distance(query, limit, offset)
        else:
            self.logger.warning(
                f"Unknown strategy '{strategy}', defaulting to sum aggregation.")
            return self.search_max_sim_sum(query, limit, offset)

    def search_max_sim_sum(self, query: str, limit: int, offset: int = 0) -> List[Tuple[int, float]]:
        """Search using sum aggregation: Sum (1 - score) for each document."""
        self.logger.info(f"Searching for query: {query} using sum aggregation")
        try:
            query_embedding = self.embeddings_generator.str_to_embedding(query)
            raw_results: List[Tuple[int, float]] = self.index.search(
                query_embedding, limit + offset).to_list()
            raw_results.sort(key=itemgetter(0))

            aggregated_results = []
            for doc_id, group in groupby(raw_results, key=itemgetter(0)):
                scores = [score for _, score in group]
                # Sum (1 - score) for each embedding.
                aggregated_score = sum(1 - s for s in scores)
                aggregated_results.append((doc_id, aggregated_score))

            aggregated_results.sort(key=lambda x: x[1], reverse=True)
            paginated_results = aggregated_results[offset:(offset + limit)]
            self.logger.info(
                f"Sum aggregation results for query '{query}': {paginated_results}")
            return paginated_results
        except Exception as e:
            self.logger.error(f"Error during sum aggregation search: {e}")
            return []

    def search_min_distance(self, query: str, limit: int, offset: int = 0) -> List[Tuple[int, float]]:
        """Search using max pooling: Use the most relevant embedding per document.

        Since lower score is better, we take the minimum score and then use (1 - best_score).
        """
        self.logger.info(f"Searching for query: {query} using max pooling")
        try:
            query_embedding = self.embeddings_generator.str_to_embedding(query)
            raw_results: List[Tuple[int, float]] = self.index.search(
                query_embedding, limit + offset).to_list()
            raw_results.sort(key=itemgetter(0))

            aggregated_results = []
            for doc_id, group in groupby(raw_results, key=itemgetter(0)):
                scores = [score for _, score in group]
                if scores:
                    best_score = min(scores)
                else:
                    best_score = 1.0
                aggregated_results.append((doc_id, best_score))

            aggregated_results.sort(key=lambda x: x[1])
            paginated_results = aggregated_results[offset:(offset + limit)]
            self.logger.info(
                f"Max pooling results for query '{query}': {paginated_results}")
            return paginated_results
        except Exception as e:
            self.logger.error(f"Error during max pooling search: {e}")
            return []

    def search_avg_distance(self, query: str, limit: int, offset: int = 0) -> List[Tuple[int, float]]:
        """Search using average pooling: Average (1 - score) for each document."""
        self.logger.info(f"Searching for query: {query} using average pooling")
        try:
            query_embedding = self.embeddings_generator.str_to_embedding(query)
            raw_results: List[Tuple[int, float]] = self.index.search(
                query_embedding, limit + offset).to_list()
            raw_results.sort(key=itemgetter(0))

            aggregated_results = []
            for doc_id, group in groupby(raw_results, key=itemgetter(0)):
                scores = [score for _, score in group]
                if scores:
                    aggregated_score = sum(1 - s for s in scores) / len(scores)
                else:
                    aggregated_score = 0.0
                aggregated_results.append((doc_id, aggregated_score))

            aggregated_results.sort(key=lambda x: x[1], reverse=True)
            paginated_results = aggregated_results[offset:(offset + limit)]
            self.logger.info(
                f"Average pooling results for query '{query}': {paginated_results}")
            return paginated_results
        except Exception as e:
            self.logger.error(f"Error during average pooling search: {e}")
            return []
