import os
import json
import logging
from typing import Dict, List, Optional

from groq import Groq
from django.conf import settings
from .base import AIProviderBase

logger = logging.getLogger(__name__)

class GroqProvider(AIProviderBase):
    """Groq API provider with flexible AI parsing"""

    def _initialize_client(self):
        """Initialize the Groq client."""
        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            logger.warning("GROQ_API_KEY not found in settings.")
            self.client = None
            return

        try:
            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self.client = None

    def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Groq"""
        if not self.client:
            logger.error("Groq client not initialized.")
            return "Error: Groq client not initialized."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert job data extractor. Extract job information from text and return clean JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return json.dumps({"error": str(e)})

    def generate_embedding(self, text: str) -> List[float]:
        """Groq doesn't provide embeddings, use fallback"""
        logger.warning("Groq doesn't provide embeddings")
        return []

    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Analyze job match using AI"""
        if not self.client:
            return self._get_fallback_analysis()
        
        try:
            prompt = self._create_match_analysis_prompt(job_data, user_profile)
            response = self.generate_text(prompt)
            
            # Clean response
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
        except Exception as e:
            logger.error(f"Error in analyze_job_match: {e}")
            return self._get_fallback_analysis()

    def extract_job_details(self, text: str) -> Dict:
        """Extract job details from text using a flexible prompt"""
        if not self.client:
            logger.error("Groq client not initialized")
            return {}

        try:
            # ============================================
            # THE FLEXIBLE PROMPT - Let AI do the work
            # ============================================
            prompt = f"""
            Extract all job information from this text.

            IMPORTANT: This is raw text from a job posting. It could be from any job site.
            Find and extract whatever information is available.

            Return a JSON object with these fields (use empty values if not found):
            - title: The job title
            - company: The company name
            - location: Job location (city, state, or "Remote")
            - salary: Salary information (if mentioned)
            - description: Full job description (combine all relevant text)
            - requirements: List of requirements, skills, qualifications needed
            - responsibilities: List of job duties and responsibilities
            - benefits: List of benefits and perks
            - qualifications: List of preferred qualifications
            - experience_required: Required experience (e.g., "5+ years")
            - education_required: Required education (e.g., "Bachelor's degree")
            - work_arrangement: "Remote", "Hybrid", or "On-site"
            - job_type: "FULL_TIME", "PART_TIME", "CONTRACT", "FREELANCE", or "INTERNSHIP"
            - experience_level: "ENTRY", "MID", "SENIOR", or "EXECUTIVE"

            Be thorough but only include what you find. If a field isn't mentioned, leave it empty.

            Here is the job posting text:

            {text[:8000]}

            Return ONLY valid JSON, no other text.
            """
            
            response = self.generate_text(prompt)
            
            # Clean response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            
            result = json.loads(response.strip())
            logger.info(f"✅ AI extracted job data: {result.get('title', 'Unknown')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting job details: {e}")
            return {}

    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        """Detect duplicates using AI"""
        if not self.client:
            return self._fallback_duplicate_detection(job1, job2)
        
        try:
            prompt = f"""
            Compare these two jobs and return a similarity score from 0 to 1.
            Consider title, company, description, and requirements.
            
            Job 1: {json.dumps(job1)}
            Job 2: {json.dumps(job2)}
            
            Return JSON: {{"similarity_score": 0.0-1.0}}
            """
            
            response = self.generate_text(prompt)
            result = json.loads(response.strip())
            return result.get('similarity_score', 0.0)
            
        except Exception as e:
            logger.error(f"Error in detect_duplicates: {e}")
            return self._fallback_duplicate_detection(job1, job2)

    def _create_match_analysis_prompt(self, job_data: Dict, user_profile: Dict) -> str:
        """Create prompt for job match analysis"""
        return f"""
        Analyze the match between this job and candidate profile.
        Return JSON with:
        - match_score: 0-100
        - skill_match: list of matching skills
        - culture_fit: 0-100
        - recommendation: "Highly Recommended", "Recommended", "Consider", or "Not Recommended"
        - reasons: list of reasons for the match
        - concerns: list of potential issues

        Job: {json.dumps(job_data)}
        Candidate: {json.dumps(user_profile)}
        """

    def _get_fallback_analysis(self) -> Dict:
        """Return fallback analysis"""
        return {
            'match_score': 50,
            'skill_match': [],
            'culture_fit': 50,
            'recommendation': 'Manual review recommended',
            'reasons': ['AI service unavailable'],
            'concerns': ['Unable to perform AI analysis']
        }

    def _fallback_duplicate_detection(self, job1: Dict, job2: Dict) -> float:
        """Fallback duplicate detection"""
        try:
            title1 = job1.get('title', '').lower().strip()
            title2 = job2.get('title', '').lower().strip()
            company1 = job1.get('company', '').lower().strip()
            company2 = job2.get('company', '').lower().strip()
            
            if title1 == title2 and company1 == company2:
                return 0.95
            
            if company1 == company2 and self._text_similarity(title1, title2) > 0.7:
                return 0.8
            
            return 0.3
            
        except Exception:
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