import os

import logging
from app.config import settings
from typing import Optional
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = settings.model
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "https://ChatAgent/",
                "X-OpenRouter-Title": "ChatAgent",
            },
        )

    def generate_reply(self, message: str, history: list[dict[str, str]] | None = None, system_prompt: str | None = None,) -> str:
        if not self.api_key:
            return (
                "OpenRouter API key is not configured. "
                "Set OPENROUTER_API_KEY in the environment to enable live replies."
            )
        
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        if history:
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        except RateLimitError as e:
            logger.exception(f"Rate Limit detected {e}")
            return None
        except Exception as e:
            logger.exception(f"Exception while generating response : {e}")
            return None

        response = self._extract_content(response=response) 
        logger.info(f"Response Generated : {response}")
        if not response:
            response = "Error while generating response from LLM"
        return response
    
    def _extract_content(self, response) -> Optional[str]:
        """Safely extract text content from an OpenAI chat response."""
        try:
            choices = response.choices
            if not choices:
                return None
            msg = choices[0].message
            if msg is None:
                return None

            # Handle text
            if isinstance(msg.content, str) and msg.content.strip():
                return msg.content

            # Handle structured content
            if isinstance(msg.content, list):
                logger.warning("Received List message instead of raw text")
                text = "".join(
                    part.get("text", "") for part in msg.content if part.get("type") == "text"
                )
                if text.strip():
                    return text

            # Handle tool calls
            if getattr(msg, "tool_calls", None):
                logger.warning("Received tool call instead of text")
                return None

            logger.warning("Empty or unsupported content in response")
            return None
        except (AttributeError, IndexError, TypeError) as e:
            logger.exception("Failed to extract content: %s", e)
            return None
