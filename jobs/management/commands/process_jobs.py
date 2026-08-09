from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jobs.services.job_processor import JobProcessor
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process job sources and update job listings'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source-id',
            type=int,
            help='Process specific source ID'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID for evaluation'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all active sources'
        )
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Disable AI processing'
        )
    
    def handle(self, *args, **options):
        user = None
        if options.get('user_id'):
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                self.stderr.write(f"User {options['user_id']} not found")
                return
        
        processor = JobProcessor(use_ai=not options.get('no_ai'))
        
        if options.get('source_id'):
            self.stdout.write(f"Processing source {options['source_id']}")
            jobs = processor.process_source(options['source_id'], user)
            self.stdout.write(f"Added {len(jobs)} jobs")
        
        elif options.get('all'):
            self.stdout.write("Processing all active sources")
            from jobs.models import JobSource
            active_sources = JobSource.objects.filter(is_active=True)
            total_jobs = 0
            for source in active_sources:
                jobs = processor.process_source(source.id, user)
                total_jobs += len(jobs)
            self.stdout.write(f"Added {total_jobs} jobs from {active_sources.count()} sources")
        
        else:
            self.stderr.write("Please specify --source-id or --all")