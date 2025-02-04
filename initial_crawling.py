import logging
import os
from pathlib import Path

import lmdb
import tomli

from wikisearch.crawler.wiki_processor import WikipediaProcessor
from wikisearch.db.DatabaseConnection import DatabaseConnectionService

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('WikiSearch')
    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)

    DB_CONFIG = {
        "host": config["Database"].get("Host", "localhost"),
        "user": config["Database"].get("User", "wikisearch"),
        "password": config["Database"].get("Password", "dih"),
        "database": config["Database"].get("Name", "indexes")
    }

    LMDB_CONFIG = {
        "path": config["FileDatabase"].get("Path", "./lmdb_store"),
        "size": int(config["FileDatabase"].get("Size", 10**9))
    }

    PROCESSOR_CONFIG = {
        "path": config["WikipediaProcessor"].get("Path", "bgwiki-20250120-pages-articles.xml"),
        "seed_urls": config["Crawler"].get("SeedURLs", "root"),
        "crawl_limit": int(config["WikipediaProcessor"].get("CrawlLimit", "")),
    }

    db_connection_service = DatabaseConnectionService(DB_CONFIG)
    if not os.path.exists(LMDB_CONFIG["path"]):
        os.makedirs(LMDB_CONFIG["path"])
    lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=LMDB_CONFIG["size"])

    with DatabaseConnectionService(DB_CONFIG) as connection:
        processor = WikipediaProcessor(
            connection, lmdb_env, None, Path(PROCESSOR_CONFIG["path"]), PROCESSOR_CONFIG["crawl_limit"])
        processor.process_dump()
