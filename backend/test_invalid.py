from webhooks.webhook_validator import validate_webhook_payload

payload = {
    'client_id': 'cli_test',
    'context': {
        'plan_id': 'plan_001',
        'block_id': 'block_001',
        'week_id': 'week_001',
        'week_number': 1
    },
    'sessions': [{
        'session_id': 'sess_001',
        # Missing session_summary!
        'steps': []
    }]
}

is_valid, error = validate_webhook_payload('populate_training_week', payload)
print(f'Invalid payload result: {is_valid}')
print(f'Error: {error}')