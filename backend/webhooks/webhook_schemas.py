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


CHECK_CLIENT_EXISTS_SCHEMA = {
    "type": "object",
    "required": ["client_id"],
    "properties": {
        "client_id": {
            "type": "string",
            "minLength": 1,
            "description": "Proposed client identifier to check, e.g. 'otter' or 'aragorn'"
        }
    }
}


LOAD_CLIENT_CONTEXT_SCHEMA = {
    "type": "object",
    "required": ["client_id"],
    "properties": {
        "client_id": {
            "type": "string",
            "minLength": 1,
            "description": "Client identifier (matched case-insensitively in Clients sheet)"
        }
    },
    "additionalProperties": False
}


POST_CONTRAINDICATION_TEMP_SCHEMA = {
    "type": "object",
    "required": ["client_id", "date_reported", "type", "description"],
    "properties": {
        "client_id": {"type": "string", "minLength": 1},
        "date_reported": {
            "type": "string",
            "description": "Date the injury/issue was reported (ISO format)"
        },
        "type": {
            "type": "string",
            "description": "Type of temporary issue, e.g. 'muscle strain', 'joint pain'"
        },
        "description": {
            "type": "string",
            "description": "Description of the injury/issue and affected area"
        },
        "expected_duration": {
            "type": "string",
            "description": "Expected recovery time, e.g. '7 days' or '2 weeks'"
        },
        "status": {
            "type": "string",
            "description": "Current status, e.g. 'active', 'monitoring'"
        },
        "notes": {"type": "string"},
        "date_resolved": {
            "type": "string",
            "description": "Date resolved (ISO format), if applicable"
        }
    }
}


POST_CONTRAINDICATION_CHRONIC_SCHEMA = {
    "type": "object",
    "required": [
        "client_id", "condition", "severity", "affected_system",
        "contraindicated_movements", "date_added", "last_reviewed", "status"
    ],
    "properties": {
        "client_id": {"type": "string", "minLength": 1},
        "condition": {
            "type": "string",
            "description": "Name of chronic condition, e.g. 'knee osteoarthritis'"
        },
        "severity": {
            "type": "string",
            "description": "Severity: 'mild', 'moderate', or 'severe'"
        },
        "affected_system": {
            "type": "string",
            "description": "Primary system affected, e.g. 'musculoskeletal', 'cardiovascular'"
        },
        "contraindicated_movements": {
            "type": "string",
            "description": "Movements to avoid or modify (comma-separated)"
        },
        "notes": {"type": "string"},
        "date_added": {
            "type": "string",
            "description": "Date condition was logged (ISO format)"
        },
        "last_reviewed": {
            "type": "string",
            "description": "Date last reviewed/confirmed (ISO format)"
        },
        "status": {
            "type": "string",
            "description": "Record status, usually 'active'"
        }
    }
}


UPDATE_CONTRAINDICATION_TEMP_SCHEMA = {
    "type": "object",
    "required": ["record_id", "client_id", "status"],
    "properties": {
        "record_id": {
            "type": "string",
            "minLength": 1,
            "description": "Row identifier from the initial log response, e.g. 'row_23'"
        },
        "client_id": {"type": "string", "minLength": 1},
        "status": {
            "type": "string",
            "description": "New status, e.g. 'resolved' or 'active'"
        },
        "expected_duration": {
            "type": "string",
            "description": "Updated expected duration"
        },
        "date_resolved": {
            "type": "string",
            "description": "Date resolved (ISO format)"
        },
        "notes": {"type": "string"}
    }
}


EXERCISE_FILTER_SCHEMA = {
    "type": "object",
    "required": ["focus_areas"],
    "properties": {
        "focus_areas": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "Lower_Pull", "Lower_Push",
                    "Upper_Pull", "Upper_Push",
                    "Core", "Cardio",
                    "Swimming", "Full_Body"
                ]
            },
            "description": "List of focus areas to filter exercises by"
        }
    }
}


ISSUE_LOG_UPDATER_SCHEMA = {
    "type": "object",
    "required": ["issue_type", "entity_type", "description"],
    "properties": {
        "client_id": {
            "type": "string",
            "description": "Optional. Defaults to 'no_client' if omitted"
        },
        "source": {
            "type": "string",
            "description": "Optional. Defaults to 'bill'"
        },
        "issue_type": {
            "type": "string",
            "description": "Issue category/type"
        },
        "entity_type": {
            "type": "string",
            "description": "What the issue relates to (e.g. scenario, schema, action, sheet)"
        },
        "entity_id": {"type": "string"},
        "description": {
            "type": "string",
            "description": "Human-readable issue description"
        },
        "context": {"type": "string"},
        "suggested_action": {"type": "string"},
        "priority": {"type": "string"},
        "status": {
            "type": "string",
            "description": "Optional. Defaults to 'open'"
        }
    },
    "additionalProperties": False
}


# ============================================================
# SCHEMA REGISTRY
# ============================================================

WEBHOOK_SCHEMAS = {
    # Training
    'populate_training_week': POPULATE_TRAINING_WEEK_SCHEMA,
    'session_update': SESSION_UPDATE_SCHEMA,
    'full_training_block': GENERATE_TRAINING_PLAN_SCHEMA,

    # Client management
    'check_client_exists': CHECK_CLIENT_EXISTS_SCHEMA,
    'load_client_context': LOAD_CLIENT_CONTEXT_SCHEMA,
    'post_user_upsert': POST_USER_UPSERT_SCHEMA,

    # Contraindications
    'add_injury': POST_CONTRAINDICATION_TEMP_SCHEMA,
    'add_chronic_condition': POST_CONTRAINDICATION_CHRONIC_SCHEMA,
    'update_injury_status': UPDATE_CONTRAINDICATION_TEMP_SCHEMA,

    # Exercise library
    'exercise_filter': EXERCISE_FILTER_SCHEMA,

    # Admin
    'issue_log_updater': ISSUE_LOG_UPDATER_SCHEMA,
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
    ],
    'add_injury': [
        ('description', 'root', 'Description of the injury/issue and affected area')
    ],
    'add_chronic_condition': [
        ('contraindicated_movements', 'root', 'Movements to avoid or modify')
    ],
}