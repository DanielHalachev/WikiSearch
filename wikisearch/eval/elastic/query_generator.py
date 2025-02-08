import json
import os
import random
import re
from pathlib import Path
from typing import List

import lmdb
import nltk
import requests
import tomli
from dotenv import load_dotenv
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures

from wikisearch.db.database_connection import DatabaseConnectionService

nltk.download('punkt')
nltk.download('stopwords')


class QueryGenerator:
    def __init__(self, db_connection, lmdb_env):
        self.db_connection = db_connection
        self.lmdb_env = lmdb_env
        self.cursor = self.db_connection.cursor()

    def get_random_article_titles(self, n) -> List[str]:
        """
        Fetch n random document titles from the MySQL 'documents' table.
        """
        self.cursor.execute("""
            SELECT title FROM document
            WHERE id IN (SELECT * FROM usearch) 
            ORDER BY RAND() 
            LIMIT %s
        """, (n, ))
        return [row[0] for row in self.cursor.fetchall()]

    def extract_collocations_from_random_articles(self, n_articles):
        """
        For each of n random articles (from namespace 0), fetch the article content and extract 2 bigram collocations.
        Returns a list of collocation phrases.

        Note: If fewer than 2 collocations are found for an article, all available collocations are used.
        """
        self.cursor.execute("""
            SELECT id FROM document
            WHERE id IN (SELECT * FROM usearch) 
            ORDER BY RAND() 
            LIMIT %s
        """, (n_articles, ))
        doc_ids = [row[0] for row in self.cursor.fetchall()]
        collocations = []
        for doc_id in doc_ids:
            with self.lmdb_env.begin(write=True) as txn:
                text = txn.get(str(doc_id).encode()).decode().replace('\n', ' ')

                tokens = nltk.word_tokenize(text)
                tokens = [token.lower()
                          for token in tokens if re.match(r'\w+', token)]

                finder = BigramCollocationFinder.from_words(tokens)
                # Only consider bigrams that occur at least 3 times.
                finder.apply_freq_filter(3)
                bigram_measures = BigramAssocMeasures()
                article_collocations = finder.nbest(bigram_measures.pmi, 2)

                for bigram in article_collocations:
                    collocations.append(" ".join(bigram))

        return collocations

    def get_top_articles(self, n, year="2024", month="12"):
        """
        Legacy: Uses Wikimedia's Pageviews API to fetch the top viewed articles for a given year/month.
        Only articles in the main namespace (namespace 0) are kept.
        """
        # articles_api = "https://bg.wikipedia.org/w/api.php"
        pageviews_api = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/bg.wikipedia.org/all-access/{year}/{month}/all-days"

        url = pageviews_api.format(year=year, month=month)
        response = requests.get(url)
        with open(Path("/data/WikiSearchData/Stats/most-read.json")) as f:
            data = response.json() if response.status_code == 200 else json.load(f)

        articles = data["items"][0]["articles"]
        filtered_articles = [a for a in articles if ":" not in a["article"]]

        top_articles = [a["article"].replace(
            "_", " ") for a in filtered_articles[1:]]
        return top_articles[:n]

    def get_queries(self, total_queries=30, queries_per_strategy=None, year="2024", month="12"):
        """
        Returns a combined list of queries using the three strategies:
          - "random": Random article titles.
          - "collocations": Two collocations from each of n random articles.
          - "top": Most viewed articles (namespace 0).

        If queries_per_strategy is provided as a dictionary with keys:
            "random", "collocations", "top"
        then:
          - For "random" and "top", the value is the number of queries desired.
          - For "collocations", the value is the number of articles to process (each yielding 2 queries).
        Otherwise, the method randomly allocates numbers so that:

            total_queries = (# random titles) + (# top articles) + 2 * (# collocation articles)

        If there is any shortfall or surplus, extra random article titles are used or the list is trimmed.
        """
        # The three strategies:
        # "random": returns as many queries as requested.
        # "collocations": returns 2 * (number of articles processed).
        # "top": returns as many queries as requested.
        if queries_per_strategy:
            # Ensure all three strategies are specified.
            required_keys = {"random", "collocations", "top"}
            if set(queries_per_strategy.keys()) != required_keys:
                raise ValueError(
                    "queries_per_strategy must contain exactly the keys: random, collocations, and top")
            random_count = queries_per_strategy["random"]
            collocation_count = queries_per_strategy["collocations"]
        else:
            # Random allocation:
            # We first randomly choose counts for "random" and "top", then derive collocation_articles.
            # Ensure at least 1 query for random and top.
            collocation_count = random.randint(1, total_queries // 3)
            random_count = total_queries - collocation_count
            # Adjust in case we have leftover queries.

        print(
            f"Allocation per strategy: random: {random_count} queries, collocations: {collocation_count} articles (≈ {2 * collocation_count} queries)")

        queries = []
        # Strategy 1: Random Article Titles
        if random_count > 0:
            queries.extend(self.get_random_article_titles(random_count))
        # Strategy 2: Collocations from random articles (2 per article)
        if collocation_count > 0:
            collocation_queries = self.extract_collocations_from_random_articles(
                collocation_count // 2)
            queries.extend(collocation_queries)

        if len(queries) > total_queries:
            queries = queries[:total_queries]
        elif len(queries) < total_queries:
            extra_needed = total_queries - len(queries)
            queries.extend(self.get_random_article_titles(extra_needed))
        # Shuffle the queries to mix them up.
        random.shuffle(queries)
        return queries


def main():
    path_to_config = Path("./config.toml")
    with open(path_to_config, "rb") as f:
        config = tomli.load(f)

    load_dotenv()
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_DATABASE"),
    }

    LMDB_CONFIG = {
        "path": config["FileDatabase"].get("Path", "./lmdb_store"),
        "size": int(config["FileDatabase"].get("Size", 10**9))
    }
    lmdb_env = lmdb.open(LMDB_CONFIG["path"], map_size=LMDB_CONFIG["size"])
    with DatabaseConnectionService(DB_CONFIG) as connection:
        generator = QueryGenerator(connection, lmdb_env)

    queries = generator.get_queries(total_queries=30)

    print("\n=== Generated Queries ===")
    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}")


if __name__ == "__main__":
    main()
