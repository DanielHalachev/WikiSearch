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
    cursor.execute("SELECT DISTINCT LOWER(token) FROM word WHERE token NOT IN (' ', '\n')")
    words = [row[0] for row in cursor.fetchall()]

    if words:
        completion_dawg = dawg.CompletionDAWG(words)
        completion_dawg.save(AUTOCOMPLETION_CONFIG["word-completion-dawg"])
