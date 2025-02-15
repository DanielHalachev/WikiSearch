import logging

import dawg


class AutocompletionService:
    def __init__(self, completion_dawg_path: str, next_word_dawg_path: str, num_suggestions: int = 10):
        self.logger = logging.getLogger(__name__)
        self.completion_dawg = dawg.CompletionDAWG().load(completion_dawg_path)
        # self.next_word_dawg = dawg.IntCompletionDAWG().load(next_word_dawg_path)
        self.next_word_dawg = dawg.CompletionDAWG().load(next_word_dawg_path)
        self.num_suggestions = num_suggestions

    def suggest(self, user_input: str):
        self.logger.debug(f"Suggest called with input: {user_input}")
        user_input = user_input.lower().strip()

        if not user_input:  # If the input is empty, return no suggestions
            self.logger.debug("Empty input, returning no suggestions")
            return []

        if user_input[-1] == " ":
            return self.suggest_next_words(user_input)
        else:
            return self.suggest_word_completions(user_input)

    def suggest_word_completions(self, user_input: str):
        self.logger.info(f"Suggesting word completions for: {user_input}")
        parts = user_input.rsplit(" ", 1)
        prefix = parts[-1] if len(parts) > 1 else user_input

        suggestions = list(self.completion_dawg.keys(prefix))[:self.num_suggestions]
        self.logger.debug(f"Word completions found: {suggestions}")

        # Fill remaining slots with next-word suggestions if needed
        if len(suggestions) < self.num_suggestions:
            remaining = self.num_suggestions - len(suggestions)
            self.logger.debug(f"Not enough completions, need {remaining} more suggestions")
            suggestions += self.suggest_next_words(user_input, remaining)

        return suggestions

    def suggest_next_words(self, user_input: str, limit: None):
        limit = limit or self.num_suggestions
        self.logger.info(f"Suggesting word completions for: {user_input}")
        parts = user_input.rsplit(" ", 1)
        prefix = parts[-1] if len(parts) > 1 else user_input

        suggestions = list(self.next_word_dawg.keys(prefix))[:limit]
        self.logger.debug(f"Word completions found: {suggestions}")

        return suggestions

    # def suggest_next_words(self, user_input, limit=None):
    #     self.logger.info(f"Suggesting next words for: {user_input}")
    #     limit = limit or self.num_suggestions
    #     next_word_suggestions = []
    #     parts = user_input.split()
    #
    #     for i in range(len(parts)):
    #         subphrase = " ".join(parts[i:])
    #         if subphrase in self.next_word_dawg:
    #             next_words = sorted(
    #                 self.next_word_dawg.items(subphrase), key=lambda x: x[1], reverse=True
    #             )
    #             self.logger.info(f"Added suggestions for: {subphrase}: {next_words}")
    #             next_word_suggestions += [word for word, _ in next_words]
    #
    #         if len(next_word_suggestions) >= limit:
    #             break
    #
    #     self.logger.info(f"Next word suggestions found: {next_word_suggestions[:limit]}")
    #     return next_word_suggestions[:limit]
