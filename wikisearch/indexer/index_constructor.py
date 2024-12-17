import numpy
from sentence_transformers import SentenceTransformer, AutoTokenizer
import torch.nn.functional as F

from wikisearch.indexer.interfaces import EmbeddingsGenerator


class DefaultEmbeddingsGenerator(EmbeddingsGenerator):
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("Alibaba-NLP/gte-multilingual-base")
        self.model = SentenceTransformer("Alibaba-NLP/gte-multilingual-base")
        self.dimension = 768


    def to_embedding(self, string: str) -> numpy.array:
        batch_dict = self.tokenizer([string], max_length=8192, padding=True, truncation=True, return_tensors='pt')
        outputs = self.model(**batch_dict)
        embeddings = outputs.last_hidden_state[:, 0][:self.dimension]
        embeddings = F.normalize(embeddings, p=2, dim=1)
        # scores = (embeddings[:1] @ embeddings[1:].T) * 100

        return embeddings[0]