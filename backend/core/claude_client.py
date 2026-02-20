"""
Bill D'Bettabody - Claude API Client (WITH PROMPT CACHING SUPPORT)
Handles all interactions with Claude API
Implements Bill's persona, priority hierarchy, and context management
NOW SUPPORTS: Structured system prompts with cache_control + tool calling
"""

import json
import anthropic
from config import Config
from core.context_loader import build_system_prompt
from core.tool_definitions import get_claude_tools, get_webhook_url_for_tool, TOOL_TO_WEBHOOK_KEY
from webhooks.webhook_handler import execute_webhook
from webhooks.webhook_validator import validate_webhook_payload
from webhooks.context_integrity import should_refresh_context_after
from models import client_context


def initialize_client():
    """Initialize Anthropic Claude client"""
    api_key = Config.ANTHROPIC_API_KEY
    
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    
    return anthropic.Anthropic(api_key=api_key)


def build_conversation_history(session):
    """
    Build conversation history in Claude API format
    
    Args:
        session: Session dict with conversation history
        
    Returns:
        list: Messages in Claude API format
    """
    messages = []
    conversation = session.get('conversation', [])
    
    for exchange in conversation:
        # Add user message
        messages.append({
            'role': 'user',
            'content': exchange['user']
        })
        
        # Add assistant (Bill's) response
        messages.append({
            'role': 'assistant',
            'content': exchange['bill']
        })
    
    return messages


def chat(message, session):
    """
    Send message to Claude and get Bill's response
    
    UPDATED: Now handles structured system prompts for prompt caching
    
    Implements:
    - Section 0: Priority hierarchy
    - Section 1: Operating modes and persona
    - Section 2.1b: Context integrity
    - Section 4.1a: Exercise Library authority
    - Prompt caching for token optimization
    
    Args:
        message: User's message
        session: Session dict with state, mode, context
        
    Returns:
        str: Bill's response
    """
    
    # Initialize Claude client
    client = initialize_client()
    
    # Build system prompt (includes Bill instructions + client context)
    # Returns: list of dicts with cache_control OR single string (backward compatible)
    system_prompt = build_system_prompt(
        session,
        include_context=True,
        user_message=message
    )
    
    # Debug: Log system prompt structure
    if isinstance(system_prompt, list):
        print(f"[Claude] System prompt: {len(system_prompt)} blocks (structured for caching)")
        for i, block in enumerate(system_prompt):
            has_cache = 'cache_control' in block
            print(f"[Claude]   Block {i+1}: {'CACHED' if has_cache else 'not cached'}")
    else:
        print(f"[Claude] System prompt: single string (no caching)")
    
    # Build conversation history
    history = build_conversation_history(session)
    
    # Add current message
    current_messages = history + [{
        'role': 'user',
        'content': message
    }]
    
    print(f"[Claude] Sending message (conversation length: {len(current_messages)} messages)")
    
    try:
        # Call Claude API
        # system parameter accepts both string and list formats
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=system_prompt,  # Can be string or list
            messages=current_messages
        )
        
        # Extract text response
        bill_response = response.content[0].text
        
        # Log usage (including cache statistics)
        print(f"[Claude] Response received")
        print(f"[Claude] Input tokens: {response.usage.input_tokens}")
        print(f"[Claude] Output tokens: {response.usage.output_tokens}")
        
        # Log cache statistics if available
        if hasattr(response.usage, 'cache_creation_input_tokens'):
            print(f"[Claude] Cache creation tokens: {response.usage.cache_creation_input_tokens}")
        if hasattr(response.usage, 'cache_read_input_tokens'):
            print(f"[Claude] Cache read tokens: {response.usage.cache_read_input_tokens}")
        
        return bill_response
        
    except anthropic.APIError as e:
        print(f"[Claude] API Error: {str(e)}")
        raise
    except Exception as e:
        print(f"[Claude] Unexpected error: {str(e)}")
        raise


