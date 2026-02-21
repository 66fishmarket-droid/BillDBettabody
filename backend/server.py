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
from core.sheets_client import get_dashboard_data, get_session_detail, get_progress_data
from core.sheets_writer import update_steps_actuals
from models import client_context
from core.context_loader import get_greeting_for_state
from webhooks import webhook_handler
from webhooks.context_integrity import determine_required_webhook, should_refresh_context_after

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
            # Use tool-aware chat so Bill can call Make.com webhooks
            response = claude_client.chat_with_tools(message, session)
        
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
# DASHBOARD
# ============================================================

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Home screen data for the PWA.

    Reads directly from Google Sheets (no Make.com):
      - Next upcoming session (date, focus, summary, duration)
      - PBs for exercises in that session (so user can see what to beat)
      - PBs set in the last 7 days
      - Current block/week summary for the progress card

    Query params:
        session_id: Active session identifier (from /initialize)

    Returns:
        {
            "next_session": { session_id, session_date, day_of_week, focus,
                              session_summary, location, estimated_duration,
                              phase_name, week_number, exercise_count },
            "session_exercise_bests": [ { exercise_name, metric_key,
                                          current_value, current_unit,
                                          current_timestamp, strength_e1rm_kg,
                                          strength_load_kg, strength_reps,
                                          session_count }, ... ],
            "recent_pbs": [ same shape as above ],
            "block_summary": { phase_name, week_number, block_id }
        }
    """
    try:
        session_id = request.args.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id parameter'}), 400

        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id — please initialize first'}), 400

        client_id = session.get('client_id')
        if not client_id:
            return jsonify({'error': 'No client_id in session — onboarding not complete'}), 400

        data = get_dashboard_data(client_id)

        return jsonify(data)

    except RuntimeError as e:
        # Config/connection errors (missing env var, wrong sheet name, etc.)
        print(f"[Dashboard] Config error: {str(e)}")
        return jsonify({
            'error': 'Google Sheets connection failed',
            'details': str(e)
        }), 503

    except Exception as e:
        print(f"[Dashboard] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to load dashboard data',
            'details': str(e)
        }), 500


# ============================================================
# PROGRESS
# ============================================================

@app.route('/progress', methods=['GET'])
def progress():
    """
    Progress and history data for the progress screen.

    Reads four sheets: Exercise_Bests, Exercise_Library,
    Plans_Sessions (completed), Plans_Steps (actuals).

    Returns exercises grouped by training category with
    first / best / recent values and % improvement.
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing session_id parameter'}), 400

        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id — please initialize first'}), 400

        client_id = session.get('client_id')
        if not client_id:
            return jsonify({'error': 'No client_id in session'}), 400

        data = get_progress_data(client_id)
        return jsonify(data)

    except RuntimeError as e:
        print(f"[Progress] Config error: {str(e)}")
        return jsonify({'error': 'Google Sheets connection failed', 'details': str(e)}), 503
    except Exception as e:
        print(f"[Progress] Error: {str(e)}")
        return jsonify({'error': 'Failed to load progress data', 'details': str(e)}), 500


# ============================================================
# PROFILE
# ============================================================

