"""
Bill D'Bettabody - Webhook Payload Schemas
Defines exact structure expected by each Make.com scenario

These schemas are the CANONICAL source of truth for payload structure.
They override Claude's memory and catch errors before reaching Make.com.
"""

# ============================================================
# SCHEMA DEFINITIONS
# ============================================================

POPULATE_TRAINING_WEEK_SCHEMA = {
    "type": "object",
    "required": ["client_id", "context", "sessions"],
    "properties": {
        "client_id": {
            "type": "string",
            "minLength": 1,
            "description": "Client identifier (e.g., cli_demo)"
        },
        "context": {
            "type": "object",
            "required": ["plan_id", "block_id", "week_id", "week_number"],
            "properties": {
                "plan_id": {"type": "string", "minLength": 1},
                "block_id": {"type": "string", "minLength": 1},
                "week_id": {"type": "string", "minLength": 1},
                "week_number": {"type": "integer", "minimum": 1}
            },
            "additionalProperties": False
        },
        "sessions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["session_id", "session_summary", "steps"],
                "properties": {
                    "session_id": {"type": "string", "minLength": 1},
                    "session_summary": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 500,
                        "description": "2-3 sentence plain-language session intent from Bill"
                    },
                    "week": {"type": "integer"},
                    "day": {"type": "integer"},
                    "phase": {"type": "string"},
                    "location": {"type": "string"},
                    "focus": {"type": "string"},
                    "exercises": {"type": "string"},
                    "macros": {"type": "string"},
                    "supplements": {"type": "string"},
                    "notes": {"type": "string"},
                    "session_date": {"type": "string"},
                    "session_day_of_week": {"type": "string"},
                    "session_global_number": {"type": "integer"},
                    "intended_intensity_rpe": {"type": ["string", "integer"]},
                    "intended_hr_zone": {"type": "string"},
                    "estimated_duration_minutes": {"type": "integer"},
                    "linked_sport": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "step_order": {"type": "integer"},
                                "segment_type": {
                                    "type": "string",
                                    "enum": ["warmup", "main", "cooldown"]
                                },
                                "step_type": {"type": "string"},
                                "duration_type": {"type": "string"},
                                "duration_value": {"type": ["integer", "number"]},
                                "target_type": {"type": "string"},
                                "target_value": {"type": ["string", "number"]},
                                "exercise_name": {"type": "string"},
                                "sets": {"type": "integer", "minimum": 1},
                                "reps": {"type": "integer", "minimum": 1},
                                "load_kg": {"type": "number"},
                                "rest_seconds": {"type": "integer"},
                                "notes_coach": {"type": "string"},
                                "notes_athlete": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    },
    "additionalProperties": False
}


SESSION_UPDATE_SCHEMA = {
    "type": "object",
    "required": ["session_id"],
    "properties": {
        "client_id": {"type": "string"},
        "session_id": {"type": "string", "minLength": 1},
        "session_updates": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "focus": {"type": "string"},
                "exercises": {"type": "string"},
                "macros": {"type": "string"},
                "supplements": {"type": "string"},
                "notes": {"type": "string"},
                "session_status": {"type": "string"},
                "session_summary": {"type": "string", "maxLength": 500}
            },
            "additionalProperties": False
        },
        "steps_upsert": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["step_id"],
                "properties": {
                    "step_id": {"type": "string", "minLength": 1},
                    "step_order": {"type": "integer"},
                    "segment_type": {
                        "type": "string",
                        "enum": ["warmup", "main", "cooldown"]
                    },
                    "exercise_name": {"type": "string"},
                    "sets": {"type": "integer", "minimum": 1},
                    "reps": {"type": "integer", "minimum": 1},
                    "load_kg": {"type": "number"},
                    "rest_seconds": {"type": "integer"},
                    "notes_coach": {"type": "string"},
                    "notes_athlete": {"type": "string"}
                }
            }
        }
    },
    "additionalProperties": False
}


POST_USER_UPSERT_SCHEMA = {
    "type": "object",
    "required": ["client_id", "data"],
    "properties": {
        "client_id": {"type": "string", "minLength": 1},
        "data": {
            "type": "object",
            "required": ["chronic_contraindications"],
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string"},
                "chronic_contraindications": {"type": "string"},
                # Add other profile fields as needed
            }
        }
    },
    "additionalProperties": False
}


GENERATE_TRAINING_PLAN_SCHEMA = {
    "type": "object",
    "required": ["plan_action", "client", "plan"],
    "properties": {
        "plan_action": {
            "type": "string",
            "enum": ["create_full_block"]
        },
        "client": {
            "type": "object",
            "required": ["client_id"],
            "properties": {
                "client_id": {"type": "string", "minLength": 1}
            }
        },
        "plan": {
            "type": "object",
            "required": ["phase_name", "phase_goal", "week_start", "duration_weeks", "days_per_week"],
            "properties": {
                "plan_id": {"type": "string"},
                "phase_name": {"type": "string", "minLength": 1},
                "phase_goal": {"type": "string", "minLength": 1},
                "week_start": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "duration_weeks": {"type": "integer", "minimum": 1},
                "days_per_week": {"type": "integer", "minimum": 1, "maximum": 7},
                "constraints": {"type": "string"},
                "primary_locations": {"type": "string"},
                "nutrition_targets": {"type": "string"},
                "supplement_protocol": {"type": "string"},
                "notes": {"type": "string"}
            }
        }
    }
}


# ============================================================
# SCHEMA REGISTRY
# ============================================================

WEBHOOK_SCHEMAS = {
    'populate_training_week': POPULATE_TRAINING_WEEK_SCHEMA,
    'session_update': SESSION_UPDATE_SCHEMA,
    'post_user_upsert': POST_USER_UPSERT_SCHEMA,
    'full_training_block': GENERATE_TRAINING_PLAN_SCHEMA,
    # Add other webhooks as needed
}


# ============================================================
# CRITICAL FIELD CHECKS
# ============================================================

CRITICAL_FIELDS = {
    'populate_training_week': [
        ('session_summary', 'sessions[*]', 'Session intent message from Bill')
    ],
    'session_update': [
        ('session_summary', 'session_updates', 'Updated session intent (if changed)')
    ]
}