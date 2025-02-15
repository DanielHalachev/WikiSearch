import os
from pathlib import Path

import dawg
import tomli
from dotenv import load_dotenv

from wikisearch.db.database_connection import DatabaseConnectionService

path_to_config = Path("./config.toml")
with open(path_to_config, "rb") as f:
    config = tomli.load(f)

AUTOCOMPLETION_CONFIG = {
    "word-completion-dawg": config["Autocompletion"].get("WordCompletionDAWG"),
    "next-word-dawg": config["Autocompletion"].get("NextWordDAWG"),
}

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_DATABASE"),
}

with DatabaseConnectionService(DB_CONFIG) as connection:
    cursor = connection.cursor()
    cursor.execute("""
        SELECT CONCAT(LOWER(w1.token), ' ', LOWER(w2.token)) AS bigram, COUNT(*) AS frequency
        FROM postings p1
        JOIN postings p2 ON p1.document_id = p2.document_id AND p1.position = p2.position - 1
        JOIN word w1 ON p1.word_id = w1.id
        JOIN word w2 ON p2.word_id = w2.id
        WHERE w1.token NOT IN (' ', '\n') AND w2.token NOT IN (' ', '\n')
        GROUP BY bigram
        ORDER BY frequency DESC
    """)

    bigrams = cursor.fetchall()
    if bigrams:
        bigram_dict = {bigram: frequency for bigram, frequency in bigrams}

        # next_word_dawg = dawg.IntCompletionDAWG(bigram_dict.items())
        next_word_dawg = dawg.CompletionDAWG([key for key,_ in bigram_dict.items()])
        next_word_dawg.save(AUTOCOMPLETION_CONFIG["next-word-dawg"])
