import logging
import hashlib
import traceback
from typing import List, Dict, Optional
from django.db import transaction, IntegrityError
from django.utils import timezone
from jobs.models import Job, JobSource
from jobs.services.job_fetcher import JobFetcherFactory
from jobs.services.job_evaluator import JobEvaluator
from jobs.services.ai_service import AIService

logger = logging.getLogger(__name__)

class JobProcessor:
    """Enhanced job processor with AI capabilities"""
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.ai_service = AIService() if use_ai else None
        self.fetcher_factory = JobFetcherFactory()
    
    def process_source(self, source_id: int, user=None):
        """Process a single job source"""
        try:
            source = JobSource.objects.get(id=source_id, is_active=True)
            logger.info(f"Processing source: {source.name} ({source.source_type})")
            
            fetcher = self.fetcher_factory.get_fetcher(source.source_type)
            
            html_content = fetcher.fetch_page(source.url)
            if not html_content:
                logger.error(f"Failed to fetch content from {source.url}")
                return []
            
            job_data_list = fetcher.parse_job_data(html_content, source.url)
            logger.info(f"Found {len(job_data_list)} jobs from {source.name}")
            
            if not job_data_list:
                logger.warning(f"No jobs found from {source.name}")
                return []
            
            jobs_created = self._save_jobs(job_data_list, source)
            logger.info(f"Saved {len(jobs_created)} new jobs from {source.name}")
            
            # Evaluate jobs if user is provided
            if user and jobs_created:
                try:
                    evaluator = JobEvaluator(user)
                    for job in jobs_created:
                        scores = evaluator.evaluate_job(job, use_ai=self.use_ai)
                        evaluator.save_evaluation(job, scores)
                    logger.info(f"Evaluated {len(jobs_created)} jobs for user {user.username}")
                except Exception as e:
                    logger.error(f"Job evaluation failed: {e}")
            
            return jobs_created
            
        except JobSource.DoesNotExist:
            logger.error(f"Job source {source_id} not found")
            return []
        except IntegrityError as e:
            if 'duplicate key value violates unique constraint' in str(e):
                logger.warning(f"Source already exists (duplicate URL): {e}")
                return []
            logger.error(f"Database integrity error: {e}")
            return []
        except Exception as e:
            error_msg = f"Error processing source {source_id}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    @transaction.atomic
    def _save_jobs(self, job_data_list: List[Dict], source: JobSource) -> List[Job]:
        """Save jobs to database"""
        jobs_created = []
        
        for job_data in job_data_list:
            try:
                if not job_data.get('content_hash'):
                    content = f"{job_data.get('title', '')}{job_data.get('company', '')}{job_data.get('description', '')[:500]}"
                    job_data['content_hash'] = hashlib.sha256(content.encode()).hexdigest()
                
                if Job.objects.filter(content_hash=job_data['content_hash']).exists():
                    logger.debug(f"Duplicate job found: {job_data.get('title', '')}")
                    continue
                
                source_url = job_data.get('source_url', '')
                if len(source_url) > 2000:
                    source_url = source_url[:1997] + '...'
                
                job = Job.objects.create(
                    title=job_data['title'][:255] if job_data.get('title') else 'Untitled',
                    description=job_data.get('description', 'No description available'),
                    company=job_data.get('company', 'Unknown Company')[:255],
                    location=job_data.get('location', 'Remote')[:255],
                    salary=job_data.get('salary'),
                    is_remote=job_data.get('is_remote', False),
                    is_hybrid=job_data.get('is_hybrid', False),
                    source=source,
                    source_url=source_url,
                    external_id=job_data.get('external_id', '')[:100],
                    posted_date=job_data.get('posted_date', timezone.now()),
                    content_hash=job_data['content_hash'],
                )
                jobs_created.append(job)
                logger.debug(f"Created job: {job.title} at {job.company}")
                
            except Exception as e:
                logger.error(f"Error saving job: {e}")
                continue
        
        return jobs_created