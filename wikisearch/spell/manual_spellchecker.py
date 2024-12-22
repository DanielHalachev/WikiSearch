import sqlite3

class SpellChecker:
    def __init__(self, db_path: str, threshold: float = 0.5):
        """
        Initializes the SpellChecker with the SQLite database connection.

        :param db_path: Path to the SQLite database.
        :param threshold: Jaccard coefficient threshold for considering a match.
        """
        self.db_path = db_path
        self.threshold = threshold

    def get_bigrams(self, word: str) -> set:
        """
        Get the set of bigrams for a given word.

        :param word: The word to generate bigrams for.
        :return: A set of bigrams.
        """
        bigrams = set()
        for i in range(len(word) - 1):
            bigrams.add(word[i:i+2])
        return bigrams

    def get_postings(self, bigram: str) -> set:
        """
        Get the term_ids of words that contain the given bigram.

        :param bigram: The bigram to search for.
        :return: A set of term_ids from the database.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT term_id FROM char_bigrams WHERE bigram = ?", (bigram,))
        postings = set([row[0] for row in cursor.fetchall()])
        conn.close()
        return postings

    def jaccard_similarity(self, word1: str, word2: str) -> float:
        """
        Calculate the Jaccard coefficient between two words.

        :param word1: The first word.
        :param word2: The second word.
        :return: Jaccard coefficient between the two words.
        """
        bigrams1 = self.get_bigrams(word1)
        bigrams2 = self.get_bigrams(word2)
        intersection = len(bigrams1.intersection(bigrams2))
        union = len(bigrams1.union(bigrams2))
        return intersection / union if union != 0 else 0

    def check_and_correct(self, tokens: list[str]) -> tuple[list[str], list[int]]:
        """
        Check and correct misspelled words based on bigram overlap.

        :param tokens: List of query tokens to spell-check.
        :return: A tuple containing:
                 1. List of tokens with corrections applied.
                 2. List of indices in the input tokens where corrections were made.
        """
        corrected_tokens = tokens[:]
        changes = []

        for i, token in enumerate(tokens):
            bigrams = self.get_bigrams(token)

            candidate_terms = {}
            for bigram in bigrams:
                postings = self.get_postings(bigram)
                for term_id in postings:
                    if term_id not in candidate_terms:
                        candidate_terms[term_id] = []

                    candidate_terms[term_id].append(bigram)

            best_match = None
            max_similarity = 0
            for term_id, candidate_bigrams in candidate_terms.items():
                # Get the word from the term_id (you might need to adjust this query based on your schema)
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT token FROM term WHERE id = ?", (term_id,))
                candidate_word = cursor.fetchone()[0]
                conn.close()

                similarity = self.jaccard_similarity(token, candidate_word)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = candidate_word

            # If the best match is above the threshold, apply the correction
            if max_similarity >= self.threshold:
                corrected_tokens[i] = best_match
                changes.append(i)

        return corrected_tokens, changes
