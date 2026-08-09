import openai
from typing import Dict, List, Optional, Any
import json
import logging
import numpy as np
from django.conf import settings
from .base import AIProviderBase

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProviderBase):
    """OpenAI API provider for job analysis"""
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in settings")
                self.client = None
                return
            
            openai.api_key = api_key
            self.client = openai
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using OpenAI"""
        if not self.client:
            logger.error("OpenAI client not initialized")
            return "Error: OpenAI client not initialized"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert job matching assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI generate_text: {e}")
            return json.dumps({"error": "Unexpected error occurred"})
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        if not self.client:
            logger.error("OpenAI client not initialized")
            return []
        
        try:
            response = self.client.embeddings.create(
                model=getattr(settings, 'AI_EMBEDDING_MODEL', 'text-embedding-ada-002'),
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except openai.APIError as e:
            logger.error(f"OpenAI embedding API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI generate_embedding: {e}")
            return []
    
    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using OpenAI"""
        if not self.client:
            logger.error("OpenAI client not initialized, using fallback")
            return self._get_fallback_analysis()
        
        try:
            prompt = self._create_match_analysis_prompt(job_data, user_profile)
            response = self.generate_text(prompt)
            
            # Try to parse JSON response
            try:
                # Clean the response - sometimes OpenAI wraps JSON in markdown
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                
                result = json.loads(response.strip())
                return {
                    'match_score': result.get('match_score', 50),
                    'skill_match': result.get('skill_match', []),
                    'culture_fit': result.get('culture_fit', 50),
                    'recommendation': result.get('recommendation', 'Review recommended'),
                    'reasons': result.get('reasons', ['Analysis completed']),
                    'concerns': result.get('concerns', [])
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                return self._get_fallback_analysis()
                
        except Exception as e:
            logger.error(f"Error in analyze_job_match: {e}")
            return self._get_fallback_analysis()
    
    def extract_job_details(self, job_description: str) -> Dict:
        """Extract structured job details using OpenAI"""
        if not self.client:
            logger.error("OpenAI client not initialized")
            return {}
        
        try:
            prompt = f"""
            Extract the following details from this job description and return as JSON.
            If a field is not found, use an empty string or empty list.
            
            Required fields:
            - required_skills: list of strings (skills that are required)
            - preferred_qualifications: list of strings (nice-to-have skills)
            - responsibilities: list of strings (job duties)
            - experience_level: string (entry/mid/senior/executive)
            - education_requirements: list of strings
            - benefits: list of strings
            - work_arrangement: string (remote/hybrid/on-site)
            - salary_range: object with min and max (or null if not mentioned)
            
            Job Description:
            {job_description[:4000]}
            
            Return ONLY valid JSON, no other text.
            """
            
            response = self.generate_text(prompt)
            
            # Clean the response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            
            try:
                return json.loads(response.strip())
            except json.JSONDecodeError:
                logger.error("Failed to parse extracted job details JSON")
                return {}
                
        except Exception as e:
            logger.error(f"Error in extract_job_details: {e}")
            return {}
    
    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect duplicate jobs using OpenAI embeddings"""
        if not self.client:
            logger.warning("OpenAI client not initialized, using text similarity fallback")
            return self._fallback_duplicate_detection(job1, job2)
        
        try:
            # Combine key fields for comparison
            text1 = f"{job1.get('title', '')} {job1.get('company', '')} {job1.get('description', '')[:500]}"
            text2 = f"{job2.get('title', '')} {job2.get('company', '')} {job2.get('description', '')[:500]}"
            
            if not text1 or not text2:
                return 0.0
            
            # Get embeddings
            embedding1 = self.generate_embedding(text1)
            embedding2 = self.generate_embedding(text2)
            
            if not embedding1 or not embedding2:
                return self._fallback_duplicate_detection(job1, job2)
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(embedding1, embedding2)
            return similarity
            
        except Exception as e:
            logger.error(f"Error in detect_duplicates: {e}")
            return self._fallback_duplicate_detection(job1, job2)
    
    def _create_match_analysis_prompt(self, job_data: Dict, user_profile: Dict) -> str:
        """Create prompt for job match analysis"""
        # Safely serialize data
        job_str = json.dumps(job_data, default=str)
        user_str = json.dumps(user_profile, default=str)
        
        return f"""
        Analyze the match between this job and candidate profile.
        Return ONLY valid JSON with these exact fields:
        - match_score: number (0-100)
        - skill_match: list of strings (matching skills)
        - culture_fit: number (0-100)
        - recommendation: string (one of: "Highly Recommended", "Recommended", "Consider", "Not Recommended")
        - reasons: list of strings (why this job matches)
        - concerns: list of strings (potential issues)
        
        Job: {job_str[:2000]}
        Candidate Profile: {user_str[:1000]}
        
        Be thorough and specific. Return ONLY valid JSON, no other text.
        """
    
    def _get_fallback_analysis(self) -> Dict:
        """Return fallback analysis when OpenAI is unavailable"""
        return {
            'match_score': 50,
            'skill_match': [],
            'culture_fit': 50,
            'recommendation': 'Manual review recommended',
            'reasons': ['AI service unavailable, using fallback analysis'],
            'concerns': ['Unable to perform AI analysis']
        }
    
    def _fallback_duplicate_detection(self, job1: Dict, job2: Dict) -> float:
        """Fallback duplicate detection using simple text comparison"""
        try:
            # Compare titles
            title1 = job1.get('title', '').lower().strip()
            title2 = job2.get('title', '').lower().strip()
            
            # Compare companies
            company1 = job1.get('company', '').lower().strip()
            company2 = job2.get('company', '').lower().strip()
            
            # If titles and companies match exactly, it's likely a duplicate
            if title1 == title2 and company1 == company2:
                return 0.95
            
            # If titles are similar and companies match
            if company1 == company2 and self._text_similarity(title1, title2) > 0.7:
                return 0.8
            
            return 0.3
            
        except Exception as e:
            logger.error(f"Error in fallback duplicate detection: {e}")
            return 0.0
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            v1 = np.array(v1)
            v2 = np.array(v2)
            
            if v1.shape != v2.shape:
                logger.warning(f"Embedding shape mismatch: {v1.shape} vs {v2.shape}")
                return 0.0
            
            # Check for zero vectors
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(v1, v2) / (norm1 * norm2)
            return float(max(0, min(1, similarity)))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0