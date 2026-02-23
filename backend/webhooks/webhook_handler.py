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
from core.sheets_client import get_exercise_bests
from webhooks.context_integrity import (
    should_refresh_context_after,
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

        # Guard: Make.com sometimes returns an empty body on cold-start
        # (scenario sleeping and didn't finish in time). Treat as transient error.
        if not raw_text or not raw_text.strip():
            raise ValueError(
                f"Make.com returned an empty response body (HTTP {response.status_code}). "
                "The scenario may be cold-starting — retry the request."
            )

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


def _post_with_retry(webhook_url, payload, timeout=30, retries=3, retry_delay=5):
    """
    POST to a Make.com webhook with retry on empty-body cold-start responses.

    Make.com scenarios sleep after inactivity and may return an empty body on
    the first call while waking up. A single retry after a short delay is enough
    to recover in almost all cases.

    Args:
        webhook_url: Full Make.com webhook URL
        payload: JSON payload dict
        timeout: Per-request timeout in seconds
        retries: Number of retry attempts after the initial call
        retry_delay: Seconds to wait between attempts

    Returns:
        dict: Parsed response from parse_make_response

    Raises:
        ValueError: If all attempts return an empty body
        requests.RequestException: On network errors
    """
    import time

    last_error = None
    for attempt in range(1 + retries):
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=timeout,
            )
            response.raise_for_status()
            raw = response.text.strip()

            # Make.com returns "Accepted" when the scenario runs asynchronously
            # (immediate-response mode). Wait longer on this — scenario needs
            # time to complete before we can get the result.
            if raw == "Accepted":
                wait = 12  # seconds — enough for Make.com to finish the scenario
                if attempt < retries:
                    print(f"[Webhook] Got 'Accepted' on attempt {attempt + 1} — scenario still running, waiting {wait}s...")
                    time.sleep(wait)
                    last_error = ValueError(f"Make.com scenario returned 'Accepted' (async mode) after {wait}s wait")
                    continue
                raise ValueError("Make.com scenario returned 'Accepted' on all attempts — check scenario response mode")

            return parse_make_response(response)
        except (ValueError, json.JSONDecodeError) as e:
            # Empty body or other non-JSON — cold-start or transient error
            last_error = e
            if attempt < retries:
                print(f"[Webhook] Unparseable response on attempt {attempt + 1} (body={repr(response.text[:50])}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
        except requests.RequestException:
            raise

    raise last_error


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

    try:
        data = _post_with_retry(webhook_url, {"client_id": client_id})
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

    try:
        context = _post_with_retry(webhook_url, {"client_id": client_id}, timeout=90)

        # Inject Exercise Bests directly from Google Sheets.
        # This replaces the Make.com fetch (modules 28-29 in the scenario)
        # and is faster, uses zero Make.com ops, and uses the real column names.
        try:
            bests = get_exercise_bests(client_id)
            context['Exercise Bests'] = bests
            print(f"[Context] Exercise Bests loaded from Sheets: {len(bests)} records for {client_id}")
        except Exception as e:
            # Non-fatal: fall back to whatever Make.com returned (may be empty)
            print(f"[Context] WARNING: Direct Sheets read failed, keeping Make.com data: {e}")

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


