"""
Bill D'Bettabody - Context Integrity Pre-Check
Implements Section 3.7 of Bill Instructions
Ensures correct webhook routing based on client context state
"""

from core.bill_config import ContextIntegrityState


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
    1. If no active sessions exist → generate_training_plan
    2. If sessions exist but no steps → populate_training_week
    3. If both exist → session_update
    
    Args:
        client_context: Dict containing client data
        operation_intent: Type of operation ('training', 'profile', 'contraindication')
        
    Returns:
        tuple: (webhook_name, reasoning)
    """
    
    # Non-training operations bypass context integrity check
    if operation_intent in ['profile', 'contraindication']:
        return None, 'Non-training operation - no context check required'
    
    state = determine_context_state(client_context)
    
    if state == ContextIntegrityState.NO_SESSIONS:
        return (
            'full_training_block',
            'Context integrity escalation: No active sessions exist. Must generate plan first.'
        )
    
    elif state == ContextIntegrityState.NO_STEPS:
        return (
            'populate_training_week',
            'Context integrity escalation: Sessions exist but no steps populated. Must populate week.'
        )
    
    else:  # READY_TO_UPDATE
        return (
            'session_update',
            'Context ready: Both sessions and steps exist. Safe to update.'
        )


def validate_session_ids_present(client_context):
    """
    Validate that session_id values exist before attempting populate_training_week
    
    Section 5.2: HARD PRECONDITION
    Bill MUST NOT attempt to populate a training week unless valid, active 
    session_id values already exist in the currently loaded client context.
    
    Args:
        client_context: Dict containing client data
        
    Returns:
        tuple: (bool, error_message or None)
    """
    sessions = client_context.get('sessions', {})
    active_sessions = sessions.get('active', []) if isinstance(sessions, dict) else []
    
    if not active_sessions:
        return False, "No active sessions found in context. Cannot populate week."
    
    # Check that sessions have session_id values
    for session in active_sessions:
        if not session.get('session_id'):
            return False, "Session exists but missing session_id. Context may be stale."
    
    return True, None


def should_refresh_context(webhook_name):
    """
    Check if a webhook requires context refresh after execution
    
    Section 2.1B + 3.7: POST-WRITE CONTEXT REFRESH (MANDATORY)
    Any successful write-type webhook call makes the currently loaded 
    client context STALE immediately.
    
    Args:
        webhook_name: Name of webhook that was executed
        
    Returns:
        bool: True if context refresh is required
    """
    from core.bill_config import WRITE_WEBHOOKS
    return webhook_name in WRITE_WEBHOOKS


def log_context_integrity_escalation(webhook_name, reasoning, client_id):
    """
    Log when context integrity check triggers an escalation
    
    Args:
        webhook_name: The webhook selected by integrity check
        reasoning: Why this webhook was selected
        client_id: Client identifier
    """
    print(f"[Context Integrity] Client: {client_id}")
    print(f"[Context Integrity] Selected webhook: {webhook_name}")
    print(f"[Context Integrity] Reasoning: {reasoning}")