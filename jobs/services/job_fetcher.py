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
    """Base class for fetching jobs from different sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': getattr(settings, 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        self.timeout = getattr(settings, 'REQUEST_TIMEOUT', 60)
        self.max_retries = getattr(settings, 'MAX_RETRIES', 5)
        self.retry_delay = 2
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL with retries and exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url[:100]}... (attempt {attempt + 1}/{self.max_retries})")
                
                # Different headers for different attempts to avoid blocking
                if attempt == 0:
                    pass
                elif attempt == 1:
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
                    })
                elif attempt == 2:
                    self.session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                    })
                
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully fetched {url[:100]}...")
                    return response.text
                    
                elif response.status_code == 403:
                    logger.warning(f"⚠️ Access forbidden (403) for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.info(f"Waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                    continue
                    
                elif response.status_code == 404:
                    logger.warning(f"❌ Page not found (404) for {url[:100]}...")
                    return None
                    
                elif response.status_code in [429, 503]:
                    logger.warning(f"⚠️ Rate limited ({response.status_code}) for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (3 ** attempt)
                        logger.info(f"Waiting {wait_time}s before retry")
                        time.sleep(wait_time)
                    continue
                    
                else:
                    logger.warning(f"⚠️ Status {response.status_code} for {url[:100]}...")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout fetching {url[:100]}... (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ All timeout attempts failed for {url[:100]}...")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Connection error for {url[:100]}...: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (1.5 ** attempt)
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ All connection attempts failed for {url[:100]}...")
                    return None
                    
            except requests.exceptions.TooManyRedirects as e:
                logger.error(f"🔄 Too many redirects for {url[:100]}...: {e}")
                return None
                
            except Exception as e:
                logger.error(f"❌ Unexpected error fetching {url[:100]}...: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return None
        
        return None
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        """Parse job data - handles both single job pages and job listings"""
        soup = BeautifulSoup(html, 'html.parser')
        html_text = str(soup)  # ← FIX: Define html_text for checking
        
        # Check if the page indicates the job is no longer available
        if 'no longer available' in html_text.lower() or 'job expired' in html_text.lower():
            logger.warning(f"Job is no longer available: {source_url}")
            return []
        
        jobs = []
        
        # First, try to parse as a single job page
        logger.info("Attempting to parse as single job page...")
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            logger.info(f"✅ Found single job posting: {single_job.get('title')}")
            jobs.append(single_job)
            return jobs
        
        # If not a single job page, try to parse as job listing
        logger.info("Attempting to parse as job listing page...")
        jobs = self._parse_job_listings(soup, source_url)
        
        if jobs:
            logger.info(f"✅ Found {len(jobs)} jobs from listing page")
        else:
            logger.warning("❌ No jobs found on page")
        
        return jobs
    
    def _parse_single_job_page(self, soup: BeautifulSoup, source_url: str) -> Optional[Dict]:
        """Parse a single job detail page"""
        try:
            # Get the HTML text for searching
            html_text = str(soup)  # ← FIX: Define html variable
            
            # Try to find job title with multiple selectors
            title_selectors = [
                'h1', 'h2.job-title', 'h1.job-title', 'div.job-title',
                'h1[data-automation="job-title"]', 'h1[data-testid="job-title"]',
                'h1.job-detail-title', '.job-header h1', '.posting-title h1',
                'h1[data-automation-id="jobTitle"]', '.job-detail-header h1',
                'h1[itemprop="title"]', '.job-title-text', '.job-title--text',
                '.posting-headline h1', 'h1.posting-title', '.css-1uq0n8y'
            ]
            
            title = None
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    title = elem.text.strip()
                    break
            
            if not title:
                # Try meta tags
                meta_title = soup.find('meta', {'property': 'og:title'})
                if meta_title and meta_title.get('content'):
                    title = meta_title.get('content')
                else:
                    meta_title = soup.find('meta', {'name': 'twitter:title'})
                    if meta_title and meta_title.get('content'):
                        title = meta_title.get('content')
            
            if not title:
                # Try to find in script tags (common in single-page apps)
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'jobTitle' in script.string:
                        match = re.search(r'"jobTitle"\s*:\s*"([^"]+)"', script.string)
                        if match:
                            title = match.group(1)
                            break
                        match = re.search(r'"title"\s*:\s*"([^"]+)"', script.string)
                        if match:
                            title = match.group(1)
                            break
            
            if not title:
                # Check if the page says the job is no longer available
                if 'no longer available' in html_text.lower() or 'job expired' in html_text.lower():
                    logger.warning("Job is no longer available")
                    return None
                logger.warning("Could not find job title")
                return None
            
            # Clean title
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Try to find company
            company_selectors = [
                '.company', '.employer', '.company-name', '.employer-name',
                'div[data-automation="job-company"]', 'div[data-testid="company-name"]',
                '.job-header .company', '.posting-company', '.job-detail-company',
                'span.company-name', 'div.company-info', '.company-info',
                '[itemprop="hiringOrganization"]', '.job-company', '.css-1u4a1zn'
            ]
            
            company = None
            for selector in company_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    company = elem.text.strip()
                    break
            
            if not company:
                # Try meta tags
                meta_company = soup.find('meta', {'property': 'og:site_name'})
                if meta_company and meta_company.get('content'):
                    company = meta_company.get('content')
                else:
                    # Try to find in script tags
                    scripts = soup.find_all('script')
                    for script in scripts:
                        if script.string and 'companyName' in script.string:
                            match = re.search(r'"companyName"\s*:\s*"([^"]+)"', script.string)
                            if match:
                                company = match.group(1)
                                break
                            match = re.search(r'"company"\s*:\s*"([^"]+)"', script.string)
                            if match:
                                company = match.group(1)
                                break
            
            if not company:
                company = 'Unknown Company'
            
            company = re.sub(r'\s+', ' ', company).strip()
            
            # Try to find location
            location_selectors = [
                '.location', '.job-location', '.job-location-text',
                'div[data-automation="job-location"]', 'div[data-testid="job-location"]',
                '.job-header .location', '.posting-location', '.job-detail-location',
                'span.location', '.job-location-info', '[itemprop="jobLocation"]',
                '.location-text', '.css-1j6scjc'
            ]
            
            location = None
            for selector in location_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    location = elem.text.strip()
                    break
            
            if not location:
                # Try to find in script tags
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'location' in script.string.lower():
                        match = re.search(r'"location"\s*:\s*"([^"]+)"', script.string)
                        if match:
                            location = match.group(1)
                            break
                        match = re.search(r'"jobLocation"\s*:\s*"([^"]+)"', script.string)
                        if match:
                            location = match.group(1)
                            break
            
            if not location:
                location = 'Remote' if 'remote' in html_text.lower() else 'Unknown'
            
            location = re.sub(r'\s+', ' ', location).strip()
            
            # Try to find description
            description_selectors = [
                '.description', '.job-description', '.jd', '.job-detail-description',
                'div[data-automation="job-description"]', 'div[data-testid="job-description"]',
                '.posting-description', '.job-description-text', '.job-desc',
                '[itemprop="description"]', '.job-description-content', '.css-1p0h5k1'
            ]
            
            description = None
            for selector in description_selectors:
                elem = soup.select_one(selector)
                if elem:
                    # Get all text from the description area
                    desc_parts = []
                    for tag in elem.find_all(['p', 'li', 'div', 'span']):
                        text = tag.text.strip()
                        if text and len(text) > 5:
                            desc_parts.append(text)
                    description = '\n'.join(desc_parts) if desc_parts else elem.text.strip()
                    break
            
            if not description:
                # Try to get all paragraphs
                paragraphs = soup.find_all('p')
                if paragraphs:
                    desc_parts = []
                    for p in paragraphs:
                        text = p.text.strip()
                        if len(text) > 20:
                            desc_parts.append(text)
                    description = '\n'.join(desc_parts) if desc_parts else 'Description not available'
                else:
                    # Try to get div content
                    content_divs = soup.find_all('div', class_=lambda x: x and 'content' in x.lower())
                    if content_divs:
                        description = content_divs[0].text.strip()
                    else:
                        description = 'Description not available'
            
            if description and len(description) > 10:
                description = re.sub(r'\s+', ' ', description).strip()
            else:
                description = 'Description not available'
            
            # Try to find salary
            salary_selectors = [
                '.salary', '.compensation', '.pay-rate', '.salary-range',
                'span[data-automation="job-salary"]', '.job-salary',
                '.salary-info', '.pay', '.compensation-info', '.css-1xa6vbg'
            ]
            
            salary = None
            for selector in salary_selectors:
                elem = soup.select_one(selector)
                if elem and elem.text.strip():
                    salary = elem.text.strip()
                    break
            
            if not salary:
                # Try to find in text using html_text
                salary_patterns = [
                    r'\$\d+[\.,]?\d*\s*[-–]\s*\$\d+[\.,]?\d*',
                    r'\$\d+[\.,]?\d*\s*(?:k|K|per year|annually|year)',
                    r'\$\d+[\.,]?\d*\s*-\s*\$\d+[\.,]?\d*',
                    r'\$\d+[\.,]?\d*\s*\/\s*hr',
                ]
                for pattern in salary_patterns:
                    match = re.search(pattern, html_text)  # ← FIX: Use html_text
                    if match:
                        salary = match.group(0)
                        break
            
            # Check if remote using html_text
            is_remote = False
            is_hybrid = False
            remote_indicators = ['remote', 'work from home', 'wfh', 'virtual', 'telecommute', 'anywhere']
            hybrid_indicators = ['hybrid', 'flexible', 'home office', 'partially remote']
            
            # Use html_text for checking
            text_to_check = f"{title} {location} {description} {html_text}".lower()
            
            if 'remote' in text_to_check and not 'onsite' in text_to_check and not 'on-site' in text_to_check:
                if any(indicator in text_to_check for indicator in hybrid_indicators):
                    is_hybrid = True
                    is_remote = True
                else:
                    is_remote = True
            
            # Build job data
            job_data = {
                'title': title[:255] if title else 'Untitled',
                'company': company[:255] if company else 'Unknown Company',
                'location': location[:255] if location else 'Remote',
                'description': description[:5000] if description else 'Description not available',
                'salary': salary,
                'posted_date': datetime.now(),
                'source_url': source_url,
                'external_id': self._extract_id_from_url(source_url),
                'is_remote': is_remote,
                'is_hybrid': is_hybrid,
            }
            job_data['content_hash'] = self.generate_content_hash(job_data)
            
            logger.info(f"📝 Parsed job: {job_data['title']} at {job_data['company']}")
            return job_data
            
        except Exception as e:
            logger.error(f"Error parsing single job page: {e}")
            return None
    
    def _parse_job_listings(self, soup: BeautifulSoup, source_url: str) -> List[Dict]:
        """Parse job listings page (multiple jobs)"""
        jobs = []
        
        # Try common selectors for job listings
        job_selectors = [
            'div.job-listing', 'div.job-item', 'div.job-card',
            'div.job-posting', 'div.job-search-result', 'li.job',
            'article.job', 'div[data-job-id]', 'div[data-job-url]',
            'div.job-result', 'div.search-result', '.job-tile'
        ]
        
        for selector in job_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    try:
                        job_data = self._extract_job_from_listing_element(element, source_url)
                        if job_data:
                            jobs.append(job_data)
                    except Exception:
                        continue
                if jobs:
                    break
        
        return jobs
    
    def _extract_job_from_listing_element(self, element, source_url: str) -> Optional[Dict]:
        """Extract job data from a listing element"""
        try:
            # Try to find title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'], 
                                      class_=lambda x: x and ('title' in x.lower() or 'job' in x.lower()))
            if not title_elem:
                title_elem = element.find('a', href=True)
            title = title_elem.text.strip() if title_elem else None
            
            if not title:
                return None
            
            # Try to find company
            company_elem = element.find(['span', 'div'], 
                                        class_=lambda x: x and ('company' in x.lower() or 'employer' in x.lower()))
            company = company_elem.text.strip() if company_elem else 'Unknown Company'
            
            # Try to find location
            location_elem = element.find(['span', 'div'], 
                                         class_=lambda x: x and ('location' in x.lower() or 'place' in x.lower()))
            location = location_elem.text.strip() if location_elem else 'Remote'
            
            # Try to find link
            link_elem = element.find('a', href=True)
            link = link_elem.get('href') if link_elem else ''
            
            job_data = {
                'title': title,
                'company': company,
                'location': location,
                'description': 'Description not available',
                'salary': None,
                'posted_date': datetime.now(),
                'source_url': source_url,
                'external_id': element.get('data-id', '') or element.get('id', ''),
                'is_remote': 'remote' in location.lower() or 'remote' in title.lower(),
            }
            if link and link.startswith('http'):
                job_data['source_url'] = link
            job_data['content_hash'] = self.generate_content_hash(job_data)
            return job_data
        except Exception:
            return None
    
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
            r'_(\d+)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        
        parts = url.rstrip('/').split('/')
        last_part = parts[-1] if parts else ''
        last_part = last_part.split('?')[0]
        if last_part:
            return last_part
        return ''
    
    def generate_content_hash(self, job_data: Dict) -> str:
        """Generate a unique hash for duplicate detection"""
        content = f"{job_data.get('title', '')}{job_data.get('company', '')}{job_data.get('description', '')[:500]}"
        return hashlib.sha256(content.encode()).hexdigest()


# ============================================
# SITE-SPECIFIC FETCHERS
# ============================================

class LinkedInFetcher(JobFetcher):
    """Fetcher for LinkedIn job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # First try single job page
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        # Then try job listings
        jobs = []
        job_cards = soup.find_all('div', class_='job-search-card')
        if not job_cards:
            job_cards = soup.find_all('li', class_='jobs-search-results__list-item')
        
        for card in job_cards:
            try:
                title_elem = card.find('h3', class_='base-search-card__title') or card.find('a', class_='job-title-link')
                company_elem = card.find('h4', class_='base-search-card__subtitle') or card.find('a', class_='hidden-nested-link')
                location_elem = card.find('span', class_='job-search-card__location')
                
                if title_elem and company_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': location_elem.text.strip() if location_elem else 'Remote',
                        'description': 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': card.get('data-id', '') or card.get('data-urn', ''),
                        'is_remote': 'remote' in location_elem.text.lower() if location_elem else False,
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing LinkedIn job card: {e}")
                continue
        
        return jobs


