import json
import random
import re
from pathlib import Path

import nltk
import requests
from bs4 import BeautifulSoup
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures

nltk.download('punkt')
nltk.download('stopwords')


class QueryGenerator:
    def __init__(self):
        self.articles_api = "https://bg.wikipedia.org/w/api.php"
        self.pageviews_api = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/bg.wikipedia.org/all-access/{year}/{month}/all-days"

    def get_random_article_titles(self, n):
        """
        Uses the MediaWiki API to fetch n random article titles from namespace 0.
        """
        params = {
            "action": "query",
            "list": "random",
            "rnnamespace": 0,
            "rnlimit": n,
            "format": "json"
        }
        response = requests.get(self.articles_api, params=params)
        response.raise_for_status()
        data = response.json()
        titles = [item["title"] for item in data["query"]["random"]]
        return titles

    def extract_collocations_from_random_articles(self, n_articles):
        """
        For each of n random articles (from namespace 0), fetch the article content and extract 2 bigram collocations.
        Returns a list of collocation phrases.

        Note: If fewer than 2 collocations are found for an article, all available collocations are used.
        """
        collocations = []
        titles = self.get_random_article_titles(n_articles)
        for title in titles:
            try:
                params = {
                    "action": "parse",
                    "page": title,
                    "prop": "text",
                    "format": "json"
                }
                response = requests.get(self.articles_api, params=params)
                response.raise_for_status()
                data = response.json()

                html_text = data["parse"]["text"]["*"]
                soup = BeautifulSoup(html_text, "html.parser")
                for tag in soup(['sup', 'othermeaning-box', 'vertical-navbox']):
                    tag.decompose()
                text = "".join(p.text.replace('\n', ' ')
                               for p in soup.find_all(['p', 'ul']))

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
            except Exception as e:
                print(
                    f"Warning: Could not process article '{title}'. Reason: {e}")
                continue
        return collocations

    def get_top_articles(self, n, year="2024", month="12"):
        """
        Uses Wikimedia's Pageviews API to fetch the top viewed articles for a given year/month.
        Only articles in the main namespace (namespace 0) are kept.
        """
        url = self.pageviews_api.format(year=year, month=month)
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
            # number of articles to process
            collocation_articles = queries_per_strategy["collocations"]
            top_count = queries_per_strategy["top"]
        else:
            # Random allocation:
            # We first randomly choose counts for "random" and "top", then derive collocation_articles.
            # Ensure at least 1 query for random and top.
            random_count = random.randint(1, total_queries // 3)
            top_count = random.randint(1, total_queries // 3)
            remaining = total_queries - (random_count + top_count)
            # Since collocations produce 2 queries per article, the number of articles to process is:
            collocation_articles = remaining // 2
            # Adjust in case we have leftover queries.
            leftover = remaining - (2 * collocation_articles)
            random_count += leftover  # add leftover to random titles

        print(
            f"Allocation per strategy: random: {random_count} queries, collocations: {collocation_articles} articles (≈ {2 * collocation_articles} queries), top: {top_count} queries")

        queries = []
        # Strategy 1: Random Article Titles
        if random_count > 0:
            queries.extend(self.get_random_article_titles(random_count))
        # Strategy 2: Collocations from random articles (2 per article)
        if collocation_articles > 0:
            collocation_queries = self.extract_collocations_from_random_articles(
                collocation_articles)
            queries.extend(collocation_queries)
        # Strategy 3: Most Viewed Articles
        if top_count > 0:
            queries.extend(self.get_top_articles(
                top_count, year=year, month=month))

        if len(queries) > total_queries:
            queries = queries[:total_queries]
        elif len(queries) < total_queries:
            # Fill the gap with extra random article titles.
            extra_needed = total_queries - len(queries)
            queries.extend(self.get_random_article_titles(extra_needed))
        # Shuffle the queries to mix them up.
        random.shuffle(queries)
        return queries


def main():
    generator = QueryGenerator()

    # Example using explicit allocation:
    # Note: For the "collocations" strategy, the value represents the number of articles to process,
    # and will contribute 2 queries per article.
    # For example, 30 random, 15 collocation articles (≈30 queries), and 40 top articles would yield 100 queries.
    # queries = generator.get_queries(total_queries=100, queries_per_strategy={"random": 30, "collocations": 15, "top": 40})

    # Example using random allocation:
    queries = generator.get_queries(total_queries=30)

    print("\n=== Generated Queries ===")
    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}")


if __name__ == "__main__":
    main()
