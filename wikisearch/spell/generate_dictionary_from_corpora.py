import os
from pathlib import Path

import tomli
from dotenv import load_dotenv

from wikisearch.db.database_connection import DatabaseConnectionService


def export_to_hunspell():
    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)

    SPELL_CONFIG = {
        "custom_path": config["SpellChecker"].get("CustomDicPath"),
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
            SELECT w.token 
            FROM word w
            JOIN postings p ON w.id = p.word_id
            GROUP BY w.token
            ORDER BY COUNT(p.position) DESC
        """)
        words = [row[0] for row in cursor.fetchall()]
        with open(SPELL_CONFIG["custom_path"], "w", encoding="utf-8") as dic_file:
            dic_file.write(f"{len(words)}\n")
            dic_file.writelines(f"{word}\n" for word in words)

    # # Create minimal affix file
    # with open(AFF_PATH, "w", encoding="utf-8") as aff_file:
    #     aff_file.write("SET UTF-8\n")  # Basic settings for Bulgarian text


if __name__ == "__main__":
    export_to_hunspell()
