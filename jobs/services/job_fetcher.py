import requests
import hashlib
import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)

class JobFetcher:
    """Simple fetcher that lets AI do all the parsing work"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': getattr(settings, 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = getattr(settings, 'REQUEST_TIMEOUT', 60)
        self.max_retries = getattr(settings, 'MAX_RETRIES', 5)
        self.retry_delay = 2
        self._ai_service = None
    
    def _get_ai_service(self):
        """Lazy load AI service"""
        if self._ai_service is None:
            try:
                from jobs.services.ai_service import AIService
                self._ai_service = AIService()
            except Exception as e:
                logger.error(f"Failed to load AI service: {e}")
                self._ai_service = None
        return self._ai_service
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL with retries"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url[:100]}... (attempt {attempt + 1}/{self.max_retries})")
                
                # Try different user agents on different attempts
                if attempt == 1:
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                    })
                elif attempt == 2:
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                    })
                
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully fetched {url[:100]}...")
                    return response.text
                    
                elif response.status_code == 403:
                    logger.warning(f"⚠️ Access forbidden for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                    
                elif response.status_code == 404:
                    logger.warning(f"❌ Page not found: {url[:100]}...")
                    return None
                    
                elif response.status_code in [429, 503]:
                    logger.warning(f"⚠️ Rate limited for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (3 ** attempt))
                    continue
                    
                else:
                    logger.warning(f"⚠️ Status {response.status_code} for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout fetching {url[:100]}... (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"❌ All timeout attempts failed for {url[:100]}...")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Error fetching {url[:100]}...: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return None
        
        return None
    
    def extract_clean_text(self, html: str) -> str:
        """Extract clean text from HTML - simple and reliable"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove non-content tags
        for tag in soup(['script', 'style', 'meta', 'link', 'noscript', 'header', 'footer', 'nav', 'iframe']):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up
        lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
        
        # Filter out common junk
        junk_patterns = ['cookie', 'privacy', 'terms', '©', 'share', 'linkedin', 'twitter', 'facebook', 'instagram']
        filtered = [line for line in lines if not any(p in line.lower() for p in junk_patterns)]
        
        return '\n'.join(filtered) if filtered else '\n'.join(lines)
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        """Let AI parse everything - the simple way"""
        
        # Check if page indicates job is gone
        if 'no longer available' in html.lower() or 'job expired' in html.lower():
            logger.warning(f"Job is no longer available: {source_url}")
            return []
        
        # Extract clean text
        clean_text = self.extract_clean_text(html)
        
        if not clean_text or len(clean_text) < 100:
            logger.warning(f"Not enough text to parse: {len(clean_text)} chars")
            # Try a different approach - get raw text
            soup = BeautifulSoup(html, 'html.parser')
            clean_text = soup.get_text(separator='\n', strip=True)
            if len(clean_text) < 100:
                return []
        
        # Get AI service
        ai_service = self._get_ai_service()
        if not ai_service:
            logger.warning("AI service not available, using fallback")
            return self._fallback_parse(html, source_url)
        
        # Let AI do the work
        logger.info(f"🤖 Sending {len(clean_text)} chars to AI for parsing...")
        
        try:
            # Use AI to extract job data
            extracted = ai_service.extract_job_details(clean_text)
            
            if not extracted:
                logger.warning("AI returned no data, using fallback")
                return self._fallback_parse(html, source_url)
            
            # Build job data
            job_data = self._build_job_data(extracted, source_url, clean_text)
            
            if job_data:
                logger.info(f"✅ AI parsed: {job_data.get('title')} at {job_data.get('company')}")
                return [job_data]
            else:
                logger.warning("Failed to build job data from AI response")
                return self._fallback_parse(html, source_url)
                
        except Exception as e:
            logger.error(f"AI parsing error: {e}, using fallback")
            return self._fallback_parse(html, source_url)
    
    def _build_job_data(self, data: Dict, source_url: str, clean_text: str) -> Optional[Dict]:
        """Build job data from AI response"""
        try:
            # Get basic fields with defaults
            title = data.get('title', 'Untitled')
            company = data.get('company', 'Unknown Company')
            location = data.get('location', 'Remote')
            description = data.get('description', '')
            
            # If description is empty, use the clean text
            if not description or len(description) < 50:
                description = clean_text[:3000]
            
            job_data = {
                'title': title[:255],
                'company': company[:255],
                'location': location[:255] if location else 'Remote',
                'description': description[:5000] if description else 'No description available',
                'salary': data.get('salary', ''),
                'requirements': data.get('requirements', []),
                'responsibilities': data.get('responsibilities', []),
                'benefits': data.get('benefits', []),
                'qualifications': data.get('qualifications', []),
                'experience_required': data.get('experience_required', ''),
                'education_required': data.get('education_required', ''),
                'work_arrangement': data.get('work_arrangement', ''),
                'job_type': data.get('job_type', 'FULL_TIME'),
                'experience_level': data.get('experience_level', 'MID'),
                'is_remote': 'remote' in data.get('work_arrangement', '').lower() or 'remote' in clean_text.lower(),
                'is_hybrid': 'hybrid' in data.get('work_arrangement', '').lower(),
                'posted_date': datetime.now(),
                'source_url': source_url,
                'external_id': self._extract_id_from_url(source_url),
            }
            job_data['content_hash'] = self.generate_content_hash(job_data)
            return job_data
            
        except Exception as e:
            logger.error(f"Error building job data: {e}")
            return None
    
    def _fallback_parse(self, html: str, source_url: str) -> List[Dict]:
        """Simple fallback parsing - gets whatever it can"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find a title
            title = None
            for tag in ['h1', 'h2', 'h3']:
                elem = soup.find(tag)
                if elem and len(elem.text.strip()) > 5:
                    title = elem.text.strip()
                    break
            
            if not title:
                return []
            
            # Try to find some text
            paragraphs = soup.find_all('p')
            description = '\n'.join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 20])
            
            job_data = {
                'title': title[:255],
                'company': 'Unknown Company',
                'location': 'Remote',
                'description': description[:5000] if description else 'No description available',
                'salary': '',
                'requirements': [],
                'responsibilities': [],
                'benefits': [],
                'qualifications': [],
                'experience_required': '',
                'education_required': '',
                'is_remote': 'remote' in html.lower(),
                'is_hybrid': 'hybrid' in html.lower(),
                'posted_date': datetime.now(),
                'source_url': source_url,
                'external_id': self._extract_id_from_url(source_url),
            }
            job_data['content_hash'] = self.generate_content_hash(job_data)
            
            logger.info(f"📝 Fallback parsed: {job_data['title']}")
            return [job_data]
            
        except Exception as e:
            logger.error(f"Fallback parsing error: {e}")
            return []
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract job ID from URL"""
        patterns = [
            r'/(\d+)/?$',
            r'job/([^/?]+)',
            r'id=([^&]+)',
            r'jr_id=([^&]+)',
            r'/([a-f0-9-]+)$',
            r'req-(\d+)',
            r'job-(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return ''
    
    def generate_content_hash(self, job_data: Dict) -> str:
        """Generate a unique hash for duplicate detection"""
        content = f"{job_data.get('title', '')}{job_data.get('company', '')}{job_data.get('description', '')[:500]}"
        return hashlib.sha256(content.encode()).hexdigest()


class JobFetcherFactory:
    """Factory to create fetcher (just returns the simple one)"""
    
    @staticmethod
    def get_fetcher(source_type: str) -> JobFetcher:
        return JobFetcher()
    
    @staticmethod
    def get_fetcher_for_url(url: str) -> JobFetcher:
        return JobFetcher()