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
        ('JOBRIGHT', 'Jobright'),
        ('GREENHOUSE', 'Greenhouse'),
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
    """Model to store job listings with AI-extracted structured data"""
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
    
    WORK_ARRANGEMENTS = [
        ('REMOTE', 'Remote'),
        ('HYBRID', 'Hybrid'),
        ('ON_SITE', 'On-Site'),
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
    work_arrangement = models.CharField(max_length=50, choices=WORK_ARRANGEMENTS, blank=True, null=True)
    is_remote = models.BooleanField(default=False)
    is_hybrid = models.BooleanField(default=False)
    
    # ============================================
    # AI-EXTRACTED STRUCTURED DATA
    # ============================================
    
    # Requirements and qualifications
    requirements = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of job requirements (skills, experience, etc.)"
    )
    qualifications = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of preferred qualifications"
    )
    responsibilities = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of job responsibilities/duties"
    )
    benefits = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of benefits offered"
    )
    
    # Experience and education
    experience_required = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Years of experience required (e.g., '3+ years')"
    )
    education_required = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Education required (e.g., 'Bachelor's degree')"
    )
    
    # Additional AI-extracted fields
    skills = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of skills extracted from the job"
    )
    keywords = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of keywords/tags extracted from the job"
    )
    
    # Source information
    source_url = models.URLField(max_length=2000)
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
            models.Index(fields=['job_type']),
            models.Index(fields=['experience_level']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    def get_salary_display(self):
        """Return formatted salary or 'Not specified'"""
        return self.salary if self.salary else 'Not specified'
    
    def get_requirements_count(self):
        """Get count of requirements"""
        return len(self.requirements) if self.requirements else 0
    
    def get_responsibilities_count(self):
        """Get count of responsibilities"""
        return len(self.responsibilities) if self.responsibilities else 0
    
    def get_benefits_count(self):
        """Get count of benefits"""
        return len(self.benefits) if self.benefits else 0
    
    def get_skills_count(self):
        """Get count of skills"""
        return len(self.skills) if self.skills else 0
    
    def has_structured_data(self):
        """Check if job has AI-extracted structured data"""
        return bool(
            self.requirements or 
            self.responsibilities or 
            self.benefits or 
            self.qualifications or
            self.skills
        )
    
    def get_structured_data_summary(self):
        """Get summary of structured data"""
        return {
            'requirements': len(self.requirements) if self.requirements else 0,
            'qualifications': len(self.qualifications) if self.qualifications else 0,
            'responsibilities': len(self.responsibilities) if self.responsibilities else 0,
            'benefits': len(self.benefits) if self.benefits else 0,
            'skills': len(self.skills) if self.skills else 0,
            'experience_required': self.experience_required,
            'education_required': self.education_required,
        }


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
    
    # Skill preferences
    preferred_skills = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of preferred skills"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def has_preferences(self):
        """Check if user has set any preferences"""
        return any([
            self.preferred_locations,
            self.remote_only,
            self.hybrid_allowed,
            self.preferred_job_types,
            self.preferred_experience_levels,
            self.include_keywords,
            self.exclude_keywords,
            self.preferred_skills,
        ])


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
    
    # AI-specific evaluation
    ai_match_score = models.FloatField(
        default=0.0, 
        help_text="AI-generated match score"
    )
    culture_fit = models.FloatField(
        default=0.0, 
        help_text="Culture fit score (0-100)"
    )
    ai_reasons = models.JSONField(
        default=list, 
        blank=True,
        help_text="Reasons provided by AI for the match"
    )
    ai_concerns = models.JSONField(
        default=list, 
        blank=True,
        help_text="Concerns raised by AI"
    )
    
    # Overall evaluation
    is_recommended = models.BooleanField(default=False)
    evaluation_notes = models.TextField(blank=True)
    
    # Metadata
    evaluated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['job', 'user']
        ordering = ['-relevance_score']
        indexes = [
            models.Index(fields=['job', 'user']),
            models.Index(fields=['-relevance_score']),
            models.Index(fields=['is_recommended']),
        ]
    
    def __str__(self):
        return f"Evaluation for {self.job.title} - {self.relevance_score}%"
    
    def get_match_level(self):
        """Get match level based on score"""
        if self.relevance_score >= 80:
            return 'Excellent'
        elif self.relevance_score >= 60:
            return 'Good'
        elif self.relevance_score >= 40:
            return 'Average'
        else:
            return 'Low'
    
    def is_high_match(self):
        """Check if match is high (>=70%)"""
        return self.relevance_score >= 70


class JobProcessingLog(models.Model):
    """Model to track job processing activities"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'),
    ]
    
    source = models.ForeignKey(JobSource, on_delete=models.CASCADE, related_name='processing_logs')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    
    # Job counts
    total_jobs_found = models.IntegerField(default=0)
    total_jobs_saved = models.IntegerField(default=0)
    total_jobs_duplicates = models.IntegerField(default=0)
    total_jobs_failed = models.IntegerField(default=0)
    
    # AI processing
    ai_used = models.BooleanField(default=False)
    ai_success = models.BooleanField(default=False)
    ai_extracted_fields = models.JSONField(default=list, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(default=0.0)
    
    # Error information
    error_message = models.TextField(blank=True, null=True)
    error_traceback = models.TextField(blank=True, null=True)
    
    # User who initiated processing
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-started_at']),
        ]
    
    def __str__(self):
        return f"Processing {self.source.name} - {self.status} ({self.created_at})"
    
    def mark_completed(self, jobs_saved=0, jobs_found=0, duplicates=0):
        """Mark processing as completed with stats"""
        self.status = 'COMPLETED'
        self.total_jobs_saved = jobs_saved
        self.total_jobs_found = jobs_found
        self.total_jobs_duplicates = duplicates
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.save()
    
    def mark_failed(self, error_message, error_traceback=None):
        """Mark processing as failed with error details"""
        self.status = 'FAILED'
        self.error_message = error_message
        self.error_traceback = error_traceback
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.save()