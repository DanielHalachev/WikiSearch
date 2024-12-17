import tomli
import json
import os
from bs4 import BeautifulSoup
import urllib.robotparser as urlrobot
import urllib.request
from urllib.parse import urljoin,urlparse
import time
from pathlib import Path

class WebCrawler:
    def __init__(self, path_to_config):
        """
        Initializes the web crawler.

        Args:
            path_to_config(Path): Path to config file
        """
        with open(path_to_config, "rb") as f:
            config = tomli.load(f)

        seed_urls = config["Crawler"].get("SeedURLs")
        self.crawl_limit = config["Crawler"].getint("CrawlLimit")
        self.domain = config["Crawler"].get("Domain")
        self.visited_urls = set()
        self.to_visit = json.loads(seed_urls)
        self.robot_parser = urlrobot.RobotFileParser(self.domain+"/robots.txt")

    def fetch_page(self, url):
        """
        Fetches the content of a given URL.

        Args:
            url (str): URL to fetch.

        Returns:
            str: HTML content of the page, or None if the request fails.
        """
        if self.robot_parser.can_fetch("*", url):
            site = urllib.request.urlopen(url)
            return site.read()
        return None

    def extract_links_and_title(self, html, base_url):
        """
        Extracts and normalizes links from an HTML page, filtering for the bg.wikipedia.org domain.

        Args:
            html (str): HTML content of the page.
            base_url (str): Base URL of the page for resolving relative links.

        Returns:
            title (str): The title of the webpage
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = urljoin(base_url, a_tag.get('href'))
            parsed = urlparse(href)
            if parsed.scheme in ('http', 'https') and urlparse(self.domain).netloc == parsed.netloc and href not in self.visited_urls:
                links.add(href)

        self.to_visit.extend(links)
        return soup.title.string

    def extract_text(self, html):
        """
        Extracts text content from an HTML page.

        Args:
            html (str): HTML content of the page.

        Returns:
            str: Extracted text content.
        """
        soup = BeautifulSoup(html, 'html.parser')

        for sup in soup.find_all('sup'):
            sup.decompose()

        for other_meanings in soup.find_all(attrs={'class':'othermeaning-box'}):
            other_meanings.decompose()

        for vertical_navbox in soup.find_all(attrs={'class':'vertical-navbox'}):
            vertical_navbox.decompose()

        return "".join(p.text.replace('\n', ' ') for p in soup.find_all(['p', 'ul']))

    def save_page(self, url, title, content, folder):
        """
        Saves the crawled page content to a file.

        Args:
            url (str): URL of the page.
            content (str): Extracted text content of the page.
            title (str): The <title> of the page
            folder (Path): Directory to save the file.
        """
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, str(hash(url))+".json")
        with open(filename, "w", encoding="utf-8" ) as f:
            json.dump({'title': title, 'url':url, 'text': content}, f, ensure_ascii=False)

    def crawl(self, save_directory):
        """
        Starts the crawling process.

        Args:
            save_directory (Path): Directory to save the crawled pages.
        """
        self.robot_parser.read()
        print(f"Starting crawl with a limit of {self.crawl_limit} pages...")

        while self.to_visit and len(self.visited_urls) < self.crawl_limit:
            url = self.to_visit.pop(0)

            if url in self.visited_urls:
                continue

            print(f"Crawling {url}...")
            html = self.fetch_page(url)

            if html is None:
                continue

            text = self.extract_text(html)
            self.visited_urls.add(url)
            title = self.extract_links_and_title(html, url)
            self.save_page(url, title, text, save_directory)

            time.sleep(1)  # Be polite to the server

        print(f"Crawling complete. {len(self.visited_urls)} pages visited.")

if __name__ == "__main__":
    crawler = WebCrawler(Path("./../../config.toml"))
    crawler.crawl(Path("./../../data/raw_pages"))
