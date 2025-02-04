from abc import ABC, abstractmethod
from pathlib import Path

import numpy

class EmbeddingsGenerator(ABC):
    @abstractmethod
    def str_to_embedding(self, string: str) -> numpy.array:
        """
        Generate an embedding from an input string
        :param string: A string to generate an embedding for
        :return: An embedding
        """
        pass

    @abstractmethod
    def collection_to_embeddings(self, documents: [str]) -> [numpy.array]:
        """
        Generate embeddings for a collection of documents
        :param documents: A collection of strings
        :return: An array of embeddings
        """
        pass


