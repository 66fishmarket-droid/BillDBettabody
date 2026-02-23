"""
Bill D'Bettabody - Webhook Payload Validator
Validates payloads before sending to Make.com

This module prevents Bill (Claude) from sending malformed payloads by:
1. Checking required fields exist
2. Validating data types
3. Enforcing field constraints (min/max, enums)
4. Providing clear error messages for Claude to self-correct
"""

from jsonschema import validate, ValidationError, Draft7Validator
from webhooks.webhook_schemas import WEBHOOK_SCHEMAS, CRITICAL_FIELDS


def validate_webhook_payload(webhook_name, payload):
    """
    Validate webhook payload against schema
    
    Args:
        webhook_name: Name of webhook (e.g., 'populate_training_week')
        payload: Dict payload to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
        
    Example:
        is_valid, error = validate_webhook_payload('populate_training_week', payload)
        if not is_valid:
            print(f"Validation failed: {error}")
    """
    
    # Check if we have a schema for this webhook
    if webhook_name not in WEBHOOK_SCHEMAS:
        return True, None  # No schema defined, allow through
    
    schema = WEBHOOK_SCHEMAS[webhook_name]
    
    try:
        # Validate against JSON schema
        validate(instance=payload, schema=schema)
        
        # Additional critical field checks
        if webhook_name in CRITICAL_FIELDS:
            for field_name, location, description in CRITICAL_FIELDS[webhook_name]:
                if not check_critical_field(payload, field_name, location):
                    return False, f"CRITICAL FIELD MISSING: '{field_name}' in {location}. {description}"
        
        return True, None
        
    except ValidationError as e:
        # Format validation error for Claude to understand
        error_msg = format_validation_error(e, webhook_name)
        return False, error_msg


def check_critical_field(payload, field_name, location):
    """
    Check if a critical field exists in the specified location
    
    Args:
        payload: Dict payload
        field_name: Name of field to check
        location: Path to field (e.g., 'sessions[*]' means check all session items)
        
    Returns:
        bool: True if field exists where expected
    """
    
    if location == 'sessions[*]':
        # Check all sessions have this field
        sessions = payload.get('sessions', [])
        for session in sessions:
            if field_name not in session or not session[field_name]:
                return False
        return len(sessions) > 0
    
    elif location == 'session_updates':
        # Check if session_updates exists and has the field
        session_updates = payload.get('session_updates', {})
        # session_summary is optional in updates unless the update is significant
        # So we won't enforce it here - just document it
        return True
    
    else:
        # Simple top-level check
        return field_name in payload and payload[field_name]


def format_validation_error(error, webhook_name):
    """
    Format jsonschema ValidationError into Claude-readable message
    
    Args:
        error: ValidationError from jsonschema
        webhook_name: Name of webhook for context
        
    Returns:
        str: Formatted error message
    """
    
    # Extract the path to the error
    path = ".".join(str(p) for p in error.path) if error.path else "root"
    
    # Build helpful message
    msg = f"""
WEBHOOK PAYLOAD VALIDATION FAILED: {webhook_name}

Error at: {path}
Problem: {error.message}

Schema expected: {error.schema.get('type', 'unknown')}
You provided: {type(error.instance).__name__}

HOW TO FIX:
1. Check the Scenario Helper Instructions for '{webhook_name}'
2. Ensure all REQUIRED fields are present
3. Verify data types match the schema
4. For session_summary: Must be 10-500 characters, plain language

Example valid structure for this webhook:
{get_example_payload(webhook_name)}
"""
    
    return msg.strip()


def get_example_payload(webhook_name):
    """
    Get example payload for a webhook
    
    Args:
        webhook_name: Name of webhook
        
    Returns:
        str: Example JSON payload (formatted)
    """
    
    examples = {
        'populate_training_week': '''
{
  "client_id": "cli_demo",
  "context": {
    "plan_id": "plan_001",
    "block_id": "block_001",
    "week_id": "week_001",
    "week_number": 1
  },
  "sessions": [
    {
      "session_id": "sess_001",
      "session_summary": "Right then, leg day. Heavy squats today at RPE 8...",
      "steps": [
        {
          "step_order": 1,
          "segment_type": "warmup",
          "exercise_name": "Hip Mobility",
          "sets": 1,
          "reps": 10
        }
      ]
    }
  ]
}
        ''',
        
        'session_update': '''
{
  "session_id": "sess_001",
  "client_id": "cli_demo",
  "session_updates": {
    "location": "home",
    "session_summary": "Changed plans - home workout today..."
  },
  "steps_upsert": []
}
        '''
    }
    
    return examples.get(webhook_name, "See Scenario Helper for structure")


def validate_or_raise(webhook_name, payload):
    """
    Validate payload and raise exception if invalid
    
    This is a convenience wrapper for use in webhook_handler.execute_webhook()
    
    Args:
        webhook_name: Name of webhook
        payload: Dict payload to validate
        
    Raises:
        ValueError: If validation fails, with detailed error message
    """
    
    is_valid, error_msg = validate_webhook_payload(webhook_name, payload)
    
    if not is_valid:
        raise ValueError(f"Webhook payload validation failed:\n{error_msg}")


def get_validation_summary(webhook_name):
    """
    Get human-readable summary of what a webhook expects
    
    Useful for Claude to review before constructing payload
    
    Args:
        webhook_name: Name of webhook
        
    Returns:
        str: Summary of requirements
    """
    
    if webhook_name not in WEBHOOK_SCHEMAS:
        return f"No schema defined for '{webhook_name}'"
    
    schema = WEBHOOK_SCHEMAS[webhook_name]
    required = schema.get('required', [])
    
    summary = f"WEBHOOK: {webhook_name}\n"
    summary += f"REQUIRED FIELDS: {', '.join(required)}\n"
    
    if webhook_name in CRITICAL_FIELDS:
        summary += "\nCRITICAL FIELDS (MUST NOT BE EMPTY):\n"
        for field_name, location, description in CRITICAL_FIELDS[webhook_name]:
            summary += f"  - {field_name} ({location}): {description}\n"
    
    return summary