"""
Bill D'Bettabody - Claude API Client (WITH TOOL CALLING)
Handles all interactions with Claude API
Implements Bill's persona, priority hierarchy, and context management
NOW WITH: Webhook execution via Claude's native tool calling
"""

import anthropic
import json
from config import Config
from core.context_loader import build_system_prompt
from core.tool_definitions import get_claude_tools, get_webhook_url_for_tool
from webhooks import webhook_handler


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


def execute_tool_call(tool_name, tool_input):
    """
    Execute a webhook tool call
    
    Args:
        tool_name: Name of the tool (e.g., 'populate_training_week')
        tool_input: Tool input parameters as dict
        
    Returns:
        dict: Webhook response
    """
    print(f"[Tool] Executing: {tool_name}")
    print(f"[Tool] Input keys: {list(tool_input.keys())}")
    
    # Get the webhook URL for this tool
    webhook_url = get_webhook_url_for_tool(tool_name)
    
    if not webhook_url:
        error_msg = f"No webhook URL found for tool: {tool_name}"
        print(f"[Tool] ERROR: {error_msg}")
        return {"error": error_msg}
    
    print(f"[Tool] Webhook URL: {webhook_url}")
    
    try:
        # Execute the webhook using webhook_handler
        response = webhook_handler.execute_webhook(webhook_url, tool_input)
        
        print(f"[Tool] Success: {tool_name}")
        
        return response
        
    except Exception as e:
        error_msg = f"Webhook execution failed: {str(e)}"
        print(f"[Tool] ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg, "details": str(e)}


def chat(message, session):
    """
    Send message to Claude and get Bill's response
    NOW WITH TOOL CALLING SUPPORT
    
    This function handles the full tool use loop:
    1. Send message to Claude with available tools
    2. If Claude wants to use a tool, execute it
    3. Send tool results back to Claude
    4. Repeat until Claude gives a text response
    
    Implements:
    - Section 0: Priority hierarchy
    - Section 1: Operating modes and persona
    - Section 2.1b: Context integrity
    - Section 3.7: Auto-refresh after writes
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
    system_prompt = build_system_prompt(
        session,
        include_context=True,
        user_message=message
    )
    
    # Load available tools
    tools = get_claude_tools()
    
    # Remove the _webhook_path metadata before sending to Claude
    # (Claude doesn't need to see internal metadata)
    claude_tools = []
    for tool in tools:
        clean_tool = {
            'name': tool['name'],
            'description': tool['description'],
            'input_schema': tool['input_schema']
        }
        claude_tools.append(clean_tool)
    
    # Build conversation history
    history = build_conversation_history(session)
    
    # Add current message
    messages = history + [{
        'role': 'user',
        'content': message
    }]
    
    # Track if we've made any write operations (for context refresh)
    made_write_operation = False
    
    # Tool use loop - keep going until we get a text response
    max_iterations = 10  # Safety limit to prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        print(f"[Claude] Iteration {iteration}: Calling API...")
        print(f"[Claude] Messages in conversation: {len(messages)}")
        
        try:
            # Call Claude API with tools
            response = client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=Config.CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
                tools=claude_tools
            )
            
            # Log usage
            print(f"[Claude] Input tokens: {response.usage.input_tokens}")
            print(f"[Claude] Output tokens: {response.usage.output_tokens}")
            
            # Check stop reason
            stop_reason = response.stop_reason
            print(f"[Claude] Stop reason: {stop_reason}")
            
            # Process response content
            if stop_reason == "tool_use":
                # Claude wants to use a tool
                tool_results = []
                
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input
                        tool_use_id = content_block.id
                        
                        print(f"[Claude] Wants to use tool: {tool_name}")
                        
                        # Execute the tool
                        tool_result = execute_tool_call(tool_name, tool_input)
                        
                        # Check if this is a write operation
                        write_tools = {
                            'post_user_upsert',
                            'generate_training_plan', 
                            'populate_training_week',
                            'session_update',
                            'post_contraindication_temp',
                            'update_contraindication_temp',
                            'post_contraindication_chronic'
                        }
                        if tool_name in write_tools:
                            made_write_operation = True
                            print(f"[Claude] Write operation detected: {tool_name}")
                        
                        # Add tool result to list
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(tool_result)
                        })
                
                # Add assistant's tool use to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Add tool results to conversation
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue loop to get Claude's response to the tool results
                continue
                
            elif stop_reason == "end_turn":
                # Claude is done - extract text response
                bill_response = ""
                
                for content_block in response.content:
                    if content_block.type == "text":
                        bill_response += content_block.text
                
                # If we made write operations, refresh context
                if made_write_operation:
                    print("[Claude] Write operation completed - context should be refreshed")
                    # Note: Context refresh is handled by server.py after this function returns
                
                return bill_response
                
            else:
                # Unexpected stop reason
                print(f"[Claude] WARNING: Unexpected stop reason: {stop_reason}")
                
                # Try to extract any text we can
                bill_response = ""
                for content_block in response.content:
                    if content_block.type == "text":
                        bill_response += content_block.text
                
                if bill_response:
                    return bill_response
                else:
                    return "I encountered an unexpected issue. Please try again."
        
        except anthropic.APIError as e:
            print(f"[Claude] API Error: {str(e)}")
            raise
        except Exception as e:
            print(f"[Claude] Unexpected error: {str(e)}")
            raise
    
    # If we hit max iterations, return a helpful message
    print(f"[Claude] WARNING: Hit max iterations ({max_iterations})")
    return "I'm having trouble completing that request. The operation may have succeeded, but I lost track of the conversation. Please check if your request was completed, or try asking again."


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
    
    # Use standard chat - tools are available during onboarding too
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
    
    # Use standard chat - tools are available in developer mode
    return chat(message, session)