from django.test import TestCase
from django.contrib.auth.models import User
from jobs.services.job_fetcher import JobFetcher, LinkedInFetcher, IndeedFetcher
from jobs.services.job_evaluator import JobEvaluator
from jobs.models import Job, JobSource, UserJobPreferences
from unittest.mock import Mock, patch

class JobFetcherTest(TestCase):
    def setUp(self):
        self.fetcher = JobFetcher()
    
    @patch('requests.Session.get')
    def test_fetch_page_success(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<html>Test</html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_page('https://example.com')
        self.assertEqual(result, '<html>Test</html>')
    
    def test_generate_content_hash(self):
        job_data = {
            'title': 'Test Job',
            'company': 'Test Company',
            'description': 'Test Description'
        }
        hash1 = self.fetcher.generate_content_hash(job_data)
        hash2 = self.fetcher.generate_content_hash(job_data)
        self.assertEqual(hash1, hash2)
        
        # Different content should produce different hash
        job_data2 = job_data.copy()
        job_data2['title'] = 'Different Job'
        hash3 = self.fetcher.generate_content_hash(job_data2)
        self.assertNotEqual(hash1, hash3)

class JobEvaluatorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.preferences = UserJobPreferences.objects.create(
            user=self.user,
            remote_only=True,
            include_keywords=['python', 'django']
        )
        self.evaluator = JobEvaluator(self.user)
        self.source = JobSource.objects.create(
            url='https://example.com',
            source_type='OTHER',
            name='Test Source'
        )
        self.job = Job.objects.create(
            title='Python Developer',
            description='Looking for a Python developer with Django experience',
            company='Tech Corp',
            location='Remote',
            source=self.source,
            source_url='https://example.com/job',
            posted_date=datetime.now(),
            content_hash='testhash123',
            is_remote=True
        )
    
    def test_evaluate_location(self):
        result = self.evaluator._evaluate_location(self.job)
        self.assertTrue(result)  # Remote only should match remote job
    
    def test_evaluate_skills(self):
        skill_score = self.evaluator._evaluate_skills(self.job)
        self.assertGreater(skill_score, 50)  # Should match python and django
    
    def test_calculate_relevance_score(self):
        scores = {
            'location_match': True,
            'remote_match': True,
            'salary_match': True,
            'skill_match': 80
        }
        score = self.evaluator._calculate_relevance_score(scores)
        self.assertGreater(score, 50)