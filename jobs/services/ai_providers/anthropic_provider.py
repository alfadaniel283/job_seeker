import anthropic
from typing import Dict, List, Optional, Any
import json
import logging
from django.conf import settings
from .base import AIProviderBase

logger = logging.getLogger(__name__)

class AnthropicProvider(AIProviderBase):
    """Anthropic Claude API provider"""
    
    def _initialize_client(self):
        """Initialize Anthropic client"""
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Claude"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="You are an expert job matching assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Anthropic doesn't provide embeddings, use fallback"""
        logger.warning("Anthropic doesn't provide embeddings, using text-based similarity")
        return []
    
    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using Claude"""
        prompt = self._create_match_analysis_prompt(job_data, user_profile)
        response = self.generate_text(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Anthropic response")
            return {
                'match_score': 0,
                'skill_match': [],
                'culture_fit': 0,
                'recommendation': 'Error analyzing match',
                'reasons': [],
                'concerns': []
            }
    
    def extract_job_details(self, job_description: str) -> Dict:
        """Extract structured job details using Claude"""
        prompt = f"""
        Extract the following details from this job description as JSON:
        - required_skills: list
        - preferred_qualifications: list
        - responsibilities: list
        - experience_level: string (entry/mid/senior/executive)
        - education_requirements: list
        - benefits: list
        - work_arrangement: string (remote/hybrid/on-site)
        - salary_range: object with min and max
        
        Job Description:
        {job_description[:3000]}
        """
        
        response = self.generate_text(prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Anthropic response")
            return {}
    
    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect duplicates using Claude text analysis"""
        prompt = f"""
        Compare these two jobs and provide a similarity score from 0 to 1.
        Consider title, company, description, requirements, and responsibilities.
        
        Job 1: {json.dumps(job1)}
        Job 2: {json.dumps(job2)}
        
        Return as JSON: {{"similarity_score": 0.0-1.0, "is_duplicate": boolean, "reasoning": "..."}}
        """
        
        response = self.generate_text(prompt)
        
        try:
            result = json.loads(response)
            return result.get('similarity_score', 0.0)
        except json.JSONDecodeError:
            return 0.0
    
    def _create_match_analysis_prompt(self, job_data: Dict, user_profile: Dict) -> str:
        """Create prompt for job match analysis"""
        return f"""
        Analyze the match between this job and candidate profile.
        Provide a comprehensive analysis in JSON format with these fields:
        - match_score: 0-100
        - skill_match: list of matching skills
        - culture_fit: 0-100
        - recommendation: string suggesting whether to apply
        - reasons: list of reasons for the match
        - concerns: list of potential issues
        
        Job: {json.dumps(job_data)}
        Candidate Profile: {json.dumps(user_profile)}
        
        Be detailed and specific.
        """