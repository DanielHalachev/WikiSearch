from typing import List, Tuple

import spacy


class NLPService:
    def __init__(self, to_lower_case: bool, preserve_ner_case: bool = False):
        """
        Initialize the NLProcessor class
        """
        self.to_lower_case = to_lower_case
        self.preserve_ner_case = preserve_ner_case
        self.nlp = spacy.load("bg_news_lg")

    def tokenize(self, string: str) -> List[str]:
        """Tokenize a string by performing stopword removal, punctuation removal, lemmatization, and case conversion.
        :param string: The string to be tokenized
        :return: Tuple containing a list of processed tokens and a dictionary mapping original words to lemmas
        """
        doc = self.nlp(string)
        tokens = []

        for token in doc:
            if not token.is_stop and not token.is_punct and not token.text == "\n":
                processed_token = (
                    token.text
                    if not self.to_lower_case
                    else (token.text if (self.preserve_ner_case and token.ent_type_) else token.lemma_)
                )
                tokens.append(processed_token)
        return tokens

    def tokenize_with_punct(self, string: str) -> List[str]:
        """Tokenize a string without performing stopword removal, punctuation removal, lemmatization, and case conversion.
        :param string: The string to be tokenized
        :return: Tuple containing a list of processed tokens and a dictionary mapping original words to lemmas
        """
        doc = self.nlp(string)
        tokens = []

        for token in doc:
            if not token.is_punct or token.text == "." or token.text == "!" or token.text == "?" or token.text == "-":
                tokens.append(token.text.lower())
        return tokens

    def process(self, string: str) -> Tuple[List[str], dict[str, str]]:
        """
        Tokenize a string by performing stopword removal, punctuation removal, lemmatization, and case conversion.
        :param string: The string to be tokenized
        :return: Tuple containing a list of processed tokens and a dictionary mapping original words to lemmas
        """
        doc = self.nlp(string)
        tokens = []
        word_to_lemma: dict[str, str] = {}

        for token in doc:
            if not token.is_stop and not token.is_punct:
                processed_token = (
                    token.text
                    if not self.to_lower_case
                    else (token.text if (self.preserve_ner_case and token.ent_type_) else token.lemma_)
                )
                tokens.append(processed_token)
                word_to_lemma[token.text] = processed_token
        return tokens, word_to_lemma

    def get_entities(self, string):
        doc = self.nlp(string)
        return [(ent.text, ent.label_) for ent in doc.ents]
