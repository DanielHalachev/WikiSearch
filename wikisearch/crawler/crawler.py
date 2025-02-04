import logging
import time
import urllib.request
import urllib.robotparser as urlrobot
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from wikisearch.crawler.shared_buffer import SharedBuffer


class WebCrawlerService:
    def __init__(self, total_crawl_limit: int, db_connection, lmdb_env, buffer: SharedBuffer):
        """
        Initializes the web crawler.
        """
        self.logger = logging.getLogger(__name__)
        self.total_count = 0
        self.batch_count = 0
        self.total_crawl_limit = total_crawl_limit
        self.batch_crawl_limit = 0

        self.conn = db_connection
        self.cursor = self.conn.cursor()
        self.lmdb_env = lmdb_env

        self.buffer = buffer

    def _initialize_seed_urls(self, seed_urls: List[str]):
        """Adds initial seed URLs to the queue if not already present in crawler_visited."""
        for url in seed_urls:
            self.cursor.execute("""
                INSERT IGNORE INTO crawler_to_visit (url)
                SELECT %s
                WHERE NOT EXISTS (SELECT 1 FROM crawler_visited WHERE url = %s)
            """, (url, url))
        self.conn.commit()

    def fetch_page(self, url) -> urllib.request._UrlopenRet | None:
        """Fetches the content of a given URL."""
        if self.robot_parser.can_fetch("*", url):
            try:
                site = urllib.request.urlopen(url)
                return site.read()
            except Exception as e:
                self.logger.error(f"Failed to fetch {url}: {e}")
        return None

    def extract_links_and_title(self, html, base_url) -> str | None:
        """Extracts and normalizes links from an HTML page."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = urljoin(base_url, a_tag.get('href'))
            parsed = urlparse(href)
            if parsed.scheme in ('http', 'https') and urlparse(self.domain).netloc == parsed.netloc:
                links.add(href)

        for link in links:
            self.cursor.execute(
                "INSERT IGNORE INTO crawler_to_visit (url) VALUES (%s)", (link,))
        self.conn.commit()
        return soup.title.string if soup.title else ""

    def extract_text(self, html) -> str:
        """Extracts text content from an HTML page."""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['sup', 'othermeaning-box', 'vertical-navbox']):
            tag.decompose()
        return "".join(p.text.replace('\n', ' ') for p in soup.find_all(['p', 'ul']))

    def save_page(self, doc_id, url, title, content):
        """Saves the crawled page content to MySQL and LMDB."""
        self.cursor.execute(
            "INSERT INTO document (doc_id, title, url, summary) VALUES (%s, %s, %s, null)", (doc_id, title, url))
        self.conn.commit()
        document_id = self.cursor.lastrowid

        with self.lmdb_env.begin(write=True) as txn:
            txn.put(str(document_id).encode(), content.encode())

    def crawl_website(self, doc_id: int, url: str):
        self.logger.info(f"Crawling {url}...")
        html = self.fetch_page(url)

        if html is not None:
            text = self.extract_text(html)
            title = self.extract_links_and_title(html, url)
            if title is not None:
                self.save_page(doc_id, url, title, text)
                if self.buffer is not None:
                    self.buffer.put((doc_id, title, text))

        self.cursor.execute(
            "INSERT INTO crawler_visited (url) VALUES (%s)", (url,))
        self.conn.commit()

        self.batch_count += 1
        self.total_count += 1

    def fetch_next(self) -> Tuple[int, str] | None:
        self.cursor.execute("SELECT id, url FROM crawler_to_visit LIMIT 1")
        row = self.cursor.fetchone()
        if not row:
            return None

        doc_id, url = row

        self.cursor.execute(
            "DELETE FROM crawler_to_visit WHERE id = %s", (doc_id,))
        self.conn.commit()

        return doc_id, url

    def crawl(self, seed_urls: List[str], domain: str, batch_crawl_limit: int):
        self.domain = domain
        self.robot_parser = urlrobot.RobotFileParser(
            urljoin(self.domain, "/robots.txt"))
        self.robot_parser.read()
        self.batch_count = 0
        self.batch_crawl_limit = batch_crawl_limit
        self._initialize_seed_urls(seed_urls)

        """Starts the crawling process."""
        self.logger.info(
            f"Starting crawl with a limit of {self.batch_crawl_limit} pages...")

        while (
            (self.batch_crawl_limit is None or self.batch_count < self.batch_crawl_limit) and
                (self.total_crawl_limit is None or self.total_count < self.total_crawl_limit)):
            next = self.fetch_next()
            if next is not None:
                doc_id, url = next
                self.crawl_website(doc_id, url)
                time.sleep(1)  # Be polite to the server

        self.logger.info(
            f"Crawling complete. {self.total_count} pages visited.")
