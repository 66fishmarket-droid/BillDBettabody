"""
Bill D'Bettabody - Make.com Webhook Handler
Executes webhooks with automatic context refresh after writes
Implements Section 3 (Action Logic) and Section 3.7 (Context Integrity)
"""

import requests
from datetime import datetime
from config import Config
from core.bill_config import is_write_webhook
from webhooks.context_integrity import (
    should_refresh_context,
    validate_session_ids_present,
    log_context_integrity_escalation
)


def check_client_exists(client_id):
    """
    Check if a client_id exists in Google Sheets
    Section 3.2: check_client_id_available
    
    Args:
        client_id: Client identifier to check
        
    Returns:
        bool: True if client exists, False otherwise
    """
    webhook_url = Config.WEBHOOKS['check_client_exists']
    
    if not webhook_url:
        raise ValueError("check_client_exists webhook URL not configured")
    
    payload = {
        "client_id": client_id
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('exists', False)
        
    except requests.RequestException as e:
        print(f"Error checking client exists: {str(e)}")
        raise


def load_client_context(client_id):
    """
    Load full client context from Make.com/Google Sheets
    Section 3: load_client_context action
    
    Returns complete client data including:
    - Profile
    - Active plans/blocks
    - Sessions
    - Steps
    - Contraindications
    - Training history
    
    Args:
        client_id: Client identifier
        
    Returns:
        dict: Complete client context
    """
    webhook_url = Config.WEBHOOKS['load_client_context']
    
    if not webhook_url:
        raise ValueError("load_client_context webhook URL not configured")
    
    payload = {
        "client_id": client_id
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        # Parse the response
        import json
        data = response.json()
        
        # Handle double-nested JSON from Make.com
        # First level: { "body": "..." }
        if 'body' in data and isinstance(data['body'], str):
            # Parse first body
            first_body = json.loads(data['body'])
            
            # Second level might also have body
            if 'body' in first_body and isinstance(first_body['body'], str):
                # Parse second body - this is the actual context
                context = json.loads(first_body['body'])
            else:
                # Only one level of nesting
                context = first_body
        else:
            # Direct JSON response
            context = data
        
        # Add metadata
        context['_loaded_at'] = datetime.now().isoformat()
        context['_client_id'] = client_id
        
        return context
        
    except requests.RequestException as e:
        print(f"Error loading client context: {str(e)}")
        raise
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing client context JSON: {str(e)}")
        print(f"Raw response (first 1000 chars): {response.text[:1000]}")
        raise

def execute_webhook(webhook_name, payload, session):
    """
    Execute a Make.com webhook with automatic context refresh
    
    Section 2.1B + 3.7: POST-WRITE CONTEXT REFRESH (MANDATORY)
    After ANY successful write-type webhook call, Bill MUST:
    1) Call load_client_context(client_id) immediately
    2) Replace working context with newly returned context
    3) Confirm the update is visible before continuing
    
    Args:
        webhook_name: Name of webhook to execute
        payload: JSON payload to send
        session: Session object (will be updated if refresh needed)
        
    Returns:
        dict: Response from webhook
    """
    webhook_url = Config.WEBHOOKS.get(webhook_name)
    
    if not webhook_url:
        raise ValueError(f"Webhook URL not configured: {webhook_name}")
    
    # Special validation for populate_training_week
    if webhook_name == 'populate_training_week':
        valid, error_msg = validate_session_ids_present(session.get('context', {}))
        if not valid:
            raise ValueError(f"Cannot populate week: {error_msg}")
    
    try:
        print(f"[Webhook] Executing: {webhook_name}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60  # Longer timeout for training generation
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Check if this webhook requires context refresh
        if should_refresh_context(webhook_name):
            print(f"[Webhook] {webhook_name} is a write operation - refreshing context")
            
            client_id = session.get('client_id')
            if client_id:
                # Refresh context immediately
                fresh_context = load_client_context(client_id)
                
                # Update session with fresh data
                session['context'] = fresh_context
                session['last_refresh'] = datetime.now().isoformat()
                
                print(f"[Webhook] Context refreshed at {session['last_refresh']}")
            else:
                print(f"[Webhook] WARNING: No client_id in session - cannot refresh context")
        
        return result
        
    except requests.RequestException as e:
        print(f"[Webhook] Error executing {webhook_name}: {str(e)}")
        raise


def authenticate_developer(provided_key):
    """
    Authenticate developer access
    Section 1.1A + 3.6: Developer/Tech Mode authentication
    
    Args:
        provided_key: Developer access key
        
    Returns:
        bool: True if authenticated, False otherwise
    """
    webhook_url = Config.WEBHOOKS['authenticate_developer']
    
    if not webhook_url:
        raise ValueError("authenticate_developer webhook URL not configured")
    
    payload = {
        "provided_key": provided_key
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get('authenticated', False)
        
    except requests.RequestException as e:
        print(f"Error authenticating developer: {str(e)}")
        return False


def post_user_upsert(client_id, data, session):
    """
    Create or update client profile
    Section 3.1: post_user_upsert action
    
    Args:
        client_id: Client identifier
        data: Profile data to upsert
        session: Session object (will be refreshed)
        
    Returns:
        dict: Response from webhook
    """
    payload = {
        "client_id": client_id,
        "data": data
    }
    
    return execute_webhook('post_user_upsert', payload, session)


def post_contraindication_temp(client_id, contraindication_data, session):
    """
    Log temporary contraindication (injury, illness, etc.)
    Section 3.3: post_contraindication_temp action
    
    Args:
        client_id: Client identifier
        contraindication_data: Injury/illness details
        session: Session object (will be refreshed)
        
    Returns:
        dict: Response from webhook
    """
    payload = {
        "client_id": client_id,
        **contraindication_data
    }
    
    return execute_webhook('add_injury', payload, session)


def generate_training_plan(client_id, plan_data, session):
    """
    Generate new training block/plan
    Section 5.1: generate_training_plan action
    
    Args:
        client_id: Client identifier
        plan_data: Plan parameters
        session: Session object (will be refreshed)
        
    Returns:
        dict: Response from webhook
    """
    payload = {
        "client_id": client_id,
        **plan_data
    }
    
    return execute_webhook('full_training_block', payload, session)


def populate_training_week(client_id, week_data, session):
    """
    Populate week with training steps
    Section 5.2: populate_training_week action
    
    HARD PRECONDITION: session_id values must already exist in context
    
    Args:
        client_id: Client identifier
        week_data: Week parameters
        session: Session object (will be refreshed)
        
    Returns:
        dict: Response from webhook
    """
    payload = {
        "client_id": client_id,
        **week_data
    }
    
    return execute_webhook('populate_training_week', payload, session)


def update_session(session_id, session_data, session):
    """
    Update existing session/steps
    Section 5.3: session_update action
    
    Args:
        session_id: Session identifier
        session_data: Updated session details
        session: Session object (will be refreshed)
        
    Returns:
        dict: Response from webhook
    """
    payload = {
        "session_id": session_id,
        **session_data
    }
    
    return execute_webhook('session_update', payload, session)