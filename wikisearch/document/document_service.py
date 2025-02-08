
from wikisearch.summary.summary_service import SummaryService


class DocumentService():
    def __init__(self, db_connection, lmdb_env) -> None:
        self.db_connection = db_connection
        self.cursor = self.db_connection.cursor()
        self.summarizer = SummaryService(lmdb_env)

    def fetch_document(self, document_id: int, score: float):
        self.cursor.execute(
            "SELECT id, title, url FROM document WHERE id = %s", (document_id,))
        document = self.cursor.fetchone()
        if document is None:
            return None
        summary = self.summarizer.summarize_static(document_id)
        return {"document_id": document_id, "title": document[1],
                "url": document[2], "summary": summary, "score": score}
