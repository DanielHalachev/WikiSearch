import atexit
import logging
from pathlib import Path

import faiss

from wikisearch.index.embeddings_generator import EmbeddingsGenerator


class FAISSIndexService:
    def __init__(self, path_to_index: Path, dimension: int, db_connection, save_threshold: int = 10, hnsw_M: int = 32):
        self.logger = logging.getLogger(__name__)
        self.path_to_index = path_to_index
        self.dimension: int = dimension
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        self.embeddings_generator = EmbeddingsGenerator(self.dimension)
        self.save_threshold = save_threshold
        self.document_save_count = 0
        self.hnsw_M = hnsw_M  # Parameter for HNSW controlling the number of neighbors

        self.index = self.load_or_create_index()
        atexit.register(self.save_index)

    def load_or_create_index(self) -> faiss.IndexHNSWFlat:
        if self.path_to_index.is_file():
            self.logger.info(f"Loading HNSW index from {self.path_to_index}")
            self.index = faiss.read_index(str(self.path_to_index))
        else:
            self.logger.info(
                f"Creating new HNSW index with dimension {self.dimension} and M={self.hnsw_M}")
            self.index = faiss.IndexHNSWFlat(self.dimension, self.hnsw_M)
            # Optionally, you can set the number of efSearch for higher recall:
            self.index.hnsw.efSearch = 50
            self.save_index()
        return self.index

    def save_index(self):
        if self.index is not None:
            self.logger.info(f"Saving index to {self.path_to_index}")
            try:
                faiss.write_index(self.index, str(self.path_to_index))
            except Exception as e:
                self.logger.error(f"Failed to save index: {e}")

    def store_document(self, doc_id: int, text: str):
        self.logger.info(f"Storing document with ID {doc_id}")
        segments = self.embeddings_generator.split_text(text)

        try:
            embeddings = self.embeddings_generator.list_to_embeddings(segments)
            start_index = self.index.ntotal
            self.index.add(embeddings)  # type: ignore
            faiss_ids = list(range(start_index, self.index.ntotal))

            # self.cursor.executemany(
            #     "INSERT INTO faiss_to_document_id (faiss_id, document_id) VALUES (%s, %s)",
            #     [(faiss_id, doc_id) for faiss_id in faiss_ids]
            # )
            for faiss_id in faiss_ids:
                self.cursor.execute(
                    "INSERT INTO faiss_to_document_id (faiss_id, document_id) VALUES (%s, %s)",
                    (faiss_id, doc_id)
                )
            self.conn.commit()

            self.document_save_count += 1
            if self.document_save_count % self.save_threshold == 0:
                self.logger.info(
                    f"Document save count reached {self.document_save_count}. Saving index.")
                self.save_index()

        except Exception as e:
            self.logger.error(f"Error storing document {doc_id}: {e}")
            self.conn.rollback()
        self.logger.info(f"Storing document with ID {doc_id}")
        segments = self.embeddings_generator.split_text(text)

        try:
            embeddings = self.embeddings_generator.list_to_embeddings(segments)
            start_index = self.index.ntotal
            self.index.add(embeddings)  # type: ignore
            faiss_ids = list(range(start_index, self.index.ntotal))

            self.cursor.executemany(
                "INSERT INTO faiss_to_document_id (faiss_id, document_id) VALUES (:faiss_id, :document_id)",
                [{'faiss_id': faiss_id, 'document_id': doc_id}
                    for faiss_id in faiss_ids]
            )
            self.conn.commit()

            self.document_save_count += 1
            if self.document_save_count % self.save_threshold == 0:
                self.logger.info(
                    f"Document save count reached {self.document_save_count}. Saving index.")
                self.save_index()

        except Exception as e:
            self.logger.error(f"Error storing document {doc_id}: {e}")
            self.conn.rollback()
