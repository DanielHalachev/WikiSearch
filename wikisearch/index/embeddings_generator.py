from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingsGenerator:
    def __init__(self, dimension: int, max_segment_length: int = 512):
        self.model = SentenceTransformer(
            "Alibaba-NLP/gte-multilingual-base", trust_remote_code=True)
        self.dimension = dimension
        self.max_segment_length = max_segment_length

    def split_text(self, text: str) -> List[str]:
        sentences = text.split(". ")
        segments = []
        current_segment = []

        for sentence in sentences:
            current_segment.append(sentence)
            segment_text = ". ".join(current_segment)

            if len(segment_text) > self.max_segment_length:
                segments.append(". ".join(current_segment[:-1]))
                current_segment = [sentence]

        if current_segment:
            segments.append(". ".join(current_segment))
        return segments

    def str_to_embedding(self, string: str) -> np.ndarray:
        embeddings = self.model.encode([string], normalize_embeddings=True)
        return embeddings

    def list_to_embeddings(self, strings: List[str]) -> np.ndarray:
        embeddings = self.model.encode(strings, normalize_embeddings=True)
        return np.array(embeddings)