@app.route('/profile', methods=['GET'])
def profile():
    """
    Return client profile for the active Bill session.

    Query params:
        session_id: Bill session identifier (from /initialize)
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'Missing session_id parameter'}), 400

        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id — please initialize first'}), 400

        client_id = session.get('client_id')
        if not client_id:
            return jsonify({'error': 'No client_id in session — onboarding not complete'}), 400

        context = session.get('context', {})
        profile = context.get('client_profile') if context else None

        # If no profile loaded yet, fetch context now
        if not profile:
            context = webhook_handler.load_client_context(client_id)
            session['context'] = context
            session['last_refresh'] = datetime.now().isoformat()
            profile = context.get('client_profile', {})

        return jsonify(profile or {})

    except Exception as e:
        print(f"[Profile] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to load profile',
            'details': str(e)
        }), 500


# ============================================================
# SESSION DETAIL + COMPLETION
# ============================================================

def _resolve_client_id_from_bill_session():
    """
    Resolve client_id from the active Bill session (from query/body).
    Returns (client_id, session_obj, error_response_tuple_or_None).
    """
    bill_session_id = request.args.get('session_id') or request.args.get('bill_session_id')
    if request.is_json:
        data = request.json or {}
        bill_session_id = bill_session_id or data.get('bill_session_id') or data.get('session_id')

    if not bill_session_id:
        return None, None, None

    session = client_context.get_session(bill_session_id)
    if not session:
        return None, None, (jsonify({'error': 'Invalid Bill session_id — please initialize first'}), 400)

    client_id = session.get('client_id')
    if not client_id:
        return None, session, (jsonify({'error': 'No client_id in session — onboarding not complete'}), 400)

    return client_id, session, None


@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """
    Return full session details for the session view screen.

    Query params:
        session_id or bill_session_id: Bill session id (from /initialize)
        client_id (optional): direct client_id override
    """
    try:
        client_id = request.args.get('client_id')
        bill_client_id, bill_session, bill_error = _resolve_client_id_from_bill_session()
        if bill_error:
            return bill_error

        if not client_id:
            client_id = bill_client_id

        if not client_id:
            return jsonify({'error': 'Missing client_id or Bill session_id'}), 400

        data = get_session_detail(client_id, session_id)

        if not data.get('session'):
            return jsonify({'error': 'Session not found'}), 404

        return jsonify(data)

    except RuntimeError as e:
        print(f"[Session Detail] Config error: {str(e)}")
        return jsonify({
            'error': 'Google Sheets connection failed',
            'details': str(e)
        }), 503

    except Exception as e:
        print(f"[Session Detail] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to load session detail',
            'details': str(e)
        }), 500


@app.route('/session/<session_id>/complete', methods=['POST'])
def complete_session(session_id):
    """
    Log session completion and update steps.

    Body:
      - client_id (optional if bill_session_id provided)
      - session_updates (optional)
      - steps_upsert OR steps (optional, mapped to steps_upsert)
    """
    try:
        data = request.json or {}

        client_id = data.get('client_id')
        bill_client_id, bill_session, bill_error = _resolve_client_id_from_bill_session()
        if bill_error:
            return bill_error

        if not client_id:
            client_id = bill_client_id

        if not client_id:
            return jsonify({'error': 'Missing client_id or Bill session_id'}), 400

        # Build steps_upsert payload
        steps_upsert = data.get('steps_upsert')
        if steps_upsert is None:
            steps = data.get('steps', [])
            steps_upsert = []
            allowed_fields = {
                'step_id', 'step_order', 'segment_type', 'step_type',
                'duration_type', 'duration_value', 'target_type', 'target_value',
                'exercise_name', 'sets', 'reps', 'load_kg', 'rest_seconds',
                'notes_coach', 'notes_athlete', 'status',
                'pattern_type', 'load_start_kg', 'load_increment_kg', 'load_peak_kg',
                'reps_pattern', 'rpe_pattern', 'tempo_pattern', 'tempo_per_set_pattern',
                'pattern_notes', 'interval_count', 'interval_work_sec',
                'interval_rest_sec', 'intensity_start', 'intensity_end'
            }
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_id = step.get('step_id')
                if not step_id:
                    continue
                mapped = {k: v for k, v in step.items() if k in allowed_fields}
                mapped['step_id'] = step_id
                steps_upsert.append(mapped)

        # Build session_updates (if provided or derivable)
        session_updates = data.get('session_updates')
        if session_updates is None:
            session_updates = {}
            for key in ['location', 'focus', 'exercises', 'macros', 'supplements', 'notes', 'session_status', 'session_summary']:
                if key in data:
                    session_updates[key] = data.get(key)
            if not session_updates:
                session_updates = None

        # Build step updates for Sheets writer
        if not steps_upsert:
            return jsonify({'error': 'No step updates provided'}), 400

        # Write actuals directly to Plans_Steps
        write_result = update_steps_actuals(
            steps_upsert,
            status='completed',
            completed_timestamp=datetime.utcnow().isoformat()
        )

        # Post-write context refresh
        if should_refresh_context_after('session_update') and bill_session:
            try:
                client_context.refresh_context(bill_session)
            except Exception as e:
                print(f"[Session Complete] WARNING: Context refresh failed: {e}")

        return jsonify({
            'status': 'ok',
            'session_id': session_id,
            'steps_updated': write_result.get('updated'),
            'steps_missing': write_result.get('missing'),
            'timestamp': datetime.now().isoformat()
        })

    except ValueError as e:
        # Validation errors from validate_or_raise
        return jsonify({'error': 'Invalid payload', 'details': str(e)}), 400

    except Exception as e:
        print(f"[Session Complete] Error: {str(e)}")
        return jsonify({
            'error': 'Failed to complete session',
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
        
        # Build a focused prompt for Claude (V2 uses 'client_profile', V1 used 'profile')
        profile = context.get('client_profile', context.get('profile', {}))
        nutrition = context.get('nutrition', {})
        contraindications = context.get('contraindications', context.get('Contraindications Temp', {}))

        # nutrition_targets may be a nested JSON string from Make.com — parse it safely
        _nt = nutrition.get('nutrition_targets', {})
        if isinstance(_nt, str):
            try:
                import json as _json
                _nt = _json.loads(_nt)
            except Exception:
                _nt = {}
        protein_target = _nt.get('protein', nutrition.get('protein_min', 'adequate'))

        # Count recent sessions for context
        sessions_field = context.get('sessions', {})
        if isinstance(sessions_field, dict):
            recent_sessions = len(sessions_field.get('active', []))
        else:
            recent_sessions = 0

        prompt = f"""Generate a 2-3 sentence rest day message for this client.

CLIENT CONTEXT:
- Name: {profile.get('first_name', 'there') if isinstance(profile, dict) else 'there'}
- Primary Goal: {profile.get('goal_primary', 'general fitness') if isinstance(profile, dict) else 'general fitness'}
- Recent sessions: {recent_sessions} scheduled this week
- Daily protein target: {protein_target}g
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
        import traceback
        print(f"[Rest Day Summary] Error: {str(e)}")
        print(traceback.format_exc())
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
            'GET /profile?session_id=...',
            'GET /dashboard?session_id=...',
            'GET /session/<session_id>?session_id=...',
            'POST /session/<session_id>/complete',
            'POST /refresh-context',
            'POST /context-integrity-check',
            'GET /sessions/rest-day-summary?session_id=...'
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
