"""
Bill D'Bettabody - Client Classification & Experience Detection
Implements Section 2.1c, 2.1d, 2.1e of Bill Instructions
Determines client experience level and appropriate explanation density
"""

import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class ClientClassifier:
    """
    Automates client experience classification and communication density decisions.
    
    WHY THIS MATTERS (North Star Vision):
    - 18-year-old gym newbie needs verbose explanations and encouragement
    - Experienced athlete needs concise, respectful communication
    - Busy working parent needs efficient, practical guidance
    - Older adult needs patient, accessible instruction
    
    This classifier ensures Bill adapts his communication style to match the person,
    making the exercise oracle accessible to everyone.
    """
    
    # Experience band constants
    BEGINNER = 'beginner'
    EARLY_INTERMEDIATE = 'early_intermediate'
    INTERMEDIATE_PLUS = 'intermediate_plus'
    
    # Explanation density constants
    VERBOSE = 'verbose'
    MODERATE = 'moderate'
    CONCISE = 'concise'
    
    @staticmethod
    def classify_experience(profile):
        """
        Section 2.1c & 2.1d: Determine client experience level
        
        Classifies clients into experience bands based on profile data:
        - BEGINNER: Little/no structured training, unfamiliar with concepts
        - EARLY INTERMEDIATE: Some experience, partial familiarity
        - INTERMEDIATE_PLUS: Consistent history, self-regulating ability
        
        WHY THIS MATTERS (North Star Vision):
        - Prevents overwhelming beginners with jargon
        - Prevents patronizing experienced athletes
        - Enables appropriate progression strategies for all levels
        
        Args:
            profile: Dict containing client profile data
            
        Returns:
            str: 'beginner' | 'early_intermediate' | 'intermediate_plus'
            
        Default Behavior (Section 2.1d):
            When uncertain, defaults to BEGINNER with respectful explanation.
            This is the safest, most inclusive approach.
        """
        
        if not profile:
            logger.warning("No profile provided - defaulting to beginner")
            return ClientClassifier.BEGINNER
        
        # Extract relevant profile fields (with safe defaults)
        training_exp = profile.get('training_experience', '').lower()
        strength_level = profile.get('strength_level', '').lower()
        cardio_fitness = profile.get('cardio_fitness_level', '').lower()
        movement_quality = profile.get('movement_quality', '').lower()
        understands_tempo = profile.get('understands_tempo', 'no').lower()
        understands_loading = profile.get('understands_loading_patterns', 'no').lower()
        
        # BEGINNER INDICATORS (Section 2.1c - Beginner characteristics)
        beginner_training_keywords = ['none', 'minimal', 'new', '<6 months', 'never', 'just starting']
        beginner_strength_keywords = ['none', 'minimal', 'weak', 'untrained']
        beginner_cardio_keywords = ['none', 'minimal', 'poor', 'untrained']
        
        if any(keyword in training_exp for keyword in beginner_training_keywords):
            logger.info(f"Classified as BEGINNER based on training_experience: {training_exp}")
            return ClientClassifier.BEGINNER
        
        if any(keyword in strength_level for keyword in beginner_strength_keywords):
            logger.info(f"Classified as BEGINNER based on strength_level: {strength_level}")
            return ClientClassifier.BEGINNER
        
        if understands_tempo == 'no' and understands_loading == 'no':
            logger.info("Classified as BEGINNER based on unfamiliarity with tempo and loading")
            return ClientClassifier.BEGINNER
        
        # INTERMEDIATE_PLUS INDICATORS (Section 2.1c - Intermediate+ characteristics)
        intermediate_training_keywords = ['1-2 years', '2+ years', '3+ years', 'experienced', 'consistent']
        
        # Strong indicators: understands concepts AND has training history
        if understands_tempo == 'yes' and understands_loading == 'yes':
            if any(keyword in training_exp for keyword in intermediate_training_keywords):
                logger.info(f"Classified as INTERMEDIATE_PLUS based on understanding + experience: {training_exp}")
                return ClientClassifier.INTERMEDIATE_PLUS
        
        # EARLY INTERMEDIATE (Default middle ground)
        # Section 2.1c: Some experience, partial familiarity, inconsistent understanding
        logger.info("Classified as EARLY_INTERMEDIATE (default middle ground)")
        return ClientClassifier.EARLY_INTERMEDIATE
    
    @staticmethod
    def get_explanation_density(classification, detail_preference=None):
        """
        Section 2.1e: Determine appropriate explanation density
        
        Returns communication style based on experience level and user preference.
        
        WHY THIS MATTERS (North Star Vision):
        - Beginners need full explanations to build confidence
        - Experienced users want efficiency without condescension
        - User preference always wins (respects individual learning styles)
        
        Args:
            classification: Experience level from classify_experience()
            detail_preference: User's stated preference ('minimal' | 'standard' | 'detailed')
            
        Returns:
            str: 'verbose' | 'moderate' | 'concise'
            
        Rules (Section 2.1e):
            - Beginners: Always verbose (safety and learning)
            - User wants detailed: Verbose regardless of level
            - User wants minimal: Concise (but never unsafe)
            - Otherwise: Moderate
        """
        
        # BEGINNER: Always verbose for safety and confidence building
        if classification == ClientClassifier.BEGINNER:
            logger.debug("Explanation density: VERBOSE (beginner classification)")
            return ClientClassifier.VERBOSE
        
        # USER PREFERENCE: Explicit detail request overrides classification
        if detail_preference:
            detail_pref_lower = detail_preference.lower()
            
            if detail_pref_lower == 'detailed':
                logger.debug("Explanation density: VERBOSE (user requested detailed)")
                return ClientClassifier.VERBOSE
            
            elif detail_pref_lower == 'minimal':
                logger.debug("Explanation density: CONCISE (user requested minimal)")
                return ClientClassifier.CONCISE
        
        # DEFAULT: Moderate explanation for intermediate+ without explicit preference
        logger.debug(f"Explanation density: MODERATE (classification: {classification})")
        return ClientClassifier.MODERATE
    
    @staticmethod
    def should_check_detail_preference(last_profile_update, check_interval_weeks=6):
        """
        Helper: Determine if Bill should prompt for detail preference check-in
        
        WHY THIS MATTERS (North Star Vision):
        - People's needs change as they progress
        - Regular check-ins prevent communication drift
        - Respects user autonomy (they can always ask for changes)
        
        Usage:
            Every ~6 weeks, Bill can conversationally ask:
            "You've been training for a while now - do you still want detailed 
            explanations, or would you prefer me to be more concise?"
        
        Args:
            last_profile_update: Datetime of last profile update
            check_interval_weeks: How often to prompt (default: 6 weeks)
            
        Returns:
            bool: True if check-in is due
        """
        
        if not last_profile_update:
            logger.debug("No last_profile_update - check-in not applicable")
            return False
        
        # Handle string dates (common from Google Sheets)
        if isinstance(last_profile_update, str):
            try:
                last_profile_update = datetime.fromisoformat(last_profile_update.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse last_profile_update: {last_profile_update}")
                return False
        
        # Calculate time since last update
        weeks_since_update = (datetime.now() - last_profile_update).days / 7
        
        should_check = weeks_since_update >= check_interval_weeks
        
        if should_check:
            logger.info(f"Detail preference check-in due ({weeks_since_update:.1f} weeks since last update)")
        else:
            logger.debug(f"Detail preference check-in not due ({weeks_since_update:.1f} weeks since last update)")
        
        return should_check
    
    @staticmethod
    def get_classification_context(profile):
        """
        Convenience method: Get both classification and density in one call
        
        Returns a dict with all classification info that can be passed to Bill's system prompt.
        
        Args:
            profile: Client profile dict
            
        Returns:
            dict: {
                'experience_level': str,
                'explanation_density': str,
                'check_in_due': bool
            }
        """
        
        classification = ClientClassifier.classify_experience(profile)
        detail_pref = profile.get('detail_level_preference')
        density = ClientClassifier.get_explanation_density(classification, detail_pref)
        
        last_update = profile.get('last_profile_update')
        check_in_due = ClientClassifier.should_check_detail_preference(last_update)
        
        return {
            'experience_level': classification,
            'explanation_density': density,
            'check_in_due': check_in_due
        }
