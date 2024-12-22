import hunspell

from wikisearch.nlp.nlp import NLProcessor


class HunSpellChecker:
    def __init__(self, aff_path: str, dic_path: str):
        """
        Initialize the SpellChecker with paths to .aff and .dic files.

        :param aff_path: Path to the .aff file.
        :param dic_path: Path to the .dic file.
        """
        self.spell_checker = hunspell.HunSpell(dic_path, aff_path)

    def check_and_correct(self, tokens: list[str]) -> tuple[list[str], list[int]]:
        """
        Check and correct misspelled words in the input tokens.

        :param tokens: List of query tokens to spell-check.
        :return: A tuple containing:
                 1. List of tokens with corrections applied.
                 2. List of indices in the input tokens where corrections were made.
        """
        corrected_tokens = tokens[:]
        changes = []

        for i, token in enumerate(tokens):
            if not self.spell_checker.spell(token):
                suggestions = self.spell_checker.suggest(token)
                if suggestions:
                    corrected_tokens[i] = suggestions[0]
                    changes.append(i)

        return corrected_tokens, changes

if __name__ == '__main__':
    document = "Мнго обичам да ямъ."
    processor = NLProcessor()
    tokens = processor.process(document, lower_case=True, preserve_ner_case=False)
    print(tokens)
    checker = SpellChecker("/home/daniel/WikiSearch/data/bg_BG_utf8.aff", "/home/daniel/WikiSearch/data/bg_BG_utf8.dic")
    tokens = checker.check_and_correct(tokens)
    print(tokens)
    # for token in tokens[0]:
    #     print(token.encode('utf-8'))