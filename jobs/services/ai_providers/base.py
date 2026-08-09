from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AIProviderBase(ABC):
    """Base class for AI providers"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.model = self.config.get('model', getattr(settings, 'AI_MODEL', 'gpt-4'))
        self.temperature = self.config.get('temperature', getattr(settings, 'AI_TEMPERATURE', 0.3))
        self.max_tokens = self.config.get('max_tokens', getattr(settings, 'AI_MAX_TOKENS', 2000))
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize the AI client"""
        pass
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass
    
    @abstractmethod
    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using AI"""
        pass
    
    @abstractmethod
    def extract_job_details(self, job_description: str) -> Dict:
        """Extract structured job details from description"""
        pass
    
    @abstractmethod
    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect if two jobs are duplicates with similarity score"""
        pass