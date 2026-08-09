from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class JobSource(models.Model):
    """Model to store job source URLs"""
    SOURCE_TYPES = [
        ('LINKEDIN', 'LinkedIn'),
        ('INDEED', 'Indeed'),
        ('GLASSDOOR', 'Glassdoor'),
        ('FLEXJOBS', 'FlexJobs'),  
        ('PROGRESSIVE', 'Progressive'),
        ('MONSTER', 'Monster'),
        ('OTHER', 'Other'),
    ]
    
    url = models.URLField(max_length=2000, unique=True)
    source_type = models.CharField(max_length=70, choices=SOURCE_TYPES)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"

class Job(models.Model):
    """Model to store job listings"""
    JOB_TYPES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('FREELANCE', 'Freelance'),
        ('INTERNSHIP', 'Internship'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('ENTRY', 'Entry Level'),
        ('MID', 'Mid Level'),
        ('SENIOR', 'Senior Level'),
        ('EXECUTIVE', 'Executive'),
    ]
    
    # Core job information
    title = models.CharField(max_length=255)
    description = models.TextField()
    company = models.CharField(max_length=255, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    salary = models.CharField(max_length=255, blank=True, null=True)
    
    # Job details
    job_type = models.CharField(max_length=100, choices=JOB_TYPES, default='FULL_TIME')
    experience_level = models.CharField(max_length=100, choices=EXPERIENCE_LEVELS, default='MID')
    is_remote = models.BooleanField(default=False)
    is_hybrid = models.BooleanField(default=False)
    
    # Source information
    source_url = models.URLField()
    source = models.ForeignKey(JobSource, on_delete=models.CASCADE, related_name='jobs')
    external_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Date fields
    posted_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Hash for duplicate detection
    content_hash = models.CharField(max_length=100, unique=True, db_index=True)
    
    class Meta:
        ordering = ['-posted_date']
        indexes = [
            models.Index(fields=['company', 'title']),
            models.Index(fields=['location', 'is_remote']),
            models.Index(fields=['-posted_date']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    def get_salary_display(self):
        return self.salary if self.salary else 'Not specified'

class UserJobPreferences(models.Model):
    """Model to store user preferences for job filtering"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='job_preferences')
    
    # Location preferences
    preferred_locations = models.JSONField(default=list, help_text="List of preferred locations")
    remote_only = models.BooleanField(default=False)
    hybrid_allowed = models.BooleanField(default=True)
    
    # Job type preferences
    preferred_job_types = models.JSONField(default=list, help_text="List of preferred job types")
    preferred_experience_levels = models.JSONField(default=list, help_text="List of preferred experience levels")
    
    # Salary preferences
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Keywords for filtering
    include_keywords = models.JSONField(default=list, help_text="Keywords that must be in job description")
    exclude_keywords = models.JSONField(default=list, help_text="Keywords that must not be in job description")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"

class JobEvaluation(models.Model):
    """Model to store evaluation results for jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='evaluations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_evaluations')
    
    # Evaluation criteria
    relevance_score = models.FloatField(default=0.0, help_text="0-100 score")
    location_match = models.BooleanField(default=False)
    remote_match = models.BooleanField(default=False)
    salary_match = models.BooleanField(default=False)
    skill_match = models.FloatField(default=0.0, help_text="Percentage of skills matched")
    experience_match = models.BooleanField(default=False)
    job_type_match = models.BooleanField(default=False)
    
    # Overall evaluation
    is_recommended = models.BooleanField(default=False)
    evaluation_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['job', 'user']
        ordering = ['-relevance_score']
    
    def __str__(self):
        return f"Evaluation for {self.job.title} - {self.relevance_score}%"