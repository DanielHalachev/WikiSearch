
from pathlib import Path
from typing import List

from hunspell import HunSpell


class HunSpellChecker:
    def __init__(self, aff_path: Path, dic_path: Path):
        """
        Initialize the SpellChecker with paths to .aff and .dic files.

        :param aff_path: Path to the .aff file.
        :param dic_path: Path to the .dic file.
        """
        self.spell_checker = HunSpell(dic_path, aff_path)

    def spellcheck(self, string: str) -> str:
        tokens = string.split(" ")
        return " ".join(self.check_and_correct(tokens))

    def check_and_correct(self, tokens: List[str]) -> List[str]:
        """
        Check and correct misspelled words in the input tokens.

        :param tokens: List of query tokens to spell-check.
        :return: A tuple containing:
                 1. List of tokens with corrections applied.
                 2. List of indices in the input tokens where corrections were made.
        """
        corrections = []

        for i, token in enumerate(tokens):
            if not self.spell_checker.spell(token):
                suggestions = self.spell_checker.suggest(token)
                if suggestions:
                    corrections.append(suggestions[0])
                else:
                    corrections.append(token)
            else:
                corrections.append(token)

        return corrections
