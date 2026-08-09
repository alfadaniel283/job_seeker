from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import Job, JobSource, JobEvaluation, UserJobPreferences, JobProcessingLog

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'company', 'location', 'posted_date', 
        'is_active', 'is_remote', 'job_type', 'experience_level',
        'has_structured_data_badge', 'requirements_count'
    ]
    list_filter = [
        'is_active', 'is_remote', 'is_hybrid', 'job_type', 
        'experience_level', 'source', 'created_at'
    ]
    search_fields = ['title', 'company', 'description', 'location']
    readonly_fields = [
        'content_hash', 'created_at', 'updated_at',
        'requirements', 'responsibilities', 'benefits', 
        'qualifications', 'skills', 'keywords'
    ]
    ordering = ['-posted_date']
    actions = ['extract_with_ai_action']
    
    fieldsets = (
        ('Core Information', {
            'fields': ('title', 'company', 'description', 'location', 'salary')
        }),
        ('Job Details', {
            'fields': ('job_type', 'experience_level', 'is_remote', 'is_hybrid', 'work_arrangement')
        }),
        ('AI-Extracted Structured Data', {
            'fields': (
                'requirements', 'qualifications', 'responsibilities', 
                'benefits', 'skills', 'keywords',
                'experience_required', 'education_required'
            ),
            'classes': ('collapse',),
            'description': 'Data extracted by AI from job description'
        }),
        ('Source Information', {
            'fields': ('source', 'source_url', 'external_id')
        }),
        ('Dates & Status', {
            'fields': ('posted_date', 'created_at', 'updated_at', 'is_active', 'content_hash')
        }),
    )
    
    def has_structured_data_badge(self, obj):
        if obj.has_structured_data():
            return mark_safe('<span style="color: green; font-weight: bold;">✅ AI Enriched</span>')
        return mark_safe('<span style="color: orange;">⏳ Pending</span>')
    has_structured_data_badge.short_description = 'AI Status'
    
    def requirements_count(self, obj):
        return obj.get_requirements_count()
    requirements_count.short_description = 'Requirements'
    
    def extract_with_ai_action(self, request, queryset):
        from jobs.services.ai_service import AIService
        success_count = 0
        error_count = 0
        
        ai_service = AIService()
        
        for job in queryset:
            try:
                if job.description and len(job.description) > 100:
                    extracted = ai_service.extract_job_details(job.description)
                    if extracted:
                        updates = {}
                        if extracted.get('requirements'):
                            updates['requirements'] = extracted['requirements']
                        if extracted.get('responsibilities'):
                            updates['responsibilities'] = extracted['responsibilities']
                        if extracted.get('benefits'):
                            updates['benefits'] = extracted['benefits']
                        if extracted.get('qualifications'):
                            updates['qualifications'] = extracted['qualifications']
                        if extracted.get('experience_required'):
                            updates['experience_required'] = extracted['experience_required']
                        if extracted.get('education_required'):
                            updates['education_required'] = extracted['education_required']
                        if extracted.get('skills'):
                            updates['skills'] = extracted['skills']
                        if extracted.get('keywords'):
                            updates['keywords'] = extracted['keywords']
                        
                        if updates:
                            Job.objects.filter(id=job.id).update(**updates)
                            success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(request, f"Error on {job.title}: {e}", level='ERROR')
        
        self.message_user(
            request, 
            f"Successfully extracted data for {success_count} jobs. {error_count} failed."
        )
    extract_with_ai_action.short_description = 'Extract structured data with AI'

@admin.register(JobSource)
class JobSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'url_short', 'is_active', 'created_at']
    list_filter = ['source_type', 'is_active']
    search_fields = ['name', 'url']
    ordering = ['-created_at']
    
    def url_short(self, obj):
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'

@admin.register(JobEvaluation)
class JobEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        'job', 'user', 'relevance_score', 'ai_match_score', 
        'is_recommended', 'culture_fit', 'created_at'
    ]
    list_filter = ['is_recommended', 'location_match', 'remote_match', 'salary_match']
    search_fields = ['job__title', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-relevance_score']
    
    fieldsets = (
        ('Job & User', {
            'fields': ('job', 'user')
        }),
        ('Match Scores', {
            'fields': (
                'relevance_score', 'ai_match_score', 'culture_fit',
                'skill_match', 'location_match', 'remote_match', 
                'salary_match', 'experience_match', 'job_type_match'
            )
        }),
        ('AI Analysis', {
            'fields': ('ai_reasons', 'ai_concerns'),
            'classes': ('collapse',),
        }),
        ('Overall', {
            'fields': ('is_recommended', 'evaluation_notes')
        }),
    )

@admin.register(UserJobPreferences)
class UserJobPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'remote_only', 'hybrid_allowed', 'has_preferences_badge']
    search_fields = ['user__username', 'user__email']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Location Preferences', {
            'fields': ('preferred_locations', 'remote_only', 'hybrid_allowed')
        }),
        ('Job Preferences', {
            'fields': ('preferred_job_types', 'preferred_experience_levels')
        }),
        ('Salary Preferences', {
            'fields': ('min_salary', 'max_salary')
        }),
        ('Keyword Preferences', {
            'fields': ('include_keywords', 'exclude_keywords', 'preferred_skills')
        }),
    )
    
    def has_preferences_badge(self, obj):
        """Display if user has set preferences"""
        if obj.has_preferences():
            return mark_safe('<span style="color: green; font-weight: bold;">✅ Configured</span>')
        return mark_safe('<span style="color: orange; font-weight: bold;">⚠️ Not Set</span>')
    has_preferences_badge.short_description = 'Status'

@admin.register(JobProcessingLog)
class JobProcessingLogAdmin(admin.ModelAdmin):
    list_display = [
        'source', 'status', 'total_jobs_saved', 'total_jobs_found',
        'ai_used', 'duration_seconds_formatted', 'started_at'
    ]
    list_filter = ['status', 'ai_used', 'ai_success']
    search_fields = ['source__name', 'error_message']
    readonly_fields = [
        'source', 'status', 'total_jobs_found', 'total_jobs_saved',
        'total_jobs_duplicates', 'total_jobs_failed',
        'ai_used', 'ai_success', 'ai_extracted_fields',
        'started_at', 'completed_at', 'duration_seconds',
        'error_message', 'error_traceback', 'triggered_by'
    ]
    ordering = ['-started_at']
    
    def duration_seconds_formatted(self, obj):
        if obj.duration_seconds:
            if obj.duration_seconds < 60:
                return f"{obj.duration_seconds:.1f}s"
            elif obj.duration_seconds < 3600:
                minutes = obj.duration_seconds // 60
                seconds = obj.duration_seconds % 60
                return f"{int(minutes)}m {int(seconds)}s"
            else:
                hours = obj.duration_seconds // 3600
                minutes = (obj.duration_seconds % 3600) // 60
                return f"{int(hours)}h {int(minutes)}m"
        return "N/A"
    duration_seconds_formatted.short_description = 'Duration'