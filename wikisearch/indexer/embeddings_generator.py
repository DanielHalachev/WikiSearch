import numpy
from sentence_transformers import SentenceTransformer
# import torch.nn.functional as F

from wikisearch.indexer.interfaces import EmbeddingsGenerator


class DefaultEmbeddingsGenerator(EmbeddingsGenerator):

    def __init__(self, dimension: int):
        """
        Initialize the embeddings generator by specifying the vector dimension
        :param dimension: Desired embedding dimension
        """
        # self.tokenizer = AutoTokenizer.from_pretrained("Alibaba-NLP/gte-multilingual-base")
        self.model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
        self.dimension = dimension

    def str_to_embedding(self, string: str) -> numpy.array:
        # batch_dict = self.tokenizer([string], max_length=8192, padding=True, truncation=True, return_tensors='pt')
        # outputs = self.model(**batch_dict)
        # embeddings = outputs.last_hidden_state[:, 0][:self.dimension]
        # embeddings = F.normalize(embeddings, p=2, dim=1)
        # scores = (embeddings[:1] @ embeddings[1:].T) * 100
        embeddings = self.model.encode([string], normalize_embeddings=True)

        return embeddings

    def collection_to_embeddings(self, documents: [str]) -> numpy.array:
        # batch_dict = self.tokenizer(documents, max_length=8192, padding=True, truncation=True, return_tensors='pt')
        # outputs = self.model(**batch_dict)
        # embeddings = outputs.last_hidden_state[:, 0][:self.dimension]
        # embeddings = F.normalize(embeddings, p=2, dim=1)

        embeddings = self.model.encode(documents, normalize_embeddings=True)
        return embeddings
