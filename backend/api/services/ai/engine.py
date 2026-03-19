"""
AI Engine — core OpenAI client shared by all AI modules.

Every module defines its own system prompt and builds its own user message.
The engine just handles the API call, retries, and response parsing.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class AIEngine:
    """Thin wrapper around the OpenAI chat completions API."""

    def __init__(self, model="gpt-4o-mini", temperature=0.7, max_tokens=3000):
        import openai

        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )
        self._client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, system_prompt, user_message, expect_json=True):
        """
        Send a system + user message pair to OpenAI.

        Args:
            system_prompt: The system-level instructions.
            user_message:  The user-level content.
            expect_json:   If True, parse the response as JSON.

        Returns:
            Parsed JSON dict (if expect_json) or raw string.

        Raises:
            RuntimeError on API or parsing failure.
        """
        logger.info("AIEngine.chat  model=%s  json=%s", self.model, expect_json)

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

        raw = response.choices[0].message.content.strip()

        if not expect_json:
            return raw

        return self._parse_json(raw)

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json(raw):
        """Strip markdown fences and parse JSON."""
        text = raw
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("AI returned invalid JSON: %s", text[:300])
            raise RuntimeError(
                "AI returned an invalid response. Please try again."
            )
