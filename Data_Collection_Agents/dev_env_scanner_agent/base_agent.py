# # micro_agents/base_agent.py
# import json
# import os
# from abc import ABC, abstractmethod
# from typing import Any, Dict, List, Optional

# from openai import OpenAI


# class BaseMicroAgent(ABC):
#     """
#     Base class for all micro-agents that evaluate code quality.

#     Each micro-agent should implement `evaluate(code_snippets, context)`
#     and return a JSON-serializable dict of stable keys.
#     """

#     def __init__(
#         self,
#         model: str = "gpt-4o-mini",
#         temperature: float = 0.1,
#         api_key: Optional[str] = None,
#         request_timeout: float = 30.0,
#         max_tokens: int = 900,
#     ) -> None:
#         self._api_key = api_key  # resolve lazily if None
#         self._client: Optional[OpenAI] = None
#         self.model = model
#         self.temperature = temperature
#         self.request_timeout = request_timeout
#         self.max_tokens = max_tokens

#     def _get_client(self) -> OpenAI:
#         if self._client is not None:
#             return self._client
#         key = self._api_key or os.getenv("OPENAI_API_KEY")
#         if not key:
#             raise RuntimeError(
#                 "OPENAI_API_KEY is not set. Set env var or pass api_key to BaseMicroAgent."
#             )
#         self._client = OpenAI(api_key=key)
#         return self._client

#     @abstractmethod
#     def evaluate(
#         self, code_snippets: List[str], context: Optional[Dict[str, Any]] = None
#     ) -> Dict[str, Any]:
#         """
#         Evaluate code snippets and return JSON-safe metrics.
#         Implement in subclasses.
#         """
#         raise NotImplementedError

#     def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
#         """
#         Make a call to the LLM and return the raw text reply.
#         """
#         try:
#             client = self._get_client()
#             messages = []
#             if system_prompt:
#                 messages.append({"role": "system", "content": system_prompt})
#             messages.append({"role": "user", "content": prompt})

#             response = client.chat.completions.create(
#                 model=self.model,
#                 messages=messages,
#                 temperature=self.temperature,
#                 max_tokens=self.max_tokens,
#                 timeout=self.request_timeout,
#             )
#             return (response.choices[0].message.content or "").strip()
#         except Exception as exc:
#             # Keep this silent-ish in production; okay to print while iterating.
#             print(f"LLM call failed: {exc}")
#             return ""

#     @staticmethod
#     def _parse_json_response(response: str) -> Dict[str, Any]:
#         """
#         Parse JSON from a possibly noisy LLM response.
#         Handles fenced code blocks and stray prose.
#         """
#         if not response:
#             return {}

#         # 1) Try to extract fenced JSON ```json ... ```
#         start = response.find("```json")
#         if start != -1:
#             start += len("```json")
#             end = response.find("```", start)
#             if end != -1:
#                 blob = response[start:end].strip()
#                 try:
#                     return json.loads(blob)
#                 except Exception:
#                     pass

#         # 2) Try generic fenced block ``` ... ```
#         start = response.find("```")
#         if start != -1:
#             start += len("```")
#             end = response.find("```", start)
#             if end != -1:
#                 blob = response[start:end].strip()
#                 try:
#                     return json.loads(blob)
#                 except Exception:
#                     pass

#         # 3) Last resort: find the first '{' and parse until last '}'.
#         l = response.find("{")
#         r = response.rfind("}")
#         if l != -1 and r != -1 and r > l:
#             blob = response[l : r + 1]
#             try:
#                 return json.loads(blob)
#             except Exception:
#                 pass

#         # 4) Final attempt: direct parse
#         try:
#             return json.loads(response)
#         except Exception:
#             return {}
