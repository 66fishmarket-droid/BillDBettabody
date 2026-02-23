"""
Bill D'Bettabody - Context Integrity Pre-Check
Implements Section 3.7 of Bill Instructions
Ensures correct webhook routing based on client context state
"""

import logging
from core.bill_config import ContextIntegrityState

# Configure logging
logger = logging.getLogger(__name__)


def determine_context_state(client_context):
    """
    Analyze client context to determine its integrity state
    
    Args:
        client_context: Dict containing client data from Make.com
        
    Returns:
        ContextIntegrityState value
    """
    if not client_context:
        return ContextIntegrityState.NO_SESSIONS
    
    # Check for active sessions
    sessions = client_context.get('sessions', {})
    active_sessions = sessions.get('active', []) if isinstance(sessions, dict) else []
    
    if not active_sessions or len(active_sessions) == 0:
        return ContextIntegrityState.NO_SESSIONS
    
    # Check for active steps
    steps = client_context.get('steps', {})
    active_steps = steps.get('active', []) if isinstance(steps, dict) else []
    
    if not active_steps or len(active_steps) == 0:
        return ContextIntegrityState.NO_STEPS
    
    # Both sessions and steps exist
    return ContextIntegrityState.READY_TO_UPDATE


def determine_required_webhook(client_context, operation_intent='training'):
    """
    Section 3.7: Context Integrity Pre-Check (MANDATORY)
    
    Determines which webhook should be called based on current context state.
    This prevents orphaned sessions, incomplete populations, and data corruption.
    
    CANONICAL DECISION ORDER:
    1. If no active sessions exist → generate_training_plan or update_training_plan
    2. If sessions exist but no steps → populate_training_week
    3. If both exist → session_update
    
    WHY THIS MATTERS (North Star Vision):
    - Prevents partial/broken training plans that frustrate users
    - Ensures Bill can focus on being the sympathetic oracle, not debugging data issues
    - Makes the system reliable enough for busy parents, older adults, beginners
    
    Args:
        client_context: Dict containing client data
        operation_intent: Type of operation ('training', 'profile', 'contraindication')
        
    Returns:
        tuple: (webhook_name, reasoning)
    """
    
    # Non-training operations bypass context integrity check
    if operation_intent in ['profile', 'contraindication']:
        logger.debug(f"Non-training operation ({operation_intent}) - no context check required")
        return None, f'Non-training operation ({operation_intent}) - no context check required'
    
    state = determine_context_state(client_context)
    
    if state == ContextIntegrityState.NO_SESSIONS:
        webhook = 'full_training_block'
        reason = 'Context integrity escalation: No active sessions exist. Must generate plan first.'
        logger.info(f"Context check: {reason} → {webhook}")
        return webhook, reason
    
    elif state == ContextIntegrityState.NO_STEPS:
        webhook = 'populate_training_week'
        reason = 'Context integrity escalation: Sessions exist but no steps populated. Must populate week.'
        logger.info(f"Context check: {reason} → {webhook}")
        return webhook, reason
    
    else:  # READY_TO_UPDATE
        webhook = 'session_update'
        reason = 'Context ready: Both sessions and steps exist. Safe to update.'
        logger.debug(f"Context check: {reason} → {webhook}")
        return webhook, reason


def should_refresh_context_after(webhook_name):
    """
    Section 2.1b: POST-WRITE CONTEXT REFRESH (MANDATORY)
    
    Determines if a webhook requires context refresh after successful execution.
    
    Any successful write-type webhook call makes the currently loaded client 
    context STALE immediately. After ANY successful write-type webhook call, 
    the system MUST:
    1. Call fetch_client_context(client_id)
    2. Replace working context with the newly returned context
    3. Re-run the Context Integrity Check before selecting further actions
    
    WHY THIS MATTERS (North Star Vision):
    - Prevents Bill from reasoning on stale data (safety issue)
    - Ensures recommendations are based on current state
    - Critical for dynamic responsiveness (travel, injury, schedule changes)
    
    Args:
        webhook_name: Name of webhook that was executed
        
    Returns:
        bool: True if context refresh is required after this webhook
    
    WRITE-TYPE WEBHOOKS (triggers refresh):
    - post_user_upsert: Profile changes affect recommendations
    - post_contraindication_temp: New injury/pain changes what's safe
    - update_contraindication_temp: Injury status changes programming
    - post_contraindication_chronic: Chronic condition affects long-term planning
    - full_training_block: New plan creates sessions
    - populate_training_week: New steps populate sessions
    - session_update: Modified sessions affect next recommendations
    """
    
    # Canonical list of write-type webhooks that invalidate context
    # This matches Section 2.1b + 3.7 of Bill Instructions
    WRITE_WEBHOOKS = {
        'post_user_upsert',
        'post_contraindication_temp',
        'update_contraindication_temp',
        'post_contraindication_chronic',
        'add_chronic_condition',  # Alias for post_contraindication_chronic
        'add_injury',             # Alias for post_contraindication_temp
        'update_injury_status',   # Alias for update_contraindication_temp
        'full_training_block',
        'populate_training_week',
        'session_update',
    }
    
    refresh_required = webhook_name in WRITE_WEBHOOKS
    
    if refresh_required:
        logger.info(f"Context refresh REQUIRED after webhook: {webhook_name}")
    else:
        logger.debug(f"Context refresh NOT required after webhook: {webhook_name}")
    
    return refresh_required


def validate_session_ids_present(client_context):
    """
    Validate that session_id values exist before attempting populate_training_week
    
    Section 5.2: HARD PRECONDITION
    Bill MUST NOT attempt to populate a training week unless valid, active 
    session_id values already exist in the currently loaded client context.
    
    WHY THIS MATTERS (North Star Vision):
    - Prevents corrupted/incomplete session data
    - Critical during onboarding (first-time users)
    - Ensures reliability for all user types (beginner to experienced)
    
    Args:
        client_context: Dict containing client data
        
    Returns:
        tuple: (bool, error_message or None)
    """
    sessions = client_context.get('sessions', {})
    active_sessions = sessions.get('active', []) if isinstance(sessions, dict) else []
    
    if not active_sessions:
        error_msg = "No active sessions found in context. Cannot populate week."
        logger.warning(error_msg)
        return False, error_msg
    
    # Check that sessions have session_id values
    for idx, session in enumerate(active_sessions):
        if not session.get('session_id'):
            error_msg = f"Session {idx} exists but missing session_id. Context may be stale - refresh required."
            logger.error(error_msg)
            return False, error_msg
    
    logger.debug(f"Session ID validation passed: {len(active_sessions)} sessions with valid IDs")
    return True, None


def log_context_integrity_escalation(webhook_name, reasoning, client_id):
    """
    Log when context integrity check triggers an escalation
    
    This helps with debugging and understanding system behavior during development.
    
    Args:
        webhook_name: The webhook selected by integrity check
        reasoning: Why this webhook was selected
        client_id: Client identifier
    """
    logger.info(f"[Context Integrity] Client: {client_id}")
    logger.info(f"[Context Integrity] Selected webhook: {webhook_name}")
    logger.info(f"[Context Integrity] Reasoning: {reasoning}")