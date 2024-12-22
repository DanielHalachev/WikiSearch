import faiss
import numpy as np
from pathlib import Path

from wikisearch.indexer.embeddings_generator import DefaultEmbeddingsGenerator


class SemanticIndex:
    def __init__(self, path_to_index: Path, dimension: int):
        self.path_to_index = path_to_index
        self.dimension = dimension
        self.index = None
        self.load_or_create_index(path_to_index)

    def load_or_create_index(self, path_to_index: Path):
        """
        Load a FAISS index from the given path. If the index does not exist, create an empty one.
        :param path_to_index: Path to the index file.
        """
        self.path_to_index = path_to_index
        if path_to_index.is_file():
            self.index = faiss.read_index(str(path_to_index))
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.save_index(path_to_index)

    def save_index(self, path_to_index: Path):
        """
        Save the FAISS index to the given path.
        :param path_to_index: Path to save the index file.
        """
        faiss.write_index(self.index, str(path_to_index))

    def store_embedding(self, embedding: np.ndarray):
        """
        Store a new embedding into the FAISS index.
        :param embedding: The embedding to be stored.
        """
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embedding)
        if self.path_to_index:
            self.save_index(self.path_to_index)

    def search(self, query: np.ndarray, num_results: int = None) -> (np.array, np.array):
        """
        Search the FAISS index for the nearest embeddings.
        :param query: The query embedding.
        :param num_results: The number of results to return.
        :return: List of lists containing the indices of the nearest embeddings.
        """
        if self.index is None or num_results is None:
            raise ValueError("The index is not loaded or the number of results is not specified.")

        return self.index.search(query, num_results)

if __name__ == '__main__':
    path_to_index = Path("../../data/semantic_index.faiss")
    semantic_index = SemanticIndex(path_to_index, 768)

    s1 = "MySQL is a relational database."
    s2 = "MariaDB is another relational database"
    s3 = "MongoDB is a document database"
    s4 = "I like pizza"

    generator = DefaultEmbeddingsGenerator(768)
    e1 = generator.str_to_embedding(s1)
    semantic_index.store_embedding(e1)

    e2 = generator.str_to_embedding(s2)
    semantic_index.store_embedding(e2)

    e3 = generator.str_to_embedding(s3)
    semantic_index.store_embedding(e3)

    e4 = generator.str_to_embedding(s4)
    semantic_index.store_embedding(e4)

    results = semantic_index.search(e1, num_results=10)

    print("Search results:", results)
