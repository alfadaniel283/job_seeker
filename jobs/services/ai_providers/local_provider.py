from typing import Dict, List, Optional, Any
import json
import logging
import numpy as np
from django.conf import settings
from .base import AIProviderBase

logger = logging.getLogger(__name__)

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class LocalProvider(AIProviderBase):
    """Local AI provider using open-source models"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.model_name = self.config.get('local_model', 'sentence-transformers/all-MiniLM-L6-v2')
        self.tokenizer = None
        self.model = None
    
    def _initialize_client(self):
        """Initialize local models"""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers library not available")
            return
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            logger.info(f"Loaded local model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using local model (simplified)"""
        return "Local text generation not fully implemented. Please use cloud providers for text generation."
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        if not self.tokenizer or not self.model:
            return []
        
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1).detach().numpy()
            return embeddings[0].tolist()
        except Exception as e:
            logger.error(f"Local embedding error: {e}")
            return []
    
    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using local models"""
        job_text = f"{job_data.get('title', '')} {job_data.get('description', '')}"
        user_text = f"{user_profile.get('skills', '')} {user_profile.get('experience', '')}"
        
        embedding1 = self.generate_embedding(job_text)
        embedding2 = self.generate_embedding(user_text)
        
        if embedding1 and embedding2:
            similarity = self._cosine_similarity(embedding1, embedding2)
            match_score = similarity * 100
        else:
            match_score = 50
        
        return {
            'match_score': match_score,
            'skill_match': [],
            'culture_fit': 50,
            'recommendation': 'Manual review recommended' if match_score < 70 else 'Recommended',
            'reasons': ['AI analysis using local model'],
            'concerns': ['Limited analysis capability']
        }
    
    def extract_job_details(self, job_description: str) -> Dict:
        """Extract job details using local model"""
        return {
            'required_skills': [],
            'preferred_qualifications': [],
            'responsibilities': [],
            'experience_level': 'Not specified',
            'education_requirements': [],
            'benefits': [],
            'work_arrangement': 'Not specified'
        }
    
    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect duplicates using local embeddings"""
        text1 = f"{job1.get('title', '')} {job1.get('company', '')} {job1.get('description', '')[:200]}"
        text2 = f"{job2.get('title', '')} {job2.get('company', '')} {job2.get('description', '')[:200]}"
        
        embedding1 = self.generate_embedding(text1)
        embedding2 = self.generate_embedding(text2)
        
        if embedding1 and embedding2:
            return self._cosine_similarity(embedding1, embedding2)
        return 0.0
    
    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity"""
        v1 = np.array(v1)
        v2 = np.array(v2)
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))