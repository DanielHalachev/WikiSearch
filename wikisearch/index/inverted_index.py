import logging
from decimal import Decimal
from typing import List, Tuple

from wikisearch.nlp.nlp import NLPService


class InvertedIndexService:

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.cursor = self.db_connection.cursor(buffered=True)
        self.num_documents: Decimal = Decimal('0')
        self.k1: Decimal = Decimal('0.5')
        self.b: Decimal = Decimal('0.75')
        self.nlp_service = NLPService(
            to_lower_case=True, preserve_ner_case=False)
        self.logger = logging.getLogger(__name__)
        self.get_number_of_documents()

    def get_number_of_documents(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM document")
            self.num_documents = self.cursor.fetchone()[0]
            self.logger.info(f"Number of documents: {self.num_documents}")
        except Exception as e:
            self.logger.error(f"Failed to get number of documents: {e}")
        return self.num_documents

    def store_document(self, doc_id: int, title: str, body: str):
        self.logger.info(f"Updating index for document ID: {doc_id}")
        self.num_documents += 1
        title_tokens, title_word_to_lemma = self.nlp_service.process(title)
        body_tokens, body_word_to_lemma = self.nlp_service.process(body)
        word_ids = {}
        lemma_ids = {}

        def insert_words_and_lemmas(word_to_lemma):
            for word, lemma in word_to_lemma.items():
                try:
                    self.cursor.execute(
                        "INSERT IGNORE INTO word (token) VALUES (%s)", (word,))
                    self.cursor.execute(
                        "SELECT id FROM word WHERE token = %s", (word,))
                    word_id = self.cursor.fetchone()[0]
                    word_ids[word] = word_id

                    self.cursor.execute(
                        "INSERT IGNORE INTO lemma (token) VALUES (%s)", (lemma,))
                    self.cursor.execute(
                        "SELECT id FROM lemma WHERE token = %s", (lemma,))
                    lemma_id = self.cursor.fetchone()[0]
                    lemma_ids[lemma] = lemma_id

                    self.cursor.execute(
                        "INSERT IGNORE INTO word_lemma (word_id, lemma_id) VALUES (%s, %s)",
                        (word_id, lemma_id)
                    )
                except Exception as e:
                    self.logger.error(f"Failed to insert word or lemma: {e}")

        insert_words_and_lemmas(title_word_to_lemma)
        insert_words_and_lemmas(body_word_to_lemma)

        def insert_tf_table(tokens, table_name):
            term_freq = {}
            for token in tokens:
                if token in lemma_ids:
                    term_freq[lemma_ids[token]] = term_freq.get(
                        lemma_ids[token], 0) + 1

            for lemma_id, freq in term_freq.items():
                try:
                    self.cursor.execute(
                        f"INSERT INTO {table_name} (term_id, document_id, frequency) VALUES (%s, %s, %s) "
                        f"ON DUPLICATE KEY UPDATE frequency = frequency + %s",
                        (lemma_id, doc_id, freq, freq)
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to insert into {table_name}: {e}")

        insert_tf_table(title_tokens, "title_tf")
        insert_tf_table(body_tokens, "body_tf")

        def insert_postings(tokens):
            for position, token in enumerate(tokens):
                word_id = word_ids.get(token)
                if word_id:
                    try:
                        self.cursor.execute(
                            "INSERT INTO postings (word_id, document_id, position) VALUES (%s, %s, %s)",
                            (word_id, doc_id, position)
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to insert into postings: {e}")

        # body_tokens_with_punct = self.nlp_service.tokenize_with_punct(body)
        body_tokens_with_punct = self.nlp_service.tokenize(body)
        insert_postings(body_tokens_with_punct)
        try:
            self.db_connection.commit()
            self.logger.info(f"Index updated for document ID: {doc_id}")
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {e}")

    def search(self, query: str, limit: int, offset: int = 0) -> List[Tuple[int, float]]:
        self.logger.info(f"Searching for query: {query}")
        query_tokens = self.nlp_service.tokenize(query)
        if not query_tokens:
            return []
        self.logger.debug(f"Tokens are: {query_tokens}")

        query_tokens_placeholders = ', '.join(['%s'] * len(query_tokens))
        try:
            self.cursor.execute(
                f"SELECT token, id FROM lemma WHERE token IN ({query_tokens_placeholders})", tuple(query_tokens))
            query_term_ids = {token: term_id for token,
                              term_id in self.cursor.fetchall()}
            self.logger.debug(f"Query Term ids: {query_term_ids}")

        except Exception as e:
            self.logger.error(f"Failed to fetch query term IDs: {e}")
            return []

        # Collect candidate documents by querying body_tf and title_tf at once
        placeholders = ', '.join(['%s'] * len(query_term_ids))
        try:
            self.cursor.execute(f"""
                SELECT document_id, term_id, frequency, 'body' AS source 
                FROM body_tf WHERE term_id IN ({placeholders})
                UNION ALL
                SELECT document_id, term_id, frequency, 'title' AS source 
                FROM title_tf WHERE term_id IN ({placeholders})
            """, tuple(query_term_ids.values()) * 2)
        except Exception as e:
            self.logger.error(f"Failed to fetch candidate documents: {e}")
            return []

        term_doc_map: dict[int, dict[str, dict[int, int]]] = {}
        for doc_id, term_id, freq, source in self.cursor.fetchall():
            if doc_id not in term_doc_map:
                term_doc_map[doc_id] = {'body': {}, 'title': {}}
            term_doc_map[doc_id][source][term_id] = freq

        self.logger.debug(f"Term-Doc Map: {term_doc_map}")

        # Calculate BM25 for each candidate document
        scores = []
        avg_body_length: Decimal = self._get_avg_doc_length("body_tf")
        avg_title_length: Decimal = self._get_avg_doc_length("title_tf")

        for doc_id, term_freqs in term_doc_map.items():
            body_length: Decimal = self._get_doc_length(doc_id, "body_tf")
            title_length: Decimal = self._get_doc_length(doc_id, "title_tf")

            score: Decimal = Decimal('0.0')
            for term, term_id in query_term_ids.items():
                body_tf: Decimal = Decimal(term_freqs['body'].get(term_id, 0))
                title_tf: Decimal = Decimal(
                    term_freqs['title'].get(term_id, 0))

                body_df: Decimal = self._get_document_frequency(
                    "body_tf", term_id)
                title_df: Decimal = self._get_document_frequency(
                    "title_tf", term_id)

                # Body score
                if body_tf > 0 and body_df > 0:
                    idf_body = Decimal.ln(
                        (self.num_documents - body_df + Decimal('0.5')) / (body_df + Decimal('0.5')))
                    score += idf_body * ((body_tf * (self.k1 + Decimal('1'))) / (body_tf + self.k1 *
                                                                                 (Decimal('1') - self.b + self.b * (body_length / avg_body_length))))

                # Title score
                if title_tf > 0 and title_df > 0:
                    idf_title = Decimal.ln(
                        (self.num_documents - title_df + Decimal('0.5')) / (title_df + Decimal('0.5')))
                    score += idf_title * ((title_tf * (self.k1 + Decimal('1'))) / (title_tf + self.k1 *
                                                                                   (Decimal('1') - self.b + self.b * (title_length / avg_title_length))))

            scores.append((doc_id, float(score)))

        scores.sort(key=lambda x: x[1], reverse=True)
        paginated_scores = scores[offset:(offset + limit)]
        self.logger.info(
            f"Search results for query '{query}': {paginated_scores}")
        return paginated_scores

    def _get_avg_doc_length(self, table_name: str) -> Decimal:
        try:
            self.cursor.execute(
                f"SELECT AVG(doc_length) FROM (SELECT SUM(frequency) AS doc_length FROM {table_name} GROUP BY document_id) AS doc_lengths")
            avg_length = self.cursor.fetchone()[0] or 0
            self.logger.debug(
                f"Average document length for {table_name}: {avg_length}")
        except Exception as e:
            self.logger.error(
                f"Failed to get average document length for {table_name}: {e}")
            avg_length = 0
        return Decimal(avg_length)

    def _get_doc_length(self, doc_id: int, table_name: str) -> Decimal:
        try:
            self.cursor.execute(
                f"SELECT SUM(frequency) FROM {table_name} WHERE document_id = %s", (doc_id,))
            doc_length = self.cursor.fetchone()[0] or 0
            self.logger.debug(
                f"Document length for document ID {doc_id} in {table_name}: {doc_length}")
        except Exception as e:
            self.logger.error(
                f"Failed to get document length for document ID {doc_id} in {table_name}: {e}")
            doc_length = 0
        return Decimal(doc_length)

    def _get_document_frequency(self, table_name: str, term_id: int) -> Decimal:
        try:
            self.cursor.execute(
                f"SELECT COUNT(DISTINCT document_id) FROM {table_name} WHERE term_id = %s", (term_id,))
            df_result = self.cursor.fetchone()
            df = df_result[0] if df_result else 0
        except Exception as e:
            self.logger.error(
                f"Failed to get document frequency for term ID {term_id} in {table_name}: {e}")
            df = 0
        return Decimal(df)
