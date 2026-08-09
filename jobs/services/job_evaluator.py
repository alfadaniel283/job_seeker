import re
from typing import Dict, List, Optional
from django.contrib.auth.models import User
from jobs.models import Job, UserJobPreferences, JobEvaluation
from .ai_service import AIService 
import logging

logger = logging.getLogger(__name__)

class JobEvaluator:
    """Enhanced job evaluator with AI capabilities"""
    
    def __init__(self, user: User):
        self.user = user
        self.ai_service = AIService()
        self.preferences = self._get_or_create_preferences()
    
    def _get_or_create_preferences(self) -> UserJobPreferences:
        """Get or create user preferences"""
        preferences, _ = UserJobPreferences.objects.get_or_create(user=self.user)
        return preferences
    
    def evaluate_job(self, job: Job, use_ai: bool = True) -> Dict:
        """Evaluate a job using AI and rule-based scoring"""
        # Prepare job data for AI
        job_data = {
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'description': job.description,
            'salary': job.salary,
            'is_remote': job.is_remote,
            'is_hybrid': job.is_hybrid,
            'job_type': job.job_type,
            'experience_level': job.experience_level
        }
        
        # Prepare user profile for AI
        user_profile = {
            'skills': self.preferences.include_keywords,
            'preferred_locations': self.preferences.preferred_locations,
            'preferred_job_types': self.preferences.preferred_job_types,
            'preferred_experience_levels': self.preferences.preferred_experience_levels,
            'min_salary': float(self.preferences.min_salary) if self.preferences.min_salary else None,
            'max_salary': float(self.preferences.max_salary) if self.preferences.max_salary else None,
            'remote_only': self.preferences.remote_only,
            'hybrid_allowed': self.preferences.hybrid_allowed
        }
        
        # Get AI analysis
        ai_analysis = {}
        if use_ai:
            try:
                ai_analysis = self.ai_service.analyze_job_match(job_data, user_profile)
            except Exception as e:
                logger.error(f"AI evaluation failed: {e}")
        
        # Calculate rule-based scores
        rule_scores = self._calculate_rule_based_scores(job_data, user_profile)
        
        # Combine scores
        final_scores = self._combine_scores(rule_scores, ai_analysis)
        
        return final_scores
    
    def _calculate_rule_based_scores(self, job_data: Dict, user_profile: Dict) -> Dict:
        """Calculate scores using rule-based system"""
        scores = {
            'location_match': False,
            'remote_match': False,
            'salary_match': False,
            'skill_match': 0.0,
            'experience_match': False,
            'job_type_match': False
        }
        
        # Location evaluation
        if user_profile.get('remote_only'):
            scores['remote_match'] = job_data.get('is_remote', False)
            scores['location_match'] = True
        else:
            scores['remote_match'] = True
            preferred_locations = user_profile.get('preferred_locations', [])
            if preferred_locations:
                job_location = job_data.get('location', '').lower()
                scores['location_match'] = any(
                    loc.lower() in job_location for loc in preferred_locations
                )
            else:
                scores['location_match'] = True
        
        # Salary evaluation
        min_salary = user_profile.get('min_salary')
        max_salary = user_profile.get('max_salary')
        job_salary = job_data.get('salary')
        
        if min_salary and job_salary:
            salary_numbers = re.findall(r'\d+', str(job_salary))
            if salary_numbers:
                salary_value = float(salary_numbers[0])
                scores['salary_match'] = salary_value >= min_salary
                if max_salary:
                    scores['salary_match'] = scores['salary_match'] and salary_value <= max_salary
        
        # Skill match
        include_keywords = user_profile.get('skills', [])
        if include_keywords:
            description_lower = job_data.get('description', '').lower()
            matched = sum(1 for kw in include_keywords if kw.lower() in description_lower)
            scores['skill_match'] = (matched / len(include_keywords)) * 100
        
        # Experience match
        preferred_levels = user_profile.get('preferred_experience_levels', [])
        if preferred_levels:
            job_level = job_data.get('experience_level', '')
            scores['experience_match'] = job_level in preferred_levels
        
        # Job type match
        preferred_types = user_profile.get('preferred_job_types', [])
        if preferred_types:
            job_type = job_data.get('job_type', '')
            scores['job_type_match'] = job_type in preferred_types
        
        return scores
    
    def _combine_scores(self, rule_scores: Dict, ai_analysis: Dict) -> Dict:
        """Combine rule-based and AI scores"""
        # Calculate overall rule-based score
        rule_score = 0.0
        weights = {
            'location_match': 15,
            'remote_match': 10,
            'salary_match': 15,
            'skill_match': 25,
            'experience_match': 20,
            'job_type_match': 15
        }
        
        for key, weight in weights.items():
            value = rule_scores.get(key, 0)
            if isinstance(value, bool):
                value = 100 if value else 0
            rule_score += (value / 100) * weight
        
        # Get AI score
        ai_score = ai_analysis.get('match_score', 0)
        
        # Weighted combination (70% rule-based, 30% AI)
        final_score = (rule_score * 0.7) + (ai_score * 0.3)
        
        # Determine if recommended
        is_recommended = final_score >= 70
        
        return {
            'relevance_score': final_score,
            'location_match': rule_scores.get('location_match', False),
            'remote_match': rule_scores.get('remote_match', False),
            'salary_match': rule_scores.get('salary_match', False),
            'skill_match': rule_scores.get('skill_match', 0),
            'experience_match': rule_scores.get('experience_match', False),
            'job_type_match': rule_scores.get('job_type_match', False),
            'is_recommended': is_recommended,
            'ai_analysis': ai_analysis,
            'recommendation_reasons': ai_analysis.get('reasons', []),
            'concerns': ai_analysis.get('concerns', []),
            'culture_fit': ai_analysis.get('culture_fit', 50)
        }
    
    def save_evaluation(self, job: Job, scores: Dict) -> JobEvaluation:
        """Save evaluation to database"""
        evaluation, created = JobEvaluation.objects.update_or_create(
            job=job,
            user=self.user,
            defaults={
                'relevance_score': scores['relevance_score'],
                'location_match': scores['location_match'],
                'remote_match': scores['remote_match'],
                'salary_match': scores['salary_match'],
                'skill_match': scores['skill_match'],
                'experience_match': scores.get('experience_match', False),
                'job_type_match': scores.get('job_type_match', False),
                'is_recommended': scores['is_recommended'],
                'evaluation_notes': self._generate_evaluation_notes(scores)
            }
        )
        return evaluation
    
    def _generate_evaluation_notes(self, scores: Dict) -> str:
        """Generate detailed evaluation notes"""
        notes = []
        notes.append(f"Overall Match Score: {scores['relevance_score']:.1f}%")
        notes.append(f"Recommended: {'Yes' if scores['is_recommended'] else 'No'}")
        
        if scores.get('location_match'):
            notes.append("✓ Location matches your preferences")
        else:
            notes.append("✗ Location does not match your preferences")
        
        if scores.get('remote_match'):
            notes.append("✓ Remote work matches your preference")
        else:
            notes.append("✗ Remote work does not match your preference")
        
        if scores.get('salary_match'):
            notes.append("✓ Salary is within your range")
        else:
            notes.append("✗ Salary may not meet your expectations")
        
        if scores.get('skill_match', 0) >= 70:
            notes.append(f"✓ Good skill match ({scores['skill_match']:.0f}%)")
        else:
            notes.append(f"✗ Low skill match ({scores['skill_match']:.0f}%)")
        
        if scores.get('experience_match'):
            notes.append("✓ Experience level matches your preference")
        
        if scores.get('job_type_match'):
            notes.append("✓ Job type matches your preference")
        
        # Add AI insights
        if scores.get('ai_analysis'):
            ai = scores['ai_analysis']
            if ai.get('reasons'):
                notes.append("\nAI Recommendations:")
                for reason in ai['reasons'][:3]:
                    notes.append(f"  • {reason}")
            
            if ai.get('concerns'):
                notes.append("\nAI Concerns:")
                for concern in ai['concerns'][:2]:
                    notes.append(f"  • {concern}")
        
        return "\n".join(notes)