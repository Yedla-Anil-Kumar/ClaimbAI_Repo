# Data_Collection_Agents/base_agent.py
import os
import json
import time
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from openai import OpenAI


class BaseMicroAgent(ABC):
    """Base for micro-agents (with retry & low variance defaults)."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client: Optional[OpenAI] = None
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def evaluate(self, code_snippets: List[str], context: Optional[Dict] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def _get_client(self) -> OpenAI:
        key = self._api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        if self._client is None:
            self._client = OpenAI(api_key=key)
        return self._client

    def _call_llm(self, prompt: str, system_prompt: str = "", max_tokens: int = 900) -> str:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # jitter to desync threads
        time.sleep(random.uniform(0.03, 0.12))

        attempts = 0
        delay = 0.35
        while True:
            attempts += 1
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=max_tokens,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e:
                msg = str(e).lower()
                if attempts < 3 and any(t in msg for t in ("429", "rate", "timeout", "gateway", "500")):
                    time.sleep(delay * (2 ** (attempts - 1)) + random.uniform(0.05, 0.2))
                    continue
                print(f"LLM call failed: {e}")
                return ""

    @staticmethod
    def _parse_json_response(response: str) -> Dict[str, Any]:
        if not response:
            return {}
        try:
            if "```json" in response:
                s = response.find("```json") + 7
                e = response.find("```", s)
                return json.loads(response[s:e].strip())
            if "```" in response:
                s = response.find("```") + 3
                e = response.find("```", s)
                return json.loads(response[s:e].strip())
            return json.loads(response)
        except Exception:
            try:
                s = response.find("{"); e = response.rfind("}")
                if s != -1 and e != -1 and e > s:
                    return json.loads(response[s:e+1])
            except Exception:
                pass
            print("Failed to parse JSON response.")
            return {}
