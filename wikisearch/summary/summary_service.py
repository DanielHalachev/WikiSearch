
class SummaryService:

    def __init__(self, lmdb_env) -> None:
        self.lmdb_env = lmdb_env

    def summarize_static(self, document_id: int, textLength: int = 200) -> str:
        with self.lmdb_env.begin(write=True) as txn:
            text: str = txn.get(str(document_id).encode()).decode('utf-8').replace('\n', ' ')
            return text[:textLength]
    
    def summarize_dynamic(self, document_id: int, textLength: int = 200) -> str:
        # unimplemented
        return ""
