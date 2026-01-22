"""
Bill D'Bettabody - Backend Server
Main Flask API integrating Claude, Make.com, and Bill's canonical rules
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import get_config, Config
from core.bill_config import OperatingMode, ClientState
from core import claude_client
from models import client_context
from core.context_loader import get_greeting_for_state
from webhooks import webhook_handler
from webhooks.context_integrity import determine_required_webhook

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Load configuration
config = get_config()
app.config.from_object(config)

# Validate configuration on startup
try:
    Config.validate()
    print("[Server] Configuration validated successfully")
except ValueError as e:
    print(f"[Server] CONFIGURATION ERROR: {e}")
    print("[Server] Server will start but some features may not work")


# ============================================================
# HEALTH & STATUS
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'Bill D\'Bettabody Backend',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Detailed status check"""
    return jsonify({
        'status': 'ok',
        'claude_configured': bool(Config.ANTHROPIC_API_KEY),
        'webhooks_configured': sum(1 for v in Config.WEBHOOKS.values() if v),
        'active_sessions': len(client_context.sessions),
        'timestamp': datetime.now().isoformat()
    })


# ============================================================
# SESSION INITIALIZATION
# ============================================================

@app.route('/initialize', methods=['POST'])
def initialize():
    """
    Initialize a session for a client
    
    Three possible states:
    1. STRANGER - no client_id provided
    2. ONBOARDING - new client_id (doesn't exist in sheets)
    3. READY - existing client (full context loaded)
    
    Section 1.3: Interaction Entry & Identity Resolution
    """
    try:
        data = request.json or {}
        client_id = data.get('client_id', '').strip()
        
        # CASE 1: No client_id provided (stranger)
        if not client_id:
            session_id = client_context.create_stranger_session()
            greeting = get_greeting_for_state(ClientState.STRANGER)
            
            return jsonify({
                'status': 'stranger',
                'session_id': session_id,
                'greeting': greeting
            })
        
        # CASE 2 & 3: Check if client exists
        print(f"[Initialize] Checking if client exists: {client_id}")
        exists = webhook_handler.check_client_exists(client_id)
        
        if exists:
            # CASE 3: Existing client - load full context
            print(f"[Initialize] Client exists - loading context")
            context = webhook_handler.load_client_context(client_id)
            session_id, _ = client_context.initialize_session(client_id, context)
            greeting = get_greeting_for_state(ClientState.READY, context)
            
            return jsonify({
                'status': 'ready',
                'session_id': session_id,
                'greeting': greeting
            })
        else:
            # CASE 2: New client - onboarding mode
            print(f"[Initialize] New client - starting onboarding")
            session_id = client_context.create_stranger_session(client_id)
            
            # Update state to onboarding
            client_context.update_session_state(session_id, ClientState.ONBOARDING)
            
            greeting = get_greeting_for_state(
                ClientState.ONBOARDING, 
                {'client_id': client_id}
            )
            
            return jsonify({
                'status': 'onboarding',
                'session_id': session_id,
                'client_id': client_id,
                'greeting': greeting
            })
            
    except Exception as e:
        print(f"[Initialize] Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Something went wrong during initialization',
            'error': str(e)
        }), 500


# ============================================================
# MAIN CHAT ENDPOINT
# ============================================================

@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    
    Implements:
    - Section 0: Priority hierarchy
    - Section 1: Operating modes
    - Section 2.1b: Context integrity
    - Section 3.7: Auto-refresh after writes
    
    Expects: { "session_id": "...", "message": "..." }
    Returns: { "response": "..." }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id or not message:
            return jsonify({
                'error': 'Missing session_id or message'
            }), 400
        
        # Get session
        session = client_context.get_session(session_id)
        
        if not session:
            return jsonify({
                'error': 'Invalid session_id - please initialize first'
            }), 400
        
        print(f"[Chat] Session: {session_id}, State: {session['state']}, Mode: {session['mode']}")
        
        # Call Claude based on mode
        mode = session.get('mode', OperatingMode.COACH)
        
        if mode == OperatingMode.DEVELOPER:
            response = claude_client.generate_developer_response(message, session)
        elif session['state'] == ClientState.ONBOARDING:
            response = claude_client.generate_onboarding_response(message, session)
        else:
            response = claude_client.chat(message, session)
        
        # Add to conversation history
        client_context.add_message_to_conversation(session_id, message, response)
        
        return jsonify({
            'response': response,
            'session_id': session_id,
            'state': session['state'],
            'mode': session['mode']
        })
        
    except Exception as e:
        print(f"[Chat] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Something went wrong processing your message',
            'details': str(e)
        }), 500


# ============================================================
# DEVELOPER AUTHENTICATION
# ============================================================

