from abc import ABC, abstractmethod
from pathlib import Path

import numpy

class EmbeddingsGenerator(ABC):
    @abstractmethod
    def to_embedding(self, string: str) -> numpy.array:
        """
        Generate an embedding from an input string
        :param string: A string to generate an embedding for
        :return: An embedding
        """
        pass


class Index(ABC):
    @abstractmethod
    def load_index(self, path_to_index: Path):
        """
        Load a stored index.
        :param path_to_index: Path to stored index.
        :return:
        """
        pass

    @abstractmethod
    def store_embedding(self, embedding: numpy.array):
        """
        Stores an embedding in the index
        :param embedding: A document embedding
        :return:
        """
        pass

    @abstractmethod
    def search(self, query: numpy.array, num_pages: int | None, num_results: int | None) -> [[int]]:
        """
        Return num_results search results, organized in num_pages pages, ordered by decreasing similarity
        :param query:
        :param num_pages:
        :param num_results:
        :return: An array of document ID arrays, ordered by decreasing similarity with query
        """
