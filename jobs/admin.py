from django.contrib import admin
from .models import Job, JobSource, JobEvaluation, UserJobPreferences

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'posted_date', 'is_active', 'is_remote']
    list_filter = ['is_active', 'is_remote', 'job_type', 'experience_level']
    search_fields = ['title', 'company', 'description']
    readonly_fields = ['content_hash', 'created_at', 'updated_at']
    ordering = ['-posted_date']

@admin.register(JobSource)
class JobSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'url', 'is_active', 'created_at']
    list_filter = ['source_type', 'is_active']
    search_fields = ['name', 'url']
    ordering = ['-created_at']

@admin.register(JobEvaluation)
class JobEvaluationAdmin(admin.ModelAdmin):
    list_display = ['job', 'user', 'relevance_score', 'is_recommended', 'created_at']
    list_filter = ['is_recommended']
    search_fields = ['job__title', 'user__username']
    ordering = ['-relevance_score']

@admin.register(UserJobPreferences)
class UserJobPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'remote_only', 'hybrid_allowed', 'created_at']
    search_fields = ['user__username']