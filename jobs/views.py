from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import models
from jobs.models import Job, JobSource, JobEvaluation, UserJobPreferences
from jobs.forms import JobSourceForm, JobPreferencesForm, JobSearchForm, BulkJobSourceForm
from jobs.services.job_processor import JobProcessor
from jobs.services.job_evaluator import JobEvaluator
from jobs.services.ai_service import AIService
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def index(request):
    """Home page with AI-powered recommendations"""
    recent_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:10]
    
    # If user is authenticated, get AI recommendations
    recommended_jobs = []
    if request.user.is_authenticated:
        try:
            evaluations = JobEvaluation.objects.filter(
                user=request.user,
                is_recommended=True
            ).select_related('job').order_by('-relevance_score')[:5]
            recommended_jobs = [e.job for e in evaluations]
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
    
    context = {
        'recent_jobs': recent_jobs,
        'recommended_jobs': recommended_jobs,
        'total_jobs': Job.objects.filter(is_active=True).count(),
    }
    return render(request, 'jobs/index.html', context)

@login_required
def job_list(request):
    """List jobs with AI-powered filtering and sorting"""
    form = JobSearchForm(request.GET)
    jobs = Job.objects.filter(is_active=True)
    
    if form.is_valid():
        # Apply search filter
        if form.cleaned_data.get('search'):
            search = form.cleaned_data['search']
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(company__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Apply location filter
        if form.cleaned_data.get('location'):
            jobs = jobs.filter(location__icontains=form.cleaned_data['location'])
        
        # Apply remote filter
        if form.cleaned_data.get('is_remote'):
            is_remote = form.cleaned_data['is_remote']
            if is_remote == 'true':
                jobs = jobs.filter(is_remote=True)
            elif is_remote == 'false':
                jobs = jobs.filter(is_remote=False)
        
        # Apply sorting
        if form.cleaned_data.get('sort_by'):
            sort_by = form.cleaned_data['sort_by']
            if sort_by == 'relevance':
                jobs = jobs.annotate(
                    avg_score=Avg('evaluations__relevance_score')
                ).order_by('-avg_score')
            elif sort_by == 'date':
                jobs = jobs.order_by('-posted_date')
            elif sort_by == 'salary':
                jobs = jobs.order_by('-salary')
    
    # Pagination
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
    }
    return render(request, 'jobs/job_list.html', context)

@login_required
def job_detail(request, job_id):
    """View job details with AI-powered analysis"""
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    # Get or create evaluation for the user
    evaluator = JobEvaluator(request.user)
    evaluation = JobEvaluation.objects.filter(job=job, user=request.user).first()
    
    if not evaluation:
        try:
            scores = evaluator.evaluate_job(job, use_ai=True)
            evaluation = evaluator.save_evaluation(job, scores)
        except Exception as e:
            logger.error(f"Error evaluating job {job_id}: {e}")
            # Create a default evaluation
            evaluation = JobEvaluation.objects.create(
                job=job,
                user=request.user,
                relevance_score=50,
                is_recommended=False,
                evaluation_notes="Evaluation failed. Please try again."
            )
    
    # Get AI-powered insights
    ai_service = AIService()
    ai_insights = {}
    try:
        job_data = {
            'title': job.title,
            'company': job.company,
            'description': job.description,
            'location': job.location,
            'salary': job.salary,
            'is_remote': job.is_remote,
            'is_hybrid': job.is_hybrid
        }
        user_profile = {}
        if hasattr(request.user, 'job_preferences'):
            prefs = request.user.job_preferences
            user_profile = {
                'skills': prefs.include_keywords,
                'preferred_locations': prefs.preferred_locations,
                'remote_only': prefs.remote_only,
                'hybrid_allowed': prefs.hybrid_allowed
            }
        ai_insights = ai_service.analyze_job_match(job_data, user_profile)
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
    
    context = {
        'job': job,
        'evaluation': evaluation,
        'ai_insights': ai_insights,
    }
    return render(request, 'jobs/job_detail.html', context)

@login_required
def add_jobs(request):
    """Add job sources with AI-powered processing"""
    if request.method == 'POST':
        form = JobSourceForm(request.POST)
        if form.is_valid():
            try:
                source = form.save()
                processor = JobProcessor(use_ai=True)
                jobs_created = processor.process_source(source.id, request.user)
                
                if jobs_created:
                    messages.success(
                        request, 
                        f'Successfully added {len(jobs_created)} jobs from {source.name} with AI analysis'
                    )
                else:
                    messages.warning(request, 'No new jobs found or there was an error processing')
                
                return redirect('jobs:job_list')
            except Exception as e:
                logger.error(f"Error adding jobs: {e}")
                messages.error(request, f'Error adding jobs: {str(e)}')
    else:
        form = JobSourceForm()
    
    return render(request, 'jobs/add_jobs.html', {'form': form})

