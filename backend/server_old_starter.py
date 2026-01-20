"""
Bill D'Bettabody - Backend Server
Flask API for Claude-powered fitness coaching
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules (we'll create these next)
import client_context
import webhook_handler
import claude_client

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Allow frontend to connect

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Check if server is running"""
    return jsonify({
        'status': 'ok',
        'service': 'Bill D\'Bettabody Backend',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/initialize', methods=['POST'])
def initialize():
    """
    Initialize a session for a client
    Three possible states:
    1. STRANGER - no client_id provided
    2. ONBOARDING - new client_id (doesn't exist in sheets)
    3. READY - existing client (full context loaded)
    """
    try:
        client_id = request.json.get('client_id', None)
        
        # CASE 1: No client_id provided (stranger)
        if not client_id or client_id.strip() == '':
            return jsonify({
                'status': 'stranger',
                'greeting': "Right then, I don't know you yet. If you're here to set up, give yourself a memorable client ID - your favourite animal, a book character, whatever sticks in your head. Something like 'cli_sherlock' or 'cli_tigger'. What'll it be?"
            })
        
        # CASE 2 & 3: Check if client exists
        exists = webhook_handler.check_client_exists(client_id)
        
        if exists:
            # CASE 3: Existing client - load full context
            session_id, context = client_context.initialize_session(client_id)
            first_name = context.get('first_name', 'there')
            
            return jsonify({
                'status': 'ready',
                'session_id': session_id,
                'greeting': f"Right then, {first_name}, what's the plan today?"
            })
        else:
            # CASE 2: New client - onboarding mode
            session_id = client_context.create_stranger_session(client_id)
            
            return jsonify({
                'status': 'onboarding',
                'session_id': session_id,
                'client_id': client_id,
                'greeting': f"Right then, {client_id} it is. Let's get you set up properly. First things first - what's your actual name?"
            })
            
    except Exception as e:
        print(f"Error in /initialize: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Something went wrong during initialization'
        }), 500


@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    Expects: { "session_id": "...", "message": "..." }
    Returns: { "response": "..." }
    """
    try:
        session_id = request.json.get('session_id')
        message = request.json.get('message')
        
        if not session_id or not message:
            return jsonify({
                'error': 'Missing session_id or message'
            }), 400
        
        # Get session (context already loaded)
        session = client_context.get_session(session_id)
        
        if not session:
            return jsonify({
                'error': 'Invalid session_id - please initialize first'
            }), 400
        
        # Call Claude with full context
        response = claude_client.chat(message, session)
        
        # Update conversation history
        session['conversation'].append({
            'user': message,
            'bill': response,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'response': response,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"Error in /chat: {str(e)}")
        return jsonify({
            'error': 'Something went wrong processing your message'
        }), 500


@app.route('/refresh-context', methods=['POST'])
def refresh_context():
    """
    Manual context refresh (useful for debugging)
    Expects: { "session_id": "..." }
    """
    try:
        session_id = request.json.get('session_id')
        
        session = client_context.get_session(session_id)
        if not session:
            return jsonify({'error': 'Invalid session_id'}), 400
        
        # Refresh context from Make.com
        client_context.refresh_context(session)
        
        return jsonify({
            'status': 'refreshed',
            'timestamp': session['last_refresh'].isoformat()
        })
        
    except Exception as e:
        print(f"Error in /refresh-context: {str(e)}")
        return jsonify({'error': 'Failed to refresh context'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    print(f"\n{'='*50}")
    print(f"Bill D'Bettabody Backend Starting...")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"{'='*50}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)