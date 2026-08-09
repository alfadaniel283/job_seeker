from django.test import TestCase
from django.contrib.auth.models import User
from jobs.models import Job, JobSource, UserJobPreferences, JobEvaluation
from datetime import datetime

class JobModelTest(TestCase):
    def setUp(self):
        self.source = JobSource.objects.create(
            url='https://example.com',
            source_type='OTHER',
            name='Test Source'
        )
        self.job = Job.objects.create(
            title='Test Job',
            description='Test Description',
            company='Test Company',
            location='Remote',
            source=self.source,
            source_url='https://example.com/job',
            posted_date=datetime.now(),
            content_hash='testhash123'
        )
    
    def test_job_creation(self):
        self.assertEqual(self.job.title, 'Test Job')
        self.assertEqual(self.job.company, 'Test Company')
        self.assertTrue(self.job.is_active)
    
    def test_job_str_method(self):
        self.assertEqual(str(self.job), 'Test Job at Test Company')
    
    def test_get_salary_display(self):
        self.assertEqual(self.job.get_salary_display(), 'Not specified')
        self.job.salary = '100k'
        self.job.save()
        self.assertEqual(self.job.get_salary_display(), '100k')

class UserPreferencesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.preferences = UserJobPreferences.objects.create(
            user=self.user,
            remote_only=True,
            include_keywords=['python', 'django']
        )
    
    def test_preferences_creation(self):
        self.assertTrue(self.preferences.remote_only)
        self.assertEqual(self.preferences.include_keywords, ['python', 'django'])
    
    def test_preferences_str_method(self):
        self.assertEqual(str(self.preferences), 'Preferences for testuser')