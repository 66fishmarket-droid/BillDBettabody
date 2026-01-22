"""
Bill D'Bettabody - Tool Definitions
Converts OpenAPI schema into Claude tool definitions for webhook calling
"""

import json
import os


# Core tools that Bill uses most frequently
# Injury/contraindication logging is critical - it's a key differentiator
ENABLED_TOOLS = {
    'check_client_id_available',
    'load_client_context', 
    'post_user_upsert',
    'generate_training_plan',
    'populate_training_week',
    'session_update',
    'post_contraindication_temp',       # Log temporary injuries
    'update_contraindication_temp',     # Update injury status (resolved, etc)
    'post_contraindication_chronic',    # Log chronic conditions
}


def load_openapi_schema(schema_path=None):
    """
    Load the OpenAPI schema from file
    
    Args:
        schema_path: Optional path to schema file. If None, uses default location.
        
    Returns:
        dict: Parsed OpenAPI schema
    """
    if schema_path is None:
        # Default: look in backend/schemas/ directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, 'schemas', 'bill_actions_openapi.json')
        
        # Normalize the path
        schema_path = os.path.normpath(schema_path)
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def convert_openapi_to_claude_tool(operation_id, operation_spec, path):
    """
    Convert a single OpenAPI operation into Claude tool format
    
    Args:
        operation_id: The operationId from OpenAPI spec
        operation_spec: The operation specification dict
        path: The webhook path/URL
        
    Returns:
        dict: Claude tool definition
    """
    
    # Extract request body schema
    request_body = operation_spec.get('requestBody', {})
    content = request_body.get('content', {})
    json_content = content.get('application/json', {})
    schema = json_content.get('schema', {})
    
    # Build Claude tool definition
    tool = {
        'name': operation_id,
        'description': operation_spec.get('summary', '') + '\n\n' + operation_spec.get('description', ''),
        'input_schema': {
            'type': 'object',
            'properties': schema.get('properties', {}),
            'required': schema.get('required', [])
        }
    }
    
    # Add webhook URL as metadata (we'll need this when executing)
    tool['_webhook_path'] = path
    
    return tool


def get_claude_tools(schema_path=None, enabled_only=True):
    """
    Get all Claude tool definitions from OpenAPI schema
    
    Args:
        schema_path: Optional path to OpenAPI schema file
        enabled_only: If True, only return tools in ENABLED_TOOLS set
        
    Returns:
        list: List of Claude tool definitions
    """
    
    schema = load_openapi_schema(schema_path)
    tools = []
    
    # Iterate through all paths and operations
    for path, path_spec in schema.get('paths', {}).items():
        for method, operation_spec in path_spec.items():
            if method.lower() != 'post':
                continue
                
            operation_id = operation_spec.get('operationId')
            if not operation_id:
                continue
            
            # Skip if not in enabled list
            if enabled_only and operation_id not in ENABLED_TOOLS:
                continue
            
            # Convert to Claude tool format
            tool = convert_openapi_to_claude_tool(operation_id, operation_spec, path)
            tools.append(tool)
    
    return tools


def get_webhook_url_for_tool(tool_name, base_url='https://hook.eu2.make.com'):
    """
    Get the full webhook URL for a given tool name
    
    Args:
        tool_name: Tool/operation name
        base_url: Base URL for webhooks
        
    Returns:
        str: Full webhook URL
    """
    
    tools = get_claude_tools(enabled_only=False)
    
    for tool in tools:
        if tool['name'] == tool_name:
            return base_url + tool['_webhook_path']
    
    return None


def describe_tools():
    """
    Print a human-readable description of available tools
    Useful for debugging
    """
    
    tools = get_claude_tools()
    
    print(f"\n{'='*60}")
    print(f"Available Claude Tools ({len(tools)} enabled)")
    print(f"{'='*60}\n")
    
    for tool in tools:
        print(f"Tool: {tool['name']}")
        print(f"Description: {tool['description'].split('\\n')[0][:80]}...")
        print(f"Required params: {tool['input_schema'].get('required', [])}")
        print(f"Webhook: {tool['_webhook_path']}")
        print()


if __name__ == '__main__':
    # When run directly, show available tools
    describe_tools()