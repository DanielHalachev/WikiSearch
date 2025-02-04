from typing import List, Tuple

import spacy


class NLPService:
    def __init__(self, to_lower_case: bool, preserve_ner_case: bool = False):
        """
        Initialize the NLProcessor class
        """
        self.to_lower_case = to_lower_case
        self.preserve_ner_case = preserve_ner_case
        self.nlp = spacy.load(
            "/home/daniel/.cache/huggingface/hub/models--sakelariev--bg_news_lg/snapshots/0f8ab4cf99a52b766beacad6fdfe74ae981e59e2/")

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


if __name__ == "__main__":
    text = "Григор Ставрев Пърличев е български възрожденец, учител, писател и преводач от Охрид. Пърличев е един от най-дейните участници в борбите за въвеждане на български език в училищата и черквите в града през 60-те години на XIX век. Преди да изиграе ключовата си роля като водач на българското движение срещу гърцизма в Охрид, печели ежегодния конкурс за гръцка поезия на Атинския университет с поемата си „Ὁ Ἁρματωλός“ (1860). Автор е на ценна автобиография, една от най-ранните в българската литература, както и на първия превод (частично запазен) на Омировата „Илиада“ на български."
    nlp = NLPService(to_lower_case=True, preserve_ner_case=False)
    tokens, mapping = nlp.process(string=text)
    print(tokens)
    print(mapping)
    print(nlp.tokenize_with_punct(text))
    # print(nlp.get_entities(text))
