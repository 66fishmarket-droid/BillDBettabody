"""
Bill D'Bettabody - Client Context & Session Models
Session state management with Bill-compliant rules
"""

from datetime import datetime
import uuid
from core.bill_config import ClientState, OperatingMode


# In-memory session storage (Redis/database in production)
sessions = {}


def generate_session_id():
    """Generate unique session identifier"""
    return f"sess_{uuid.uuid4().hex[:16]}"


def create_stranger_session(client_id=None):
    """
    Create session for new/onboarding client
    Section 1.5: Stranger/Prospect Handling
    Section 1.3A: Client ID naming guidance
    
    Args:
        client_id: Proposed client_id (if user has chosen one)
        
    Returns:
        str: session_id
    """
    session_id = generate_session_id()
    
    sessions[session_id] = {
        'session_id': session_id,
        'client_id': client_id,
        'state': ClientState.ONBOARDING if client_id else ClientState.STRANGER,
        'mode': OperatingMode.COACH,
        'developer_authenticated': False,
        'context': {},
        'profile_data': {},  # Collected during onboarding
        'conversation': [],
        'created_at': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat(),
        'last_refresh': None
    }
    
    return session_id


def initialize_session(client_id, context):
    """
    Create session for existing client with loaded context
    Section 1.4: Existing Client Handling
    
    Args:
        client_id: Client identifier
        context: Full client context from Make.com
        
    Returns:
        tuple: (session_id, context)
    """
    session_id = generate_session_id()
    
    sessions[session_id] = {
        'session_id': session_id,
        'client_id': client_id,
        'state': ClientState.READY,
        'mode': OperatingMode.COACH,
        'developer_authenticated': False,
        'context': context,
        'conversation': [],
        'created_at': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat(),
        'last_refresh': datetime.now().isoformat()
    }
    
    return session_id, context


def get_session(session_id):
    """
    Retrieve session by ID
    
    Args:
        session_id: Session identifier
        
    Returns:
        dict: Session data or None
    """
    session = sessions.get(session_id)
    
    if session:
        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
    
    return session


def update_session_state(session_id, new_state):
    """
    Update session state (stranger → onboarding → ready)
    
    Args:
        session_id: Session identifier
        new_state: New ClientState value
    """
    session = sessions.get(session_id)
    
    if session:
        session['state'] = new_state
        session['last_activity'] = datetime.now().isoformat()


def refresh_context(session):
    """
    Refresh client context from Make.com
    Section 2.1B: POST-ACTION CONTEXT REFRESH (MANDATORY)
    
    This should be called after any write operation.
    The actual loading is done by webhook_handler.load_client_context()
    
    Args:
        session: Session dict (modified in place)
    """
    from webhooks.webhook_handler import load_client_context
    
    client_id = session.get('client_id')
    
    if not client_id:
        raise ValueError("Cannot refresh context: no client_id in session")
    
    fresh_context = load_client_context(client_id)
    
    session['context'] = fresh_context
    session['last_refresh'] = datetime.now().isoformat()
    
    print(f"[Session] Context refreshed for {client_id} at {session['last_refresh']}")


def set_developer_mode(session_id, authenticated=True):
    """
    Enable/disable developer mode for session
    Section 1.1A: Developer/Tech Mode
    
    Args:
        session_id: Session identifier
        authenticated: Whether developer is authenticated
    """
    session = sessions.get(session_id)
    
    if session:
        session['developer_authenticated'] = authenticated
        if authenticated:
            session['mode'] = OperatingMode.DEVELOPER
            print(f"[Session] Developer mode ENABLED for {session_id}")
        else:
            session['mode'] = OperatingMode.COACH
            print(f"[Session] Developer mode DISABLED for {session_id}")


def add_message_to_conversation(session_id, user_message, bill_response):
    """
    Add message exchange to conversation history
    
    Args:
        session_id: Session identifier
        user_message: User's message
        bill_response: Bill's response
    """
    session = sessions.get(session_id)
    
    if session:
        session['conversation'].append({
            'user': user_message,
            'bill': bill_response,
            'timestamp': datetime.now().isoformat()
        })
        
        session['last_activity'] = datetime.now().isoformat()


def get_conversation_history(session_id, limit=None):
    """
    Get conversation history for session
    
    Args:
        session_id: Session identifier
        limit: Max number of recent messages (None = all)
        
    Returns:
        list: Conversation messages
    """
    session = sessions.get(session_id)
    
    if not session:
        return []
    
    conversation = session.get('conversation', [])
    
    if limit:
        return conversation[-limit:]
    
    return conversation


def cleanup_old_sessions(max_age_hours=24):
    """
    Remove sessions older than max_age_hours
    
    Args:
        max_age_hours: Maximum session age in hours
    """
    now = datetime.now()
    to_remove = []
    
    for session_id, session in sessions.items():
        last_activity = datetime.fromisoformat(session['last_activity'])
        age_hours = (now - last_activity).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            to_remove.append(session_id)
    
    for session_id in to_remove:
        del sessions[session_id]
        print(f"[Session] Cleaned up expired session: {session_id}")
    
    return len(to_remove)