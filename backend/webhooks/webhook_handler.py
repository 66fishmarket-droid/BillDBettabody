"""
Bill D'Bettabody - Make.com Webhook Handler
Executes webhooks with automatic context refresh after writes
Implements Section 3 (Action Logic) and Section 3.7 (Context Integrity)
"""

import requests
import json
from datetime import datetime
from config import Config
from core.bill_config import is_write_webhook
from webhooks.context_integrity import (
    should_refresh_context,
    validate_session_ids_present,
    log_context_integrity_escalation
)
from webhooks.webhook_validator import validate_or_raise


def parse_make_response(response):
    """
    Parse Make.com webhook response which may have double-nested JSON
    
    Make.com returns: {"body": "{...}", "headers": [...]}
    Problem: The ENTIRE response often contains literal newlines/tabs 
    Solution: Clean the raw response text before any JSON parsing
    
    Args:
        response: requests.Response object
        
    Returns:
        dict: Parsed response data
    """
    import re
    
    try:
        # CRITICAL: Clean the raw response text BEFORE parsing
        # Make.com includes literal control characters in JSON strings
        raw_text = response.text
        
        # We can't just replace all newlines/tabs because the outer JSON
        # structure uses them. We need to be smarter.
        # 
        # The pattern is: {"body": "{\n  ..."}
        # We need to replace control chars INSIDE string values only
        
        # Actually, let's try a different approach:
        # Parse what we can, then handle the body separately
        
        # First attempt: Try to parse as-is (might work if Make.com fixed it)
        try:
            data = response.json()
        except json.JSONDecodeError:
            # Failed - the outer JSON has issues
            # Strip all control characters and try again
            cleaned_text = re.sub(r'[\n\r\t]+', ' ', raw_text)
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                print(f"[Webhook] Failed to parse even after stripping control chars: {str(e)}")
                raise
        
        # Now handle the body if it exists
        if 'body' in data and isinstance(data['body'], str):
            body_str = data['body']
            
            # Clean control characters from body string
            body_str_cleaned = re.sub(r'[\n\r\t]+', ' ', body_str)
            
            try:
                first_body = json.loads(body_str_cleaned)
                
                # Check for second level nesting
                if 'body' in first_body and isinstance(first_body['body'], str):
                    second_body_str = re.sub(r'[\n\r\t]+', ' ', first_body['body'])
                    return json.loads(second_body_str)
                else:
                    return first_body
                    
            except json.JSONDecodeError as e:
                print(f"[Webhook] Failed to parse body: {str(e)}")
                print(f"[Webhook] Cleaned body (first 500 chars): {body_str_cleaned[:500]}")
                # Return the outer data as fallback
                return data
        else:
            # Direct JSON response (no body wrapper)
            return data
            
    except Exception as e:
        print(f"[Webhook] Error parsing response: {str(e)}")
        print(f"[Webhook] Raw response (first 1000 chars): {response.text[:1000]}")
        raise


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
        
        data = parse_make_response(response)
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
        
        # Use centralized parsing
        context = parse_make_response(response)
        
        # Add metadata
        context['_loaded_at'] = datetime.now().isoformat()
        context['_client_id'] = client_id
        
        return context
        
    except requests.RequestException as e:
        print(f"Error loading client context: {str(e)}")
        raise


def execute_webhook(webhook_url, payload):
    """
    Execute a Make.com webhook (SIMPLIFIED for tool calling)
    
    This is called by claude_client.py's execute_tool_call function.
    Session management and context refresh happen at a higher level.
    
    Args:
        webhook_url: Full webhook URL
        payload: JSON payload to send
        
    Returns:
        dict: Response from webhook
    """
    try:
        print(f"[Webhook] Executing webhook: {webhook_url[:50]}...")
        print(f"[Webhook] Payload keys: {list(payload.keys())}")
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        response.raise_for_status()
        
        result = parse_make_response(response)
        
        print(f"[Webhook] Success - Response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
        
        return result
        
    except requests.RequestException as e:
        error_msg = f"Webhook execution failed: {str(e)}"
        print(f"[Webhook] ERROR: {error_msg}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[Webhook] Response status: {e.response.status_code}")
            print(f"[Webhook] Response text: {e.response.text[:500]}")
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
        
        data = parse_make_response(response)
        return data.get('authenticated', False)
        
    except requests.RequestException as e:
        print(f"Error authenticating developer: {str(e)}")
        return False