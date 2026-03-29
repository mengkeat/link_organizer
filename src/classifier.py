"""
Classification service and LLM providers.
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import litellm
import aiohttp
from .core import get_logger, ClassificationResult

logger = get_logger("classifier")

# --- LLM Providers ---

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None

class LLMProvider(ABC):
    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.timeout = kwargs.get('timeout', 30)

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse: pass
    
    @abstractmethod
    def validate_config(self) -> bool: pass

    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass

class LiteLLMProvider(LLMProvider):
    def validate_config(self) -> bool:
        if not self.api_key: raise ValueError("API key is required")
        if not self.model: raise ValueError("Model is required")
        return True

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        litellm.api_key = self.api_key
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 500)
            )
            choice = response.choices[0]
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = {"prompt_tokens": response.usage.prompt_tokens, 
                         "completion_tokens": response.usage.completion_tokens, 
                         "total_tokens": response.usage.total_tokens}
            return LLMResponse(content=choice.message.content, model=self.model, usage=usage, finish_reason=getattr(choice, 'finish_reason', None))
        except Exception as e:
            logger.error("LiteLLM error: %s", e)
            raise

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if "referer" in self.config: headers["HTTP-Referer"] = self.config["referer"]
        if "title" in self.config: headers["X-Title"] = self.config["title"]
        
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}],
                   "temperature": kwargs.get("temperature", 0.1),
                   "max_tokens": kwargs.get("max_tokens", 500)}
        
        # Use existing session if in context manager, else create one-off
        if self.session:
            async with self.session.post("https://openrouter.ai/api/v1/chat/completions", 
                                    headers=headers, json=payload, timeout=self.timeout) as resp:
                result = await resp.json()
                if "error" in result: raise RuntimeError(f"OpenRouter error: {result['error']}")
                choice = result["choices"][0]
                return LLMResponse(content=choice["message"]["content"], model=result.get("model", self.model), 
                                   usage=result.get("usage"), finish_reason=choice.get("finish_reason"))
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", 
                                        headers=headers, json=payload, timeout=self.timeout) as resp:
                    result = await resp.json()
                    if "error" in result: raise RuntimeError(f"OpenRouter error: {result['error']}")
                    choice = result["choices"][0]
                    return LLMResponse(content=choice["message"]["content"], model=result.get("model", self.model), 
                                       usage=result.get("usage"), finish_reason=choice.get("finish_reason"))

    def validate_config(self) -> bool:
        if not self.api_key: raise ValueError("API key is required")
        if not self.model: raise ValueError("Model is required")
        return True

class LLMProviderType(Enum):
    LITELLM = "litellm"
    OPENROUTER = "openrouter"

class LLMProviderFactory:
    PROVIDERS = {LLMProviderType.LITELLM: LiteLLMProvider, LLMProviderType.OPENROUTER: OpenRouterProvider}

    @classmethod
    def create_provider(cls, provider_type: Union[LLMProviderType, str], api_key: str, model: str, **kwargs) -> LLMProvider:
        if isinstance(provider_type, str):
            try:
                provider_type = LLMProviderType(provider_type.lower())
            except ValueError:
                raise ValueError(f"Unknown provider type: {provider_type}")
        return cls.PROVIDERS[provider_type](api_key, model, **kwargs)

    @classmethod
    def from_env(cls) -> LLMProvider:
        provider_type_str = os.getenv("LLM_PROVIDER", "litellm").lower()
        try:
            provider_type = LLMProviderType(provider_type_str)
        except ValueError:
            raise ValueError(f"Invalid provider type: {provider_type_str}")
        
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("LITELLM_API_KEY")
        if not api_key: raise ValueError("OPENROUTER_API_KEY is required")
        
        model = os.getenv("LITELLM_MODEL", "openrouter/openai/gpt-4o-mini")
        kwargs = {}
        if provider_type == LLMProviderType.OPENROUTER:
            kwargs.update({"referer": os.getenv("OPENROUTER_REFERER"), "title": os.getenv("OPENROUTER_TITLE")})
        return cls.create_provider(provider_type, api_key, model, **kwargs)

    @classmethod
    def get_available_providers(cls) -> Dict[str, str]:
        return {
            "litellm": "LiteLLM provider (supports multiple LLM services)",
            "openrouter": "OpenRouter direct API provider"
        }

# --- Classification Service ---

class ClassificationService:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or LLMProviderFactory.from_env()
        self.categories = ["Technology", "Science", "AI/ML", "Programming", "Research", "Tutorial", "News", "Blog", "Documentation", "Business", "Design", "Security", "Data Science", "Web Development"]
        self.content_types = ["tutorial", "guide", "documentation", "research_paper", "blog_post", "news_article", "reference", "course", "tool"]

    async def classify_content(self, url: str, title: str, content: str) -> ClassificationResult:
        prompt = self.get_classification_prompt(url, title, content)
        try:
            resp = await self.llm_provider.generate(prompt, temperature=0.7)
            data = self._parse_json(resp.content)
            return ClassificationResult(**data)
        except Exception as e:
            logger.error("Classification failed for %s: %s", url, e)
            return self._get_fallback(url, title)

    def get_classification_prompt(self, url: str, title: str, content: str) -> str:
        return f"""Analyze this web content and respond with a JSON object.
URL: {url}
Title: {title}
Content: {content[:4000]}

JSON schema:
{{
  "category": "one of: {', '.join(self.categories)}",
  "subcategory": "specific subcategory",
  "tags": ["3-7 tags"],
  "summary": "2-3 sentence summary",
  "confidence": 0.0-1.0,
  "content_type": "one of: {', '.join(self.content_types)}",
  "difficulty": "beginner/intermediate/advanced",
  "quality_score": 1-10,
  "key_topics": ["main topics"],
  "target_audience": "who it's for"
}}"""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            start, end = text.find('{'), text.rfind('}') + 1
            return json.loads(text[start:end])
        except Exception:
            raise ValueError(f"Could not parse JSON from response: {text[:100]}...")

    def parse_llm_response(self, text: str) -> Dict[str, Any]:
        try:
            return self._parse_json(text)
        except ValueError:
            return self.parse_text_response(text)

    def parse_text_response(self, text: str) -> Dict[str, Any]:
        result = self._get_fallback("unknown", "unknown").model_dump()
        result["confidence"] = 0.5
        if "technology" in text.lower():
            result["category"] = "Technology"
        return result

    def _get_fallback(self, url: str, title: str) -> ClassificationResult:
        return ClassificationResult(
            category="Technology", subcategory="None", tags=["uncategorized"],
            summary=f"Content from {url}", confidence=0.3, content_type="article",
            difficulty="unknown", quality_score=5, key_topics=[title], target_audience="general"
        )

    def get_fallback_classification(self, url: str, title: str, content: str = "") -> ClassificationResult:
        return self._get_fallback(url, title)

    def save_classifications(self, classifications: Dict[str, ClassificationResult], output_file: Path):
        output_file.parent.mkdir(parents=True, exist_ok=True)
        data = {url: res.model_dump() for url, res in classifications.items()}
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    async def classify_existing_links(self, index_file: Path):
        if not index_file.exists(): return {}
        data = json.loads(index_file.read_text(encoding='utf-8'))
        return {item['link']: item.get('classification') for item in data if 'classification' in item}