class IndeedFetcher(JobFetcher):
    """Fetcher for Indeed job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # First try single job page
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        jobs = []
        job_cards = soup.find_all('div', class_='jobsearch-SerpJobCard')
        if not job_cards:
            job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        for card in job_cards:
            try:
                title_elem = card.find('a', class_='jobtitle') or card.find('h2', class_='jobTitle')
                company_elem = card.find('span', class_='company') or card.find('div', class_='company_location')
                location_elem = card.find('span', class_='location') or card.find('div', class_='company_location')
                summary_elem = card.find('div', class_='summary')
                
                if title_elem and company_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': location_elem.text.strip() if location_elem else 'Remote',
                        'description': summary_elem.text.strip() if summary_elem else 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': card.get('data-jk', ''),
                        'is_remote': 'remote' in location_elem.text.lower() if location_elem else False,
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing Indeed job card: {e}")
                continue
        
        return jobs


class GlassdoorFetcher(JobFetcher):
    """Fetcher for Glassdoor job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        jobs = []
        job_cards = soup.find_all('li', class_='react-job-listing')
        
        for card in job_cards:
            try:
                title_elem = card.find('a', class_='jobLink')
                company_elem = card.find('div', class_='employerName')
                location_elem = card.find('span', class_='location')
                
                if title_elem and company_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': location_elem.text.strip() if location_elem else 'Remote',
                        'description': 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': card.get('data-id', ''),
                        'is_remote': 'remote' in location_elem.text.lower() if location_elem else False,
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing Glassdoor job card: {e}")
                continue
        
        return jobs