@login_required
def preferences(request):
    """User preferences with AI recommendations"""
    preferences, created = UserJobPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = JobPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            
            # Trigger AI-powered job re-evaluation
            try:
                processor = JobProcessor(use_ai=True)
                active_sources = JobSource.objects.filter(is_active=True)
                total_jobs = 0
                for source in active_sources:
                    jobs = processor.process_source(source.id, request.user)
                    total_jobs += len(jobs)
                messages.success(
                    request,
                    f'Preferences updated successfully! {total_jobs} jobs re-evaluated with AI.'
                )
            except Exception as e:
                logger.error(f"Error re-evaluating jobs: {e}")
                messages.warning(
                    request,
                    f'Preferences updated but AI re-evaluation failed: {str(e)}'
                )
            
            return redirect('jobs:job_list')
    else:
        form = JobPreferencesForm(instance=preferences)
    
    context = {
        'form': form,
    }
    return render(request, 'jobs/preferences.html', context)

@login_required
@require_POST
def evaluate_jobs(request):
    """API endpoint for AI-powered job evaluation"""
    job_ids = request.POST.getlist('job_ids')
    use_ai = request.POST.get('use_ai', 'true') == 'true'
    
    if not job_ids:
        return JsonResponse({'error': 'No job IDs provided'}, status=400)
    
    evaluator = JobEvaluator(request.user)
    results = []
    
    for job_id in job_ids:
        try:
            job = Job.objects.get(id=job_id, is_active=True)
            scores = evaluator.evaluate_job(job, use_ai=use_ai)
            evaluator.save_evaluation(job, scores)
            
            results.append({
                'job_id': job.id,
                'title': job.title,
                'company': job.company,
                'score': scores['relevance_score'],
                'is_recommended': scores['is_recommended'],
                'reasons': scores.get('recommendation_reasons', []),
                'concerns': scores.get('concerns', [])
            })
        except Job.DoesNotExist:
            continue
        except Exception as e:
            logger.error(f"Error evaluating job {job_id}: {e}")
            results.append({
                'job_id': job_id,
                'error': str(e)
            })
    
    return JsonResponse({
        'results': results,
        'total_evaluated': len(results),
        'ai_enabled': use_ai
    })

@login_required
def ai_analyze_job(request, job_id):
    """Get AI-powered analysis for a specific job"""
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    ai_service = AIService()
    
    job_data = {
        'title': job.title,
        'company': job.company,
        'location': job.location,
        'description': job.description,
        'salary': job.salary,
        'is_remote': job.is_remote,
        'is_hybrid': job.is_hybrid
    }
    
    user_profile = {}
    if hasattr(request.user, 'job_preferences'):
        prefs = request.user.job_preferences
        user_profile = {
            'skills': prefs.include_keywords,
            'preferred_locations': prefs.preferred_locations,
            'remote_only': prefs.remote_only,
            'hybrid_allowed': prefs.hybrid_allowed
        }
    
    try:
        analysis = ai_service.analyze_job_match(job_data, user_profile)
        extracted = ai_service.extract_job_details(job.description)
        
        return JsonResponse({
            'success': True,
            'analysis': analysis,
            'extracted_details': extracted
        })
    except Exception as e:
        logger.error(f"Error analyzing job {job_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def regenerate_analysis(request, job_id):
    """Regenerate AI analysis for a job"""
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    try:
        evaluator = JobEvaluator(request.user)
        scores = evaluator.evaluate_job(job, use_ai=True)
        evaluator.save_evaluation(job, scores)
        
        return JsonResponse({
            'success': True,
            'score': scores['relevance_score'],
            'is_recommended': scores['is_recommended']
        })
    except Exception as e:
        logger.error(f"Error regenerating analysis for job {job_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def dashboard(request):
    """Dashboard view with statistics and analytics"""
    # Get job statistics
    total_jobs = Job.objects.filter(is_active=True).count()
    remote_jobs = Job.objects.filter(is_active=True, is_remote=True).count()
    
    # Get user's evaluation stats
    evaluations = JobEvaluation.objects.filter(user=request.user)
    evaluated_count = evaluations.count()
    recommended_count = evaluations.filter(is_recommended=True).count()
    
    # Get top companies
    top_companies = Job.objects.filter(is_active=True).values('company').annotate(
        count=models.Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'total_jobs': total_jobs,
        'remote_jobs': remote_jobs,
        'evaluated_count': evaluated_count,
        'recommended_count': recommended_count,
        'top_companies': top_companies,
    }
    return render(request, 'jobs/dashboard.html', context)

def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'database': 'connected',
        'jobs_count': Job.objects.filter(is_active=True).count(),
    })


