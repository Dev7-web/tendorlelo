"""
LLM-based metadata extraction using a configurable provider.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


TENDER_PROMPT = """
You are extracting structured metadata from a government tender document.
Return ONLY valid JSON with the following keys:
- title
- department
- sector
- domains (array of strings)
- required_certifications (array of strings)
- required_technologies (array of strings)
- required_experience_years (number or null)
- estimated_value (string or null)
- eligibility_criteria (object with keys: min_turnover, min_experience_years, required_registrations)
- location
- delivery_period
- emd_amount
- summary

Text:
{content}
"""


COMPANY_PROMPT = """
You are extracting structured metadata from a company profile document.
Return ONLY valid JSON with the following keys:
- company_name
- industries (array of strings)
- capabilities (array of strings)
- certifications (array of strings)
- technologies (array of strings)
- domains (array of strings)
- past_clients (array of strings)
- government_experience (boolean or null)
- years_in_business (number or null)
- employee_count (string or null)
- annual_turnover (string or null)
- locations (array of strings)
- registrations (array of strings)
- summary

Text:
{content}
"""


class LLMExtractor:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER.lower()
        self._model = None
        self._client: Optional[httpx.Client] = None

        if self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not configured")
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
        elif self.provider in {"ollama", "local"}:
            self._client = httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS)
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def extract_tender(self, text: str) -> Dict[str, Any]:
        prompt = TENDER_PROMPT.format(content=text[: settings.LLM_INPUT_MAX_CHARS])
        response_text = self._generate(prompt)
        return self._parse_json(response_text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def extract_company(self, text: str) -> Dict[str, Any]:
        prompt = COMPANY_PROMPT.format(content=text[: settings.LLM_INPUT_MAX_CHARS])
        response_text = self._generate(prompt)
        return self._parse_json(response_text)

    def _generate(self, prompt: str) -> str:
        if self.provider == "gemini":
            response = self._model.generate_content(prompt)
            return response.text

        payload = {"model": settings.LLM_MODEL, "prompt": prompt, "stream": False}
        url = settings.LLM_BASE_URL.rstrip("/") + "/api/generate"
        headers = {"Content-Type": "text/plain"}
        response = self._client.post(url, content=json.dumps(payload), headers=headers)
        response.raise_for_status()
        try:
            data = response.json()
            return data.get("response") or data.get("text") or response.text
        except json.JSONDecodeError:
            return response.text

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                logger.info("llm.json_parse_failed", raw=text[:300])
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.info("llm.json_parse_failed", raw=text[:300])
                return {}