@app.route('/developer-auth', methods=['POST'])
def developer_auth():
    """
    Authenticate developer for tech mode operations
    
    Section 1.1A + 3.6: Developer/Tech Mode authentication
    
    Expects: { "session_id": "...", "developer_key": "..." }
    Returns: { "authenticated": true/false }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        developer_key = data.get('developer_key')
        
        if not session_id or not developer_key:
            return jsonify({
                'error': 'Missing session_id or developer_key'
            }), 400
        
        # Get session
        session = client_context.get_session(session_id)
        
        if not session:
            return jsonify({
                'error': 'Invalid session_id'
            }), 400
        
        # Authenticate with Make.com
        authenticated = webhook_handler.authenticate_developer(developer_key)
        
        if authenticated:
            # Enable developer mode for this session
            client_context.set_developer_mode(session_id, authenticated=True)
            
            return jsonify({
                'authenticated': True,
                'message': 'Developer mode enabled',
                'session_id': session_id
            })
        else:
            return jsonify({
                'authenticated': False,
                'message': 'Invalid developer key'
            }), 401
            
    except Exception as e:
        print(f"[Developer Auth] Error: {str(e)}")
        return jsonify({
            'error': 'Authentication failed',
            'details': str(e)
        }), 500


# ============================================================
# CONTEXT MANAGEMENT
# ============================================================

@app.route('/refresh-context', methods=['POST'])
def refresh_context():
    """
    Manual context refresh (debugging)
    
    Section 2.1b: POST-ACTION CONTEXT REFRESH
    
    Expects: { "session_id": "..." }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        # Refresh context from Make.com
        client_context.refresh_context(session)
        
        return jsonify({
            'status': 'refreshed',
            'timestamp': session['last_refresh'],
            'client_id': session['client_id']
        })
        
    except Exception as e:
        print(f"[Refresh Context] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to refresh context',
            'details': str(e)
        }), 500


@app.route('/context-integrity-check', methods=['POST'])
def context_integrity_check():
    """
    Check context integrity state and get recommended webhook
    
    Section 3.7: Context Integrity Pre-Check
    Useful for debugging and understanding system state
    
    Expects: { "session_id": "..." }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        context = session.get('context', {})
        
        # Determine required webhook based on context state
        webhook_name, reasoning = determine_required_webhook(context, 'training')
        
        return jsonify({
            'session_id': session_id,
            'client_id': session['client_id'],
            'recommended_webhook': webhook_name,
            'reasoning': reasoning,
            'context_summary': {
                'has_sessions': len(context.get('sessions', {}).get('active', [])),
                'has_steps': len(context.get('steps', {}).get('active', []))
            }
        })
        
    except Exception as e:
        print(f"[Context Integrity Check] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to check context integrity',
            'details': str(e)
        }), 500


# ============================================================
# REST DAY SUMMARY GENERATION
# ============================================================

@app.route('/sessions/rest-day-summary', methods=['GET'])
def get_rest_day_summary():
    """
    Generate contextual rest day message when no session is scheduled
    
    This endpoint is called by the PWA when:
    - No session exists for today (rest day)
    - Client loads the dashboard
    
    Returns a 2-3 sentence message from Bill about rest, recovery, and nutrition.
    Uses Claude API to generate a contextual, personalized message based on:
    - Recent training load (from context)
    - Client goals
    - Nutrition targets
    - Active contraindications
    
    Query params:
        session_id: User's session identifier
    
    Returns:
        {
            "summary": "Rest day message from Bill",
            "client_id": "cli_xxx",
            "timestamp": "ISO datetime"
        }
    """
    try:
        session_id = request.args.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Missing session_id parameter'}), 400
        
        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        client_id = session.get('client_id')
        context = session.get('context', {})
        
        # Build a focused prompt for Claude
        profile = context.get('profile', {})
        nutrition = context.get('nutrition', {})
        contraindications = context.get('contraindications', {})
        
        # Count recent sessions for context
        recent_sessions = len(context.get('sessions', {}).get('active', []))
        
        prompt = f"""Generate a 2-3 sentence rest day message for this client.

CLIENT CONTEXT:
- Name: {profile.get('first_name', 'there')}
- Primary Goal: {profile.get('goal_primary', 'general fitness')}
- Recent sessions: {recent_sessions} scheduled this week
- Daily protein target: {nutrition.get('protein_min', 'adequate')}g
- Active injuries: {'Yes' if contraindications else 'None'}

TONE REQUIREMENTS:
- Use Bill's gruff-but-warm voice
- Frame rest as essential, not optional
- Reference protein intake
- Mention light movement if they're feeling restless
- Reassure that recovery is progress

Generate ONLY the 2-3 sentence message, nothing else."""

        # Call Claude to generate the message
        rest_message = claude_client.chat(prompt, session)
        
        return jsonify({
            'summary': rest_message,
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"[Rest Day Summary] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate rest day summary',
            'details': str(e)
        }), 500


# ============================================================
# SESSION CLEANUP
# ============================================================

@app.route('/cleanup-sessions', methods=['POST'])
def cleanup_sessions():
    """Clean up old sessions (admin endpoint)"""
    try:
        max_age_hours = request.json.get('max_age_hours', 24) if request.json else 24
        
        count = client_context.cleanup_old_sessions(max_age_hours)
        
        return jsonify({
            'status': 'ok',
            'sessions_cleaned': count
        })
        
    except Exception as e:
        print(f"[Cleanup] Error: {str(e)}")
        return jsonify({
            'error': 'Cleanup failed',
            'details': str(e)
        }), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            'GET /health',
            'GET /status',
            'POST /initialize',
            'POST /chat',
            'POST /developer-auth',
            'POST /refresh-context',
            'POST /context-integrity-check',
            'GET /sessions/rest-day-summary'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end'
    }), 500


# ============================================================
# STARTUP
# ============================================================

if __name__ == '__main__':
    port = Config.PORT
    debug = Config.FLASK_DEBUG
    
    print(f"\n{'='*60}")
    print(f"Bill D'Bettabody Backend Starting...")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Environment: {Config.FLASK_ENV}")
    print(f"Claude Model: {Config.CLAUDE_MODEL}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)