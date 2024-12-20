from collections import defaultdict, Counter
import math
import pickle
from pathlib import Path
from typing import List

from wikisearch.nlp.nlp import NLProcessor

class InvertedIndex:
    def __init__(self, path_to_index: Path):
        self.path_to_index = path_to_index
        self.inverted_index = defaultdict(lambda: defaultdict(list))  # term -> {doc_id: [positions]}
        self.tf_index = defaultdict(lambda: defaultdict(int))  # term -> {doc_id: term_frequency}
        self.cf_index = defaultdict(int)  # term -> collection frequency
        self.df_index = defaultdict(int)  # term -> document frequency
        self.doc_lengths = defaultdict(int)  # doc_id -> document length
        self.num_documents = 0
        self.k1 = 1.5
        self.b = 0.75
        self.load_or_create_index(path_to_index)

    def load_or_create_index(self, path_to_index: Path):
        if path_to_index.is_file():
            self.read_index(path_to_index)
        else:
            self.save_index(path_to_index)

    def save_index(self, path_to_index: Path):
        with open(path_to_index, 'wb') as file:
            pickle.dump({
                'inverted_index': dict(self.inverted_index),
                'tf_index': dict(self.tf_index),
                'cf_index': dict(self.cf_index),
                'df_index': dict(self.df_index),
                'doc_lengths': dict(self.doc_lengths),
                'num_documents': self.num_documents
            }, file)

    def read_index(self, path_to_index: Path):
        with open(path_to_index, 'rb') as file:
            index_data = pickle.load(file)
            self.inverted_index = defaultdict(lambda: defaultdict(list), index_data['inverted_index'])
            self.tf_index = defaultdict(lambda: defaultdict(int), index_data['tf_index'])
            self.cf_index = defaultdict(int, index_data['cf_index'])
            self.df_index = defaultdict(int, index_data['df_index'])
            self.doc_lengths = defaultdict(int, index_data['doc_lengths'])
            self.num_documents = index_data['num_documents']

    def update_inverted_index(self, document_tokens: List[List[str]]):
        start_doc_id = self.num_documents
        self.num_documents += len(document_tokens)

        for doc_id, tokens in enumerate(document_tokens, start=start_doc_id):
            self.doc_lengths[doc_id] = len(tokens)

            tf_counter = Counter(tokens)
            for term, count in tf_counter.items():
                self.tf_index[term][doc_id] = count
                self.cf_index[term] += count
                if doc_id not in self.inverted_index[term]:
                    self.df_index[term] += 1

            for position, term in enumerate(tokens):
                self.inverted_index[term][doc_id].append(position)

    def get_tf_idf(self, term: str, doc_id: int):
        if term not in self.df_index or doc_id not in self.tf_index[term]:
            return 0.0
        tf = self.tf_index[term][doc_id]
        idf = math.log10(self.num_documents / self.df_index[term])
        return (1 + math.log10(tf)) * idf

    def bm25_score(self, query_tokens: List[str], doc_id: int) -> float:
        avg_doc_length = sum(self.doc_lengths.values()) / self.num_documents
        doc_length = self.doc_lengths[doc_id]
        score = 0.0

        for term in query_tokens:
            if term in self.tf_index and doc_id in self.tf_index[term]:
                tf = self.tf_index[term][doc_id]
                df = self.df_index[term]
                idf = math.log((self.num_documents - df + 0.5) / (df + 0.5))
                score += idf * ((tf * (self.k1 + 1)) / (
                            tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))))

        return score

    def search(self, query_tokens: List[str], num_results: int):
        candidate_docs = set(
            doc_id for term in query_tokens if term in self.inverted_index for doc_id in self.inverted_index[term])

        scores = [(doc_id, self.bm25_score(query_tokens, doc_id)) for doc_id in candidate_docs]
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:num_results]
