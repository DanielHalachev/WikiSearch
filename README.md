# WikiSearch
A combined TF-IDF and semantic search engine, specialized in Bulgarian, operating over the `bg.wikipedia.org` domain.

## Capabilities
### Web crawler
- can queue processed pages for indexer
- can store in persistent `LMDB` storage
- for index construction used XML dump instead[^1]
### NLP processing
-  using `sakelariev/bg_news_lg`[^2]
-  stopword removal
- tokenization
- lemmatization
### Embedding Generation
  - using the multilingual `Alibaba-NLP/gte-multinational-base`[^3] sentence-transformer
  - document embeddings stored in `FAISS` or `USearch`
  - vector index can be loaded from persistent storage or from RAM
### TF-IDF Index
  - stored in `MySQL` database in *Boyce-Codd* normal form
  - overcomes HDD latency (yes, I still use an HDD!)
  - allows distributed capabilities
### Positional Index
  - helps with autocompletion and spellchecking
  - convenient base for KWIC Snippet generation
### Query Autocompletion
  - fast and space-efficient storage using Directed Acyclic Word Graphs (DAWGs)
  - two DAWGs - one for single-word completion and one for next-word completion
### Spellchecking
  - using `hunspell`
  - supports default Bulgarian dictionary
  - supports custom dictionary from corpora
### Searching and Ranking
  - semantic search ranks by cosine similarity
  - keyword search uses TF-IDF and BM25
    $$
    \text{BM25}_{d, Q} = \sum_{t \in Q} {\left[\ln \left( \frac{N - \text{df}_t +
    0.5}{\text{df}_t +
    0.5}\right)
    \cdot
    \frac
    {\text{tf}_{t,d} \cdot (k_1 + 1)}
    {\text{tf}_{t,d} + k_1 \cdot \left(1 - b + b
    \cdot\frac{|d|}{\text{avgdl}}\right)}\right]}
    $$

## Project Structure
```
WikiSearch/
├── api.py
├── config.toml
├── uv.lock
├── LICENSE
├── pyproject.toml
├── README.md
├── docs/
│   ├── presentation/
│   └── text/
├── requirements.txt
├── scripts/
│   ├── construct_next_word_dawg.py
│   ├── construct_word_dawg.py
│   ├── initial_crawling.py
│   ├── initial_index_construction.py
│   └── evaluate.py
├── sql/
│   ├── create_db.sql
│   ├── create_structure.sql
│   └── delete.sql
├── ui/
│   ├── gui.py
│   ├── static/
│   └── templates/
└── wikisearch/
    ├── __init__.py
    ├── autocomplete/
    ├── crawler/
    ├── db/
    ├── document/
    ├── eval/
    ├── index/
    ├── nlp/
    ├── spell/
    └── summary/
```
## Benchmarks
### Inverted Index

<ul style="display:flex; justify-content:center;background-color:gray">
    <li style="display:flex; flex-direction:column; align-items: center;flex:1"> Precision
        <bruh style="color: green; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large">0.870</span>
            ± 0.034
        </bruh>
    </li>
    <li style="display:flex; flex-direction:column; align-items:center; flex:1"> Recall
        <bruh style="color: green; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large">0.893 </span>
            ± 0.029
        </bruh>
    </li>
  <li style="display:flex; flex-direction:column; align-items:center;flex:1;"> F1
        <bruh style="color: green; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large;">0.877 </span>
            ± 0.030
        </bruh>
    </li>
</ul>

### Semantic Index
<ul style="display:flex; justify-content:center;background-color:gray">
    <li style="display:flex; flex-direction:column; align-items: center;flex:1"> Precision
        <bruh style="color: red; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large">0.130</span>
            ± 0.021
        </bruh>
    </li>
    <li style="display:flex; flex-direction:column; align-items:center; flex:1"> Recall
        <bruh style="color: red; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large">0.419 </span>
            ± 0.055
        </bruh>
    </li>
  <li style="display:flex; flex-direction:column; align-items:center;flex:1;"> F1
        <bruh style="color: red; display:flex; flex-direction:column;align-items:center">
            <span style="font-size:xx-large;">0.142 </span>
            ± 0.019
        </bruh>
    </li>
</ul>

**Remark:** Comparing vector index results to tf-idf index results is unfair. A TF-IDF index returns only the documents, containing the keywords. A vector index returns as many documents, as the user wants. 

## Possible Future Improvements
- crawl all of `bg.wikipedia.org`
- evaluate system using human evaluators
- combine the semantic and TF-IDF search results into one algorithm (a machine learning task)
- dynamic summaries (KWIC Snippets)
- more fine-grained autocompletion strategy
- support multiple languages by running language detection on a document and a language-specific tokenizer
- distributed database
- performance improvements

## References
[^1]: https://dumps.wikimedia.org/bgwiki/20250120
[^2]: https://huggingface.co/sakelariev/bg_news_lg
[^3]: https://huggingface.co/Alibaba-NLP/gte-multilingual-base

