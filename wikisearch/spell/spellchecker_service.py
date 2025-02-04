from typing import List

import mysql.connector
from spell import SpellChecker
from spellchecker import SpellChecker


class SpellCheckerService:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        self.spell = SpellChecker(language=None)
        self._load_frequencies()

    def _load_frequencies(self):
        """Load word frequencies from MySQL database and add them to the spell checker."""
        cursor = self.db_connection.cursor()

        cursor.execute("""
            SELECT w.token, COUNT(p.position) AS frequency
            FROM postings p
            JOIN word w ON p.word_id = w.id
            GROUP BY w.id
        """)

        word_frequencies = cursor.fetchall()
        for word, frequency in word_frequencies:
            self.spell.word_frequency.add_word(word, frequency)

    def check_spelling(self, words: List[str]):
        """Check the spelling of words and return a list of misspelled words with suggestions."""
        misspelled = self.spell.unknown(words)
        return {word: list(self.spell.candidates(word)) for word in misspelled}
