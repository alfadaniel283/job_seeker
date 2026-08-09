from django import forms
from .models import JobSource, UserJobPreferences, Job

class JobSourceForm(forms.ModelForm):
    class Meta:
        model = JobSource
        fields = ['url', 'source_type', 'name']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.example.com/jobs'}),
            'source_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
        }

class BulkJobSourceForm(forms.Form):
    """Form for adding multiple job sources at once"""
    source_type = forms.ChoiceField(
        choices=[('OTHER', 'Other'), ('LINKEDIN', 'LinkedIn'), ('INDEED', 'Indeed'), 
                 ('GLASSDOOR', 'Glassdoor'), ('MONSTER', 'Monster'), ('FLEXJOBS', 'FlexJobs')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    urls = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'https://www.example.com/jobs\nhttps://www.linkedin.com/jobs/...\nhttps://www.indeed.com/jobs?...',
            'style': 'font-family: monospace;'
        }),
        help_text='Enter one URL per line. All will be processed with AI evaluation.'
    )
    batch_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: Batch name (e.g., "Tech Jobs Batch 1")'
        }),
        help_text='Optional name for this batch of job sources'
    )
    skip_existing = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Skip URLs that already exist in the system'
    )

class JobPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserJobPreferences
        fields = [
            'preferred_locations', 'remote_only', 'hybrid_allowed',
            'min_salary', 'max_salary', 'include_keywords', 'exclude_keywords'
            # 'preferred_job_types' and 'preferred_experience_levels' removed
        ]
        widgets = {
            'preferred_locations': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New York, London, ...'}),
            'remote_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hybrid_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '50000'}),
            'max_salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '100000'}),
            'include_keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'python, django, ...'}),
            'exclude_keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'senior, manager, ...'}),
        }


class JobSearchForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search jobs...'}))
    location = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}))
    is_remote = forms.ChoiceField(required=False, choices=[('', 'All'), ('true', 'Remote Only'), ('false', 'On-site')], widget=forms.Select(attrs={'class': 'form-select'}))
    min_salary = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Salary'}))
    sort_by = forms.ChoiceField(required=False, choices=[('date', 'Date'), ('relevance', 'Relevance'), ('salary', 'Salary')], widget=forms.Select(attrs={'class': 'form-select'}))