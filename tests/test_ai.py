from django.test import TestCase
from jobs.services.ai_service import AIService
from jobs.services.ai_providers.local_provider import LocalProvider
from unittest.mock import patch, Mock

class AIServiceTest(TestCase):
    def setUp(self):
        self.ai_service = AIService()
    
    def test_ai_service_singleton(self):
        service1 = AIService()
        service2 = AIService()
        self.assertEqual(service1, service2)
    
    def test_extract_job_details(self):
        description = """
        We are looking for a Python Developer with 3+ years of experience.
        Skills required: Python, Django, PostgreSQL.
        This is a remote position.
        """
        result = self.ai_service.extract_job_details(description)
        self.assertIsInstance(result, dict)
    
    def test_analyze_job_match(self):
        job_data = {
            'title': 'Python Developer',
            'company': 'Tech Corp',
            'description': 'Looking for Python developer'
        }
        user_profile = {
            'skills': ['python', 'django'],
            'remote_only': True
        }
        result = self.ai_service.analyze_job_match(job_data, user_profile)
        self.assertIn('match_score', result)
        self.assertIn('reasons', result)
        self.assertIn('concerns', result)

class LocalProviderTest(TestCase):
    def setUp(self):
        self.provider = LocalProvider()
    
    def test_generate_embedding(self):
        # Test with a simple text
        embedding = self.provider.generate_embedding("Test text")
        # If transformers is not available, embedding should be empty
        if embedding:
            self.assertIsInstance(embedding, list)
            self.assertGreater(len(embedding), 0)
    
    def test_analyze_job_match(self):
        job_data = {'title': 'Test', 'description': 'Test description'}
        user_profile = {'skills': ['python'], 'experience': '3 years'}
        result = self.provider.analyze_job_match(job_data, user_profile)
        self.assertIn('match_score', result)
        self.assertIn('recommendation', result)