def chat_with_tools(message, session, max_tool_rounds=10):
    """
    Send message to Claude with tool definitions, execute any tool calls,
    and loop until Claude returns a final text response.

    Flow:
      1. Build system prompt + tool definitions
      2. Send to Claude with tools= parameter
      3. If response has tool_use blocks → execute webhooks → send tool_results back
      4. If write webhook → refresh client context
      5. Loop until Claude responds with text (or max rounds hit)

    Args:
        message: User's message
        session: Session dict with state, mode, context
        max_tool_rounds: Safety limit on tool-use loops

    Returns:
        str: Bill's final text response
    """
    client = initialize_client()

    system_prompt = build_system_prompt(
        session,
        include_context=True,
        user_message=message
    )

    # Load tool definitions from OpenAPI schema (strips _webhook_path before sending)
    raw_tools = get_claude_tools(enabled_only=True)
    tools = []
    for t in raw_tools:
        tools.append({
            'name': t['name'],
            'description': t['description'],
            'input_schema': t['input_schema'],
        })

    if isinstance(system_prompt, list):
        print(f"[Claude] System prompt: {len(system_prompt)} blocks (structured for caching)")
    else:
        print(f"[Claude] System prompt: single string (no caching)")
    print(f"[Claude] Tools loaded: {len(tools)} ({', '.join(t['name'] for t in tools)})")

    # Build conversation history + current message
    history = build_conversation_history(session)
    messages = history + [{'role': 'user', 'content': message}]

    for round_num in range(max_tool_rounds):
        print(f"[Claude] Round {round_num + 1} — sending {len(messages)} messages")

        try:
            response = client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=Config.CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )
        except anthropic.APIError as e:
            print(f"[Claude] API Error on round {round_num + 1}: {e}")
            raise

        # Log usage
        print(f"[Claude] Stop reason: {response.stop_reason}")
        print(f"[Claude] Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
        if hasattr(response.usage, 'cache_creation_input_tokens'):
            print(f"[Claude] Cache creation: {response.usage.cache_creation_input_tokens}")
        if hasattr(response.usage, 'cache_read_input_tokens'):
            print(f"[Claude] Cache read: {response.usage.cache_read_input_tokens}")

        # If Claude's done (no more tool calls), extract final text
        if response.stop_reason in ('end_turn', 'max_tokens'):
            text_parts = [block.text for block in response.content if block.type == 'text']
            if response.stop_reason == 'max_tokens':
                print(f"[Claude] WARNING: Response hit max_tokens limit — returning partial response")
            return '\n'.join(text_parts)

        # Process tool_use blocks
        if response.stop_reason == 'tool_use':
            # Append the full assistant response (text + tool_use blocks) to messages
            messages.append({'role': 'assistant', 'content': response.content})

            # Build tool_result blocks for each tool_use
            tool_results = []
            for block in response.content:
                if block.type != 'tool_use':
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                print(f"[Claude] Tool call: {tool_name}(keys={list(tool_input.keys())})")

                result = _execute_tool_call(tool_name, tool_input, session)

                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_use_id,
                    'content': json.dumps(result) if isinstance(result, dict) else str(result),
                })

            # Send tool results back as a user message
            messages.append({'role': 'user', 'content': tool_results})
            continue

        # Unexpected stop reason — return whatever text we got
        print(f"[Claude] Unexpected stop_reason: {response.stop_reason}")
        text_parts = [block.text for block in response.content if block.type == 'text']
        return '\n'.join(text_parts) if text_parts else "I ran into an issue processing that request."

    # Safety: max rounds exceeded
    print(f"[Claude] WARNING: max tool rounds ({max_tool_rounds}) exceeded")
    return "I've been working on that but hit a processing limit. Let me know if you'd like me to continue."


def _execute_tool_call(tool_name, tool_input, session):
    """
    Execute a single tool call by routing to the correct Make.com webhook.

    Handles:
    - Tool name → webhook URL resolution
    - Webhook execution
    - Post-write context refresh
    - Error wrapping (returns error dict so Claude can self-correct)

    Args:
        tool_name: OpenAPI operationId (e.g. 'populate_training_week')
        tool_input: Dict of parameters from Claude
        session: Current session dict

    Returns:
        dict: Webhook response or error dict
    """
    webhook_url = get_webhook_url_for_tool(tool_name)
    if not webhook_url:
        error = f"No webhook URL configured for tool '{tool_name}'"
        print(f"[Claude] {error}")
        return {'error': error}

    # Validate payload against schema (uses webhook key, not tool name)
    webhook_key = TOOL_TO_WEBHOOK_KEY.get(tool_name, tool_name)
    is_valid, validation_error = validate_webhook_payload(webhook_key, tool_input)
    if not is_valid:
        print(f"[Claude] Payload validation failed for '{tool_name}': {validation_error[:200]}")
        return {'error': f"Payload validation failed: {validation_error}"}

    try:
        result = execute_webhook(webhook_url, tool_input)
        print(f"[Claude] Tool '{tool_name}' executed successfully")
    except Exception as e:
        error = f"Webhook execution failed for '{tool_name}': {str(e)}"
        print(f"[Claude] {error}")
        return {'error': error}

    # Post-write context refresh (Section 2.1b)
    if should_refresh_context_after(webhook_key):
        try:
            print(f"[Claude] Write webhook '{webhook_key}' — refreshing context")
            client_context.refresh_context(session)
        except Exception as e:
            print(f"[Claude] WARNING: Context refresh failed after '{webhook_key}': {e}")
            # Don't fail the tool call — stale context is better than crashing

    return result


def generate_onboarding_response(message, session):
    """
    Generate response during client onboarding
    
    Focuses on:
    - Collecting profile information
    - Building motivation profile (Section 2.2)
    - Establishing communication preferences
    
    Args:
        message: User's message
        session: Session dict in ONBOARDING state
        
    Returns:
        str: Bill's response
    """
    
    # Use standard chat but with onboarding context
    return chat(message, session)


def generate_developer_response(message, session):
    """
    Generate response in developer mode
    
    Section 1.1A: Developer/Tech Mode
    - Precise, structured responses
    - Schema and automation focus
    - Access to developer-only operations
    
    Args:
        message: Developer's message
        session: Session dict with developer_authenticated=True
        
    Returns:
        str: Bill's response in tech mode
    """
    
    if not session.get('developer_authenticated'):
        return "Developer mode requires authentication. Use /developer-auth endpoint first."
    
    # Use standard chat but mode is already set to DEVELOPER
    return chat(message, session)