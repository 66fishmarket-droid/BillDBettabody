"""
Bill D'Bettabody - Claude API Client
Handles all interactions with Claude API
Implements Bill's persona, priority hierarchy, and context management
"""

import anthropic
from config import Config
from core.context_loader import build_system_prompt


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
    
    Implements:
    - Section 0: Priority hierarchy
    - Section 1: Operating modes and persona
    - Section 2.1b: Context integrity
    - Section 4.1a: Exercise Library authority
    
    Args:
        message: User's message
        session: Session dict with state, mode, context
        
    Returns:
        str: Bill's response
    """
    
    # Initialize Claude client
    client = initialize_client()
    
    # Build system prompt (includes Bill instructions + client context)
    # Pass user_message for smart exercise library loading
    system_prompt = build_system_prompt(
        session,
        include_context=True,
        user_message=message  # ← Added this
    )
    
    # Build conversation history
    history = build_conversation_history(session)
    
    # Add current message
    current_messages = history + [{
        'role': 'user',
        'content': message
    }]
    
    # Log token estimate
    print(f"[Claude] Sending message (conversation length: {len(current_messages)} messages)")
    
    try:
        # Call Claude API
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=current_messages
        )
        
        # Extract text response
        bill_response = response.content[0].text
        
        # Log usage
        print(f"[Claude] Response received")
        print(f"[Claude] Input tokens: {response.usage.input_tokens}")
        print(f"[Claude] Output tokens: {response.usage.output_tokens}")
        
        return bill_response
        
    except anthropic.APIError as e:
        print(f"[Claude] API Error: {str(e)}")
        raise
    except Exception as e:
        print(f"[Claude] Unexpected error: {str(e)}")
        raise

def chat_with_webhook_awareness(message, session):
    """
    Enhanced chat that can detect and execute webhook requests
    
    This is where Bill's responses might trigger Make.com webhooks.
    For V1, we keep it simple - Bill explicitly states when he needs
    to call a webhook, and we parse that intent.
    
    Args:
        message: User's message
        session: Session dict
        
    Returns:
        str: Bill's response (may include webhook execution results)
    """
    
    # Get initial response from Claude
    response = chat(message, session)
    
    # TODO: Parse response for webhook intent
    # For now, just return the response
    # Later we'll add webhook parsing and execution
    
    return response


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