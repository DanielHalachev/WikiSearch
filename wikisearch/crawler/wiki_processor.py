import logging
import os
from pathlib import Path

import lmdb
import mwparserfromhell
import tomli
import tqdm
from lxml import etree

from wikisearch.crawler.shared_buffer import SharedBuffer
from wikisearch.db.DatabaseConnection import DatabaseConnectionService


class WikipediaProcessor:
    def __init__(self, mysql_conn, lmdb_env: lmdb.Environment, shared_buffer: SharedBuffer | None, xml_file_path: Path, total_pages: int):
        """
        Initialize the WikipediaProcessor with MySQL connection, LMDB environment, and SharedBuffer.

        :param mysql_conn: MySQL database connection instance (from a connection pool).
        :param lmdb_env: LMDB environment instance for storing documents.
        :param shared_buffer: SharedBuffer instance to add document data.
        :param xml_file_path: Path to the extracted Wikipedia XML dump.
        :param total_pages: Total number of pages to process (for progress bar).
        """
        self.conn = mysql_conn
        self.lmdb_env = lmdb_env
        # self.shared_buffer = shared_buffer
        self.xml_file_path = xml_file_path
        self.cursor = self.conn.cursor()
        self.total_pages = total_pages
        self.logger = logging.getLogger(__name__)

    def extract_text(self, raw_text):
        """
        Extracts clean text from raw Wikipedia markup using mwparserfromhell.
        :param raw_text: Raw Wikipedia markup text.
        :return: Clean, plain text extracted from the markup.
        """
        self.logger.debug("Extracting text from raw markup.")
        wikicode = mwparserfromhell.parse(raw_text)
        return wikicode.strip_code()

    def save_page(self, url, title, content):
        """
        Saves the crawled page content to MySQL and LMDB using the MySQL-generated document ID.
        :param url: The URL of the page.
        :param title: The title of the page.
        :param content: The extracted text content of the page.
        """
        self.logger.info(f"Saving page: {title} ({url})")
        self.cursor.execute(
            "INSERT INTO document (title, url) VALUES (%s, %s)",
            (title, url)
        )
        self.conn.commit()

        document_id = self.cursor.lastrowid
        self.logger.debug(
            f"Document ID {document_id} generated for page: {title}")

        with self.lmdb_env.begin(write=True) as txn:
            txn.put(str(document_id).encode(), content.encode())

        # self.shared_buffer.put((document_id, title, content))
        self.logger.debug(f"Page {title} saved to LMDB and shared buffer.")

    def process_dump(self):
        """
        Process the extracted Wikipedia XML dump file, parse each page, and save it to LMDB and MySQL.
        Uses iterparse() to efficiently handle large XML files.
        """
        self.logger.info(f"Starting to process XML dump: {self.xml_file_path}")
        NAMESPACE = "{http://www.mediawiki.org/xml/export-0.11/}"
        ns = {"mw": "http://www.mediawiki.org/xml/export-0.11/"}
        context = etree.iterparse(
            self.xml_file_path, tag=f"{NAMESPACE}page", huge_tree=True)

        with tqdm.tqdm(total=self.total_pages, unit='page', desc='Processing Pages') as pbar:
            for event, elem in context:
                ns_elem = elem.find("mw:ns", ns)
                namespace = int(ns_elem.text)
                if namespace != 0:
                    self.logger.debug(
                        f"Skipping metapage - wrong namespace {namespace}")
                    elem.clear()
                    continue

                title_elem = elem.find("mw:title", ns)
                title = title_elem.text if title_elem is not None else ""
                if title == "":
                    self.logger.debug("Skipping page with no title.")
                    elem.clear()
                    continue

                text_elem = elem.find(".//mw:text", ns)
                raw_text = text_elem.text if text_elem is not None else ""
                if raw_text == "":
                    self.logger.debug(f"Skipping page with no text: {title}")
                    elem.clear()
                    continue

                url = f'https://bg.wikipedia.org/wiki/{title.replace(" ", "_")}'

                self.logger.debug(f"Processing page: {title}")
                content = self.extract_text(raw_text)

                print(content)

                self.save_page(url, title, content)

                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                pbar.update(1)
        # self.shared_buffer.put((-1, "", ""))
        self.logger.info("Finished processing XML dump.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('WikiSearch')
    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)

    DB_CONFIG = {
        "host": config["Database"].get("Host", "localhost"),
        "user": config["Database"].get("User", "root"),
        "password": config["Database"].get("Password", ""),
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