@login_required
def bulk_add_jobs(request):
    """Add multiple job sources at once"""
    if request.method == 'POST':
        form = BulkJobSourceForm(request.POST)
        if form.is_valid():
            urls = form.cleaned_data['urls'].strip().split('\n')
            source_type = form.cleaned_data['source_type']
            batch_name = form.cleaned_data.get('batch_name', f'Batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            # Filter out empty lines
            urls = [url.strip() for url in urls if url.strip()]
            
            if not urls:
                messages.warning(request, 'No valid URLs provided')
                return redirect('jobs:bulk_add_jobs')
            
            logger.info(f"Processing {len(urls)} URLs with Groq AI")
            print(f" Processing {len(urls)} URLs with Groq AI...")
            
            processor = JobProcessor(use_ai=True)
            total_jobs = 0
            created_sources = []
            failed_urls = []
            skipped_urls = []  # Track skipped duplicates
            errors = []
            
            # First, check which URLs already exist
            existing_urls = set(JobSource.objects.filter(
                url__in=urls
            ).values_list('url', flat=True))
            
            for i, url in enumerate(urls, 1):
                try:
                    # Skip if URL already exists
                    if url in existing_urls:
                        print(f" Skipping duplicate URL {i}/{len(urls)}: {url[:50]}... (already exists)")
                        skipped_urls.append(url)
                        continue
                    
                    print(f" Processing URL {i}/{len(urls)}: {url[:50]}...")
                    
                    # Create job source
                    source = JobSource.objects.create(
                        url=url,
                        source_type=source_type,
                        name=f"{batch_name} - {url[:50]}",
                        is_active=True
                    )
                    created_sources.append(source)
                    
                    # Process jobs
                    try:
                        jobs = processor.process_source(source.id, request.user)
                        total_jobs += len(jobs)
                        print(f" Added {len(jobs)} jobs from {url[:50]}")
                    except Exception as e:
                        error_msg = f"Error processing {url[:50]}: {str(e)}"
                        logger.error(error_msg)
                        logger.error(traceback.format_exc())
                        errors.append(error_msg)
                        failed_urls.append(url)
                    
                except IntegrityError:
                    # This shouldn't happen now that we check above, but just in case
                    print(f" Skipping duplicate URL {url[:50]}... (integrity error)")
                    skipped_urls.append(url)
                except Exception as e:
                    error_msg = f"Error creating source for {url[:50]}: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    errors.append(error_msg)
                    failed_urls.append(url)
            
            # Summary
            print("\n" + "="*50)
            print(" BULK PROCESSING SUMMARY")
            print("="*50)
            print(f"Total URLs: {len(urls)}")
            print(f"New Sources Created: {len(created_sources)}")
            print(f"Jobs Added: {total_jobs}")
            print(f"Skipped (duplicates): {len(skipped_urls)}")
            print(f"Failed URLs: {len(failed_urls)}")
            
            if skipped_urls:
                print("\n SKIPPED (already exist):")
                for url in skipped_urls[:5]:
                    print(f"  - {url[:60]}...")
                if len(skipped_urls) > 5:
                    print(f"  ... and {len(skipped_urls) - 5} more")
            
            if errors:
                print("\n ERRORS:")
                for error in errors[:5]:
                    print(f"  - {error}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more errors")
            
            # Show message to user
            if total_jobs > 0:
                messages.success(
                    request, 
                    f' Added {total_jobs} jobs from {len(created_sources)} new sources! '
                    f'Skipped {len(skipped_urls)} duplicates.'
                )
            elif len(skipped_urls) > 0 and total_jobs == 0:
                messages.info(
                    request,
                    f'All {len(skipped_urls)} URLs already exist. No new jobs added.'
                )
            else:
                messages.warning(
                    request, 
                    f' No new jobs found. Failed: {len(failed_urls)} URLs. Check logs for details.'
                )
            
            if failed_urls:
                messages.warning(
                    request, 
                    f'Failed to process {len(failed_urls)} URLs. Check logs for details.'
                )
            
            return redirect('jobs:job_list')
    else:
        form = BulkJobSourceForm()
    
    return render(request, 'jobs/bulk_add_jobs.html', {'form': form})

@login_required
@require_POST
def process_urls_api(request):
    """API endpoint for bulk URL processing"""
    urls = request.POST.getlist('urls')
    source_type = request.POST.get('source_type', 'OTHER')
    
    if not urls:
        return JsonResponse({'error': 'No URLs provided'}, status=400)
    
    processor = JobProcessor(use_ai=True)
    results = []
    total_jobs = 0
    
    for url in urls:
        try:
            source = JobSource.objects.create(
                url=url,
                source_type=source_type,
                name=f"API - {url[:50]}",
                is_active=True
            )
            jobs = processor.process_source(source.id, request.user)
            total_jobs += len(jobs)
            results.append({
                'url': url,
                'status': 'success',
                'jobs_found': len(jobs)
            })
        except Exception as e:
            results.append({
                'url': url,
                'status': 'error',
                'error': str(e)
            })
    
    return JsonResponse({
        'total_jobs': total_jobs,
        'results': results
    })