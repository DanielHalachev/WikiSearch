import spacy

class NLProcessor:
    def __init__(self):
        """
        Initialize the NLProcessor class
        """
        self.nlp = spacy.load("/home/daniel/.cache/huggingface/hub/models--sakelariev--bg_news_lg/snapshots/0f8ab4cf99a52b766beacad6fdfe74ae981e59e2/")

    def process(self, string: str, lower_case: bool, preserve_ner_case: bool):
        """
        Tokenize a string by performing stopword removal, punctuation removal, lemmatization and case conversion.
        :param string: The string to be tokenized
        :param lower_case: Should the processor convert every word lowercase?
        :param preserve_ner_case: Should the processor preserve the case of named entities, if lower_case is True
        :return: List of processed tokens
        """
        doc = self.nlp(string)
        return [
            token.text if not lower_case else (token.text if (preserve_ner_case and token.ent_type_) else token.lemma_)
            for token in doc
            if not token.is_stop and not token.is_punct
        ]

    def get_entities(self, document):
        doc = self.nlp(document)
        return [(ent.text, ent.label_) for ent in doc.ents]
