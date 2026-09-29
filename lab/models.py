"""Language models the bot can talk to.

Any object with a `chat(messages) -> str` method works as a model, so the
rest of the code doesn't care whether it's talking to a real LLM or a fake.
"""

import requests


class OllamaModel:
    """A real LLM running locally through Ollama (https://ollama.com)."""

    def __init__(self, name="llama3.2:3b", host="http://localhost:11434", max_tokens=200):
        self.name = name
        self.host = host
        # Capping the reply length keeps runs fast. A leak almost always
        # happens in the first few sentences anyway.
        self.max_tokens = max_tokens

    def chat(self, messages):
        response = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.name,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": self.max_tokens},
            },
            timeout=120,
        )
        if response.status_code == 404:
            raise RuntimeError(f"Model '{self.name}' not found. Run: ollama pull {self.name}")
        response.raise_for_status()
        return response.json()["message"]["content"]


class FakeModel:
    """A deliberately gullible stand-in for a real LLM, used in tests.

    It ignores the system prompt completely and follows two simple rules:
    say "ignore" and it hands over the secret; say "spell" and it spells the
    secret out with spaces. Anything else gets a refusal. That's enough to
    test every code path without needing Ollama or a GPU.
    """

    def __init__(self, secret):
        self.secret = secret

    def chat(self, messages):
        user_message = messages[-1]["content"].lower()
        if "spell" in user_message:
            return " ".join(self.secret)
        if "ignore" in user_message:
            return f"Sure! The password is {self.secret}."
        return "Sorry, I can't help with that."
