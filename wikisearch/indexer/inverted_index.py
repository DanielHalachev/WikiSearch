import math
import sqlite3
from pathlib import Path
from typing import List

class InvertedIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.num_documents = 0
        self.k1 = 1.5
        self.b = 0.75

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM document")
            self.num_documents = cursor.fetchone()[0]

    def update_inverted_index(self, document_tokens: List[str], title_tokens: List[str], document_title:str, document_url:str, document_summary:str):
        doc_id = self.num_documents
        self.num_documents += 1

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO document (id, url, summary) VALUES (?, ?, ?)",
                           (doc_id, document_url, document_summary, document_title))

            self.fill_posting(cursor, doc_id, document_tokens, 'posting')
            self.fill_posting(cursor, doc_id, title_tokens, 'title_posting')

    def fill_posting(self, cursor, doc_id, document_tokens, table_name:str):
        term_positions = {}
        for position, term in enumerate(document_tokens):
            if term not in term_positions:
                term_positions[term] = []
            term_positions[term].append(position)
        for term, positions in term_positions.items():
            cursor.execute("SELECT id FROM term WHERE token = ?", (term,))
            result = cursor.fetchone()

            if result:
                term_id = result[0]
            else:
                cursor.execute("INSERT INTO term (token) VALUES (?)", (term,))
                term_id = cursor.lastrowid

            if table_name == 'posting':
                for position in positions:
                    cursor.execute("INSERT INTO posting (term_id, document_id, position) VALUES (?, ?, ?)",
                                   (term_id, doc_id, position))
            if table_name == 'title_posting':
                for position in positions:
                    cursor.execute("INSERT INTO title_posting (term_id, document_id, position) VALUES (?, ?, ?)",
                                   (term_id, doc_id, position))

    def bm25_score(self, query_tokens: List[str], doc_id: int) -> float:
        avg_doc_length = self._get_avg_doc_length()
        doc_length = self._get_doc_length(doc_id)
        score = 0.0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for term in query_tokens:
                cursor.execute("SELECT id FROM term WHERE token = ?", (term,))
                result = cursor.fetchone()
                if not result:
                    continue

                term_id = result[0]

                # Get term frequency in the document
                cursor.execute("SELECT frequency FROM tf WHERE term_id = ? AND document_id = ?", (term_id, doc_id))
                tf_result = cursor.fetchone()
                tf = tf_result[0] if tf_result else 0

                # Get document frequency for the term
                cursor.execute("SELECT document_frequency FROM df WHERE term_id = ?", (term_id,))
                df_result = cursor.fetchone()
                df = df_result[0] if df_result else 0

                if tf > 0 and df > 0:
                    idf = math.log((self.num_documents - df + 0.5) / (df + 0.5))
                    score += idf * ((tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))))

        return score

    def search(self, query_tokens: List[str], num_results: int):
        candidate_docs = set()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for term in query_tokens:
                cursor.execute("SELECT DISTINCT document_id FROM posting WHERE term_id = (SELECT id FROM term WHERE token = ?)", (term,))
                candidate_docs.update(row[0] for row in cursor.fetchall())

        scores = [(doc_id, self.bm25_score(query_tokens, doc_id)) for doc_id in candidate_docs]
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:num_results]

    def _get_avg_doc_length(self) -> float:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(length) FROM (SELECT COUNT(*) AS length FROM posting GROUP BY document_id) as pl")
            return cursor.fetchone()[0] or 0

    def _get_doc_length(self, doc_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posting WHERE document_id = ?", (doc_id,))
            return cursor.fetchone()[0] or 0
