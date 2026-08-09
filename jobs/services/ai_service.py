from typing import Dict, List, Optional, Any
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _import_provider_class(provider_name: str):
    """Dynamically import only the requested provider's class.

    Each branch imports its provider module lazily, right here, instead of
    at the top of this file. That keeps heavy/optional SDKs (google-genai +
    its grpcio/protobuf chain, transformers/torch for the local provider,
    etc.) completely out of the import path unless that specific provider
    is actually selected via AI_PROVIDER_PREFERENCE. Previously all five
    providers were imported unconditionally at module load time, which is
    what was pulling in google-genai (and crashing the worker) even when
    only Groq was configured.
    """
    if provider_name == 'openai':
        from .ai_providers.openai_provider import OpenAIProvider
        return OpenAIProvider
    elif provider_name == 'anthropic':
        from .ai_providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider
    elif provider_name == 'gemini':
        from .ai_providers.gemini_provider import GeminiProvider
        return GeminiProvider
    elif provider_name == 'local':
        from .ai_providers.local_provider import LocalProvider
        return LocalProvider
    elif provider_name == 'groq':
        from .ai_providers.groq_provider import GroqProvider
        return GroqProvider
    return None


class AIService:
    """Central AI service manager"""

    _instance = None
    _provider = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize AI provider based on settings, importing only the
        selected provider's module (and its dependencies) on demand."""
        provider_name = getattr(settings, 'AI_PROVIDER_PREFERENCE', 'openai').lower()

        try:
            provider_class = _import_provider_class(provider_name)
        except ImportError as e:
            logger.error(f"Could not import provider '{provider_name}': {e}")
            provider_class = None

        if provider_class:
            try:
                self._provider = provider_class()
                logger.info(f"Initialized {provider_name} AI provider")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {e}")
                self._provider = self._get_local_fallback()
        else:
            logger.warning(f"Unknown provider {provider_name}, using local")
            self._provider = self._get_local_fallback()

    def _get_local_fallback(self):
        """Lazily import LocalProvider only when actually needed as a
        fallback, so a failure in e.g. Gemini doesn't drag in torch/
        transformers unless the local provider is genuinely being used."""
        try:
            from .ai_providers.local_provider import LocalProvider
            return LocalProvider()
        except Exception as e:
            logger.error(f"Local provider fallback also failed: {e}")
            return None

    @property
    def provider(self):
        """Get the current AI provider"""
        if not self._provider:
            self._initialize()
        return self._provider

    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using AI"""
        try:
            return self.provider.analyze_job_match(job_data, user_profile)
        except Exception as e:
            logger.error(f"AI match analysis error: {e}")
            return {
                'match_score': 0,
                'skill_match': [],
                'culture_fit': 0,
                'recommendation': 'Error in AI analysis',
                'reasons': [],
                'concerns': ['AI service unavailable']
            }

    def extract_job_details(self, job_description: str) -> Dict:
        """Extract structured job details using AI"""
        try:
            return self.provider.extract_job_details(job_description)
        except Exception as e:
            logger.error(f"AI job extraction error: {e}")
            return {}

    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect duplicate jobs using AI"""
        try:
            return self.provider.detect_duplicates(job1, job2)
        except Exception as e:
            logger.error(f"AI duplicate detection error: {e}")
            return 0.0

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using AI"""
        try:
            return self.provider.generate_embedding(text)
        except Exception as e:
            logger.error(f"AI embedding generation error: {e}")
            return []