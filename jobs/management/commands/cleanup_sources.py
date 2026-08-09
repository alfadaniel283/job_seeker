from django.core.management.base import BaseCommand
from django.db.models import Count
from jobs.models import JobSource

class Command(BaseCommand):
    help = 'Clean up duplicate job sources'

    def handle(self, *args, **options):
        self.stdout.write(" Cleaning up duplicate job sources...")
        
        # Find duplicates
        duplicates = JobSource.objects.values('url').annotate(
            count=Count('url')
        ).filter(count__gt=1)
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate URLs found!"))
            return
        
        self.stdout.write(f"Found {duplicates.count()} duplicate URLs")
        
        for dup in duplicates:
            url = dup['url']
            sources = JobSource.objects.filter(url=url).order_by('created_at')
            
            # Keep the first one, delete the rest
            keep = sources.first()
            delete = sources.exclude(id=keep.id)
            
            self.stdout.write(f"  Keeping: {keep.name} (created: {keep.created_at})")
            self.stdout.write(f"  Deleting {delete.count()} duplicates")
            
            # Move jobs to the kept source before deleting
            for source in delete:
                # Reassign jobs to the kept source
                source.jobs.update(source=keep)
                source.delete()
            
            self.stdout.write(self.style.SUCCESS(f" Cleaned up duplicates for {url[:50]}..."))
        
        self.stdout.write(self.style.SUCCESS("Cleanup complete!"))