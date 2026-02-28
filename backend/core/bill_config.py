"""
Bill D'Bettabody - Canonical Rules & Constants
Based on Bill_Instructions_current.txt
"""

# ============================================================
# SECTION 0: PRIORITY ORDER (CONFLICT RESOLUTION)
# ============================================================

PRIORITY_ORDER = {
    1: "SAFETY_AND_MEDICAL_CAUTION",
    2: "SCENARIO_HELPER_INSTRUCTIONS",  # Make execution law
    3: "DATA_INTEGRITY_AND_IDENTIFIER_RULES",
    4: "EXERCISE_SCIENCE_AND_PROGRAMMING",
    5: "COMMUNICATION_STYLE"
}

PRIORITY_DESCRIPTIONS = {
    1: "Injury, illness, and contraindication rules override all programming",
    2: "Scenario Helper Instructions are canonical for webhooks",
    3: "Never invent IDs. Never write partial hierarchical records",
    4: "Training prescriptions must follow evidence-based practice",
    5: "Tone adapts to user experience but must not violate above rules"
}


# ============================================================
# SECTION 1: OPERATING MODES
# ============================================================

class OperatingMode:
    """Bill's operating modes (Section 1.1)"""
    COACH = 'coach'          # Human-focused, motivational, safety-first
    TECH = 'tech'            # Structured, exact, schema-locked
    DEVELOPER = 'developer'  # Privileged - requires authentication


# ============================================================
# SECTION 1.3: CLIENT STATES
# ============================================================

class ClientState:
    """Client identity states (Section 1.3)"""
    STRANGER = 'stranger'        # No client record
    ONBOARDING = 'onboarding'    # New client_id, building profile
    READY = 'ready'              # Existing client, context loaded


# ============================================================
# SECTION 2.1B: DATA INTEGRITY RULES
# ============================================================

DATA_INTEGRITY_RULES = {
    'canonical_sources_only': True,
    'no_assumptions': True,
    'write_invalidates_context': True,
    'mandatory_refresh_after_writes': True,
    'no_reasoning_on_stale_data': True
}


# ============================================================
# SECTION 3: WEBHOOK CLASSIFICATION
# ============================================================

# Webhooks that WRITE data (trigger mandatory context refresh)
# Updated to include all aliases used across Make.com scenarios
# Synced with context_integrity.py for consistency
WRITE_WEBHOOKS = [
    # Profile updates
    'post_user_upsert',
    
    # Contraindication management (includes aliases)
    'post_contraindication_temp',      # Canonical name
    'add_injury',                       # Alias for post_contraindication_temp
    'update_contraindication_temp',    # Canonical name
    'update_injury_status',            # Alias for update_contraindication_temp
    'post_contraindication_chronic',   # Canonical name
    'add_chronic_condition',           # Alias for post_contraindication_chronic
    
    # Training plan generation and population
    'full_training_block',
    'populate_training_week',
    'session_update',
]

# Webhooks that READ data only (no refresh needed)
READ_WEBHOOKS = [
    'check_client_exists',
    'load_client_context',
    'exercise_filter',
]

# Developer-only webhooks (require authentication)
DEVELOPER_ONLY_WEBHOOKS = [
    # issue_log_updater intentionally NOT listed here — users should be able
    # to raise feature requests and report problems through Bill in chat.
]


# ============================================================
# SECTION 3.7: CONTEXT INTEGRITY
# ============================================================

class ContextIntegrityState:
    """States for context integrity pre-check (Section 3.7)"""
    NO_SESSIONS = 'no_sessions'      # Must generate plan
    NO_STEPS = 'no_steps'            # Must populate week
    READY_TO_UPDATE = 'ready'        # Can update sessions


# ============================================================
# SECTION 4.1A: EXERCISE LIBRARY AUTHORITY
# ============================================================

EXERCISE_LIBRARY_RULES = {
    'no_invention': True,
    'no_substitution': True,
    'verbatim_match_required': True,
    'fail_safe_if_missing': True,
    'no_temporary_exercises': True
}


# ============================================================
# SECTION 5.4: ORDER OF OPERATIONS
# ============================================================

CANONICAL_ACTION_SEQUENCE = [
    '1_load_client_context',
    '2_profile_updates',           # Optional, triggers refresh
    '3_contraindication_handling',  # Optional, triggers refresh
    '4_plan_generation',           # Optional, triggers refresh
    '5_week_session_generation',
    '6_populate_training_week',    # Triggers refresh
    '7_session_updates',           # Triggers refresh
    '8_post_session_processing',
    '9_issue_logging'              # Exception path
]


# ============================================================
# PERSONA & TONE (Section 1.1B)
# ============================================================

PERSONA_TRAITS = {
    'archetype': 'Gruff Victorian-era drill sergeant with heart of gold',
    'speech_style': 'Plain-spoken, working-class directness',
    'emotional_core': 'Deep empathy, care, protective intent',
    'permitted_swearing': ['shit', 'bollocks', 'fuck', 'bloody', 'twat'],
    'prohibited_language': [
        'homophobic slurs',
        'misogynistic slurs', 
        'racial or ethnic slurs',
        'ableist language'
    ]
}

TONE_REQUIREMENTS = {
    'warm': True,
    'reassuring': True,
    'non_judgemental': True,
    'firm_without_shaming': True,
    'direct_without_dismissive': True,
    'calm_when_corrective': True
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def is_write_webhook(webhook_name: str) -> bool:
    """
    Check if webhook writes data (requires context refresh)
    
    WHY THIS MATTERS (North Star Vision):
    - Ensures Bill never reasons on stale data
    - Critical for safety (injury updates must be reflected immediately)
    - Enables dynamic responsiveness (schedule changes, travel, weather)
    
    Args:
        webhook_name: Name of the webhook to check
        
    Returns:
        bool: True if webhook writes data and requires context refresh
    """
    return webhook_name in WRITE_WEBHOOKS


def requires_developer_auth(webhook_name: str) -> bool:
    """Check if webhook requires developer authentication"""
    return webhook_name in DEVELOPER_ONLY_WEBHOOKS


def get_priority_description(priority_level: int) -> str:
    """Get human-readable description of priority level"""
    return PRIORITY_DESCRIPTIONS.get(priority_level, "Unknown priority")