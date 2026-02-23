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
        'session_summary': 'Right then, leg day. Heavy squats at RPE 8.',
        'steps': [{'step_order': 1, 'segment_type': 'warmup', 'sets': 1, 'reps': 1}]
    }]
}

is_valid, error = validate_webhook_payload('populate_training_week', payload)
print(f'Valid payload result: {is_valid}')
print(f'Error: {error}')