class MonsterFetcher(JobFetcher):
    """Fetcher for Monster job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        jobs = []
        job_cards = soup.find_all('div', class_='job-tile')
        
        for card in job_cards:
            try:
                title_elem = card.find('h2', class_='job-title')
                company_elem = card.find('div', class_='company-name')
                location_elem = card.find('div', class_='location')
                
                if title_elem and company_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': location_elem.text.strip() if location_elem else 'Remote',
                        'description': 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': '',
                        'is_remote': 'remote' in location_elem.text.lower() if location_elem else False,
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing Monster job card: {e}")
                continue
        
        return jobs


class FlexJobsFetcher(JobFetcher):
    """Fetcher for FlexJobs job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        jobs = []
        job_cards = soup.find_all('div', class_='job-item')
        if not job_cards:
            job_cards = soup.find_all('div', class_='job-listing')
        
        for card in job_cards:
            try:
                title_elem = card.find('h3', class_='job-title') or card.find('div', class_='job-title')
                company_elem = card.find('div', class_='company-name') or card.find('span', class_='company')
                location_elem = card.find('div', class_='location') or card.find('span', class_='location')
                
                if title_elem and company_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': location_elem.text.strip() if location_elem else 'Remote',
                        'description': 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': card.get('data-id', ''),
                        'is_remote': True,
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing FlexJobs job card: {e}")
                continue
        
        return jobs


