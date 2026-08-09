import os
import json
import logging
from typing import Dict, List, Optional

from groq import Groq
from django.conf import settings
from .base import AIProviderBase

logger = logging.getLogger(__name__)

class GroqProvider(AIProviderBase):
    """Groq API provider for super-fast AI inference."""

    def _initialize_client(self):
        """Initialize the Groq client."""
        api_key = getattr(settings, 'GROQ_API_KEY', None)
        if not api_key:
            logger.warning("GROQ_API_KEY not found in settings.")
            self.client = None
            return

        try:
            # The client automatically uses the GROQ_API_KEY environment variable
            # if no api_key argument is passed, but we'll pass it explicitly.
            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            self.client = None

    def generate_text(self, prompt: str, **kwargs) -> str:
        if not self.client:
            logger.error("Groq client not initialized.")
            return "Error: Groq client not initialized."

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
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return json.dumps({"error": str(e)})

    def generate_embedding(self, text: str) -> List[float]:
        """Groq does not currently provide an embedding API."""
        logger.warning("Groq does not provide an embedding API. Using a fallback.")
        return []

    def analyze_job_match(self, job_data: Dict, user_profile: Dict) -> Dict:
        if not self.client:
            return self._get_fallback_analysis()
        try:
            prompt = self._create_match_analysis_prompt(job_data, user_profile)
            response = self.generate_text(prompt)

            # Clean the response (remove markdown code fences if present)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()

            result = json.loads(response)
            return {
                'match_score': result.get('match_score', 50),
                'skill_match': result.get('skill_match', []),
                'culture_fit': result.get('culture_fit', 50),
                'recommendation': result.get('recommendation', 'Review recommended'),
                'reasons': result.get('reasons', ['Analysis completed via Groq.']),
                'concerns': result.get('concerns', [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq response as JSON: {e}. Response: {response[:200]}")
            return self._get_fallback_analysis()
        except Exception as e:
            logger.error(f"Error in Groq analyze_job_match: {e}")
            return self._get_fallback_analysis()

    def extract_job_details(self, job_description: str) -> Dict:
        # ... (implementation similar to other providers) ...
        return {}

    def detect_duplicates(self, job1: Dict, job2: Dict) -> float:
        # ... (implementation similar to other providers) ...
        return 0.0

    def _create_match_analysis_prompt(self, job_data: Dict, user_profile: Dict) -> str:
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
        return {
            'match_score': 50,
            'skill_match': [],
            'culture_fit': 50,
            'recommendation': 'Manual review recommended',
            'reasons': ['AI service unavailable, using fallback analysis.'],
            'concerns': ['Unable to perform AI analysis.']
        }