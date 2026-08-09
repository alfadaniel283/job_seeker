from typing import Dict, List, Optional, Any
import logging
from django.conf import settings
from .ai_providers.openai_provider import OpenAIProvider
from .ai_providers.anthropic_provider import AnthropicProvider
from .ai_providers.gemini_provider import GeminiProvider
from .ai_providers.local_provider import LocalProvider
from .ai_providers.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

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
        """Initialize AI provider based on settings"""
        provider_name = getattr(settings, 'AI_PROVIDER_PREFERENCE', 'openai').lower()
        
        providers = {
            'openai': OpenAIProvider,
            'anthropic': AnthropicProvider,
            'gemini': GeminiProvider,
            'local': LocalProvider,
            'groq': GroqProvider,
        }
        
        provider_class = providers.get(provider_name)
        
        if provider_class:
            try:
                self._provider = provider_class()
                logger.info(f"Initialized {provider_name} AI provider")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {e}")
                self._provider = LocalProvider()
        else:
            logger.warning(f"Unknown provider {provider_name}, using local")
            self._provider = LocalProvider()
    
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