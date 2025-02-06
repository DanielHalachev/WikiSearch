import dawg


class AutocompletionService:
    def __init__(self, completion_dawg_path: str, next_word_dawg_path: str, num_suggestions: int = 10):
        self.completion_dawg = dawg.CompletionDAWG().load(completion_dawg_path)
        self.next_word_dawg = dawg.IntDAWG().load(next_word_dawg_path)
        self.num_suggestions = num_suggestions

    def suggest(self, user_input: str):
        user_input = user_input.lower().strip()

        if not user_input:  # If the input is empty, return no suggestions
            return []

        if user_input[-1] == " ":
            return self.suggest_next_words(user_input)
        else:
            return self.suggest_word_completions(user_input)

    def suggest_word_completions(self, user_input: str):
        parts = user_input.rsplit(" ", 1)
        prefix = parts[-1] if len(parts) > 1 else user_input
        # prefix_base = parts[0] + " " if len(parts) > 1 else ""

        suggestions = list(self.completion_dawg.keys(prefix))[
            :self.num_suggestions]
        # word_suggestions = [prefix_base + w for w in word_suggestions]

        # Fill remaining slots with next-word suggestions if needed
        if len(suggestions) < self.num_suggestions:
            remaining = self.num_suggestions - len(suggestions)
            suggestions += self.suggest_next_words(user_input, remaining)

        return suggestions

    def suggest_next_words(self, user_input, limit=None):
        limit = limit or self.num_suggestions
        next_word_suggestions = []
        parts = user_input.split()

        for i in range(len(parts)):
            subphrase = " ".join(parts[i:])
            if subphrase in self.next_word_dawg:
                next_words = sorted(
                    self.next_word_dawg.items(subphrase), key=lambda x: x[1], reverse=True
                )
                next_word_suggestions += [
                    # user_input + " " +
                    word for word, _ in next_words]

            if len(next_word_suggestions) >= limit:
                break

        return next_word_suggestions[:limit]
