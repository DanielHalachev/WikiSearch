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

    def search(self, query: str, limit: int, offset: int = 0) -> List[Tuple[int, float]]:
        """Search for the closest documents to the query and return paginated results."""
        self.logger.info(f"Searching for query: {query}")
        try:
            query_embedding = self.embeddings_generator.str_to_embedding(query)
            # returns them in increasing score order (lower is closer)

            results: List = self.index.search(
                query_embedding, limit + offset).to_list()
            results.sort(key=lambda x: x[0])
            aggregated_results = [
                (doc_id, sum((1 - score) for _, score in group))
                for doc_id, group in groupby(results, key=itemgetter(0))
            ]
            aggregated_results.sort(key=lambda x: x[1], reverse=True)
            paginated_results = aggregated_results[offset:(offset + limit)]
            self.logger.info(
                f"Search results for query '{query}': {paginated_results}")
            return paginated_results

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []
