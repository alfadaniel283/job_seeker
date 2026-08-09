from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('add-jobs/', views.add_jobs, name='add_jobs'),
    path('bulk-add-jobs/', views.bulk_add_jobs, name='bulk_add_jobs'),
    path('preferences/', views.preferences, name='preferences'),
    
    # API endpoints
    path('api/evaluate-jobs/', views.evaluate_jobs, name='evaluate_jobs'),
    path('api/ai-analyze/<int:job_id>/', views.ai_analyze_job, name='ai_analyze_job'),
    path('api/regenerate-analysis/<int:job_id>/', views.regenerate_analysis, name='regenerate_analysis'),
    path('api/process-urls/', views.process_urls_api, name='process_urls_api'),
    path('api/extract-job-details/<int:job_id>/', views.extract_job_details, name='extract_job_details'),
    
    # Dashboard and health
    path('dashboard/', views.dashboard, name='dashboard'),
    path('health/', views.health_check, name='health_check'),
]