class JobrightFetcher(JobFetcher):
    """Fetcher for Jobright.ai job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        html_text = str(soup)
        
        # Check if job is available
        if 'no longer available' in html_text.lower():
            logger.warning(f"Jobright job is no longer available: {source_url}")
            return []
        
        # Try single job page parsing
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        return []


class GreenhouseFetcher(JobFetcher):
    """Fetcher for Greenhouse job listings"""
    
    def parse_job_data(self, html: str, source_url: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        html_text = str(soup)
        
        # Check if job is available
        if 'no longer available' in html_text.lower() or 'this job is no longer accepting applications' in html_text.lower():
            logger.warning(f"Greenhouse job is no longer available: {source_url}")
            return []
        
        # Try single job page parsing
        single_job = self._parse_single_job_page(soup, source_url)
        if single_job:
            return [single_job]
        
        # Try to find job listings
        jobs = []
        job_cards = soup.find_all('div', class_='opening')
        if not job_cards:
            job_cards = soup.find_all('div', class_='job')
        
        for card in job_cards:
            try:
                title_elem = card.find('a', class_='title') or card.find('h2')
                if title_elem:
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': 'Greenhouse',
                        'location': 'Remote' if 'remote' in html_text.lower() else 'Unknown',
                        'description': 'Description not available',
                        'salary': None,
                        'posted_date': datetime.now(),
                        'source_url': source_url,
                        'external_id': card.get('data-id', '') or title_elem.get('href', '').split('/')[-1] if title_elem.get('href') else '',
                        'is_remote': 'remote' in html_text.lower(),
                    }
                    job_data['content_hash'] = self.generate_content_hash(job_data)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error parsing Greenhouse job card: {e}")
                continue
        
        return jobs


class JobFetcherFactory:
    """Factory to create appropriate fetcher based on source type"""
    
    @staticmethod
    def get_fetcher(source_type: str) -> JobFetcher:
        fetchers = {
            'LINKEDIN': LinkedInFetcher,
            'INDEED': IndeedFetcher,
            'GLASSDOOR': GlassdoorFetcher,
            'MONSTER': MonsterFetcher,
            'FLEXJOBS': FlexJobsFetcher,
            'JOBRIGHT': JobrightFetcher,
            'GREENHOUSE': GreenhouseFetcher,
        }
        
        fetcher_class = fetchers.get(source_type, JobFetcher)
        return fetcher_class()
    
    @staticmethod
    def get_fetcher_for_url(url: str) -> JobFetcher:
        """Automatically detect the best fetcher based on URL"""
        url_lower = url.lower()
        
        if 'linkedin.com' in url_lower:
            return LinkedInFetcher()
        elif 'indeed.com' in url_lower:
            return IndeedFetcher()
        elif 'glassdoor.com' in url_lower:
            return GlassdoorFetcher()
        elif 'monster.com' in url_lower:
            return MonsterFetcher()
        elif 'flexjobs.com' in url_lower:
            return FlexJobsFetcher()
        elif 'jobright.ai' in url_lower:
            return JobrightFetcher()
        elif 'greenhouse.io' in url_lower:
            return GreenhouseFetcher()
        elif 'icims.com' in url_lower:
            return JobFetcher()
        else:
            return JobFetcher()