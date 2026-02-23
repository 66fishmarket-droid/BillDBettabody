"""
Bill D'Bettabody - Context Loader (WITH PROMPT CACHING)
Selective instruction loading to optimize token usage
NOW WITH: Structured system messages for Claude's prompt caching

PROMPT CACHING STRATEGY:
- Bill's instructions + scenario index are CACHED (stable)
- Scenario group files are CACHED per operation type
- Client context is NOT cached (changes frequently)
- Cache TTL: 5 minutes (refreshed with each request)
- Expected savings: 90% reduction on cached portions after first request

SCENARIO LOADING STRATEGY:
- scenario_index.txt is always loaded (slim, ~2KB)
- Scenario group files are pre-loaded based on operation_type
  onboarding → user_upsert, user_id_check, add_injury, update_injury,
               add_chronic_condition, sync_contraindications_webhook
  planning   → full_training_block_generator, exercise_filter,
               populate_training_week, session_update
  session    → load_client_context, session_update
- Full scenario files can be loaded on demand via load_scenario(name)

Cache invalidation: Different operation types create separate caches.
"""

import os
from datetime import datetime
from config import Config
from core.bill_config import OperatingMode, ClientState

# Scenario groups — maps operation_type to list of scenario file names (without .txt)
SCENARIO_GROUPS = {
    'onboarding': [
        '01_user_upsert',
        '04_user_id_check',
        '10_add_injury',
        '11_update_injury_status',
        '12_add_chronic_condition',
        '02_sync_contraindications_webhook',
    ],
    'planning': [
        '09_full_training_block_generator',
        '08_exercise_filter',
        '06_populate_training_week',
        '07_session_update',
    ],
    'session': [
        '05_load_client_context',
        '07_session_update',
    ],
}


def load_section_from_file(filepath, section_id=None):
    """
    Load a section from Bill Instructions file
    
    Args:
        filepath: Path to instruction file
        section_id: Optional section identifier (e.g., '0', '1', '2.1')
        
    Returns:
        str: Section content or full file if section_id is None
    """
    if not os.path.exists(filepath):
        print(f"[Context Loader] WARNING: File not found: {filepath}")
        return ""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if section_id is None:
            return content
        
        # Simple section extraction (can be enhanced)
        # For now, return full file - we'll optimize this later
        return content
        
    except Exception as e:
        print(f"[Context Loader] Error loading file: {str(e)}")
        return ""


def load_scenario_index():
    """
    Load the slim scenario index. Always included in Bill's cached context.
    Tells Bill what scenarios exist, their URLs, and when to call them.

    Returns:
        str: Scenario index content (~2KB)
    """
    return load_section_from_file(Config.SCENARIO_INDEX_PATH)


def load_scenario(scenario_name):
    """
    Load a single scenario file by name (without .txt extension).

    Args:
        scenario_name: e.g. '01_user_upsert' or 'user_upsert'

    Returns:
        str: Full scenario instructions, or empty string if not found
    """
    # Allow bare names like 'user_upsert' by checking for numeric prefix
    if not scenario_name[0].isdigit():
        # Search the scenarios dir for a file ending in _{scenario_name}.txt
        try:
            for fname in os.listdir(Config.SCENARIOS_DIR):
                if fname.endswith(f'_{scenario_name}.txt'):
                    scenario_name = fname[:-4]  # strip .txt
                    break
        except OSError:
            pass

    filepath = os.path.join(Config.SCENARIOS_DIR, f'{scenario_name}.txt')
    content = load_section_from_file(filepath)
    if content:
        print(f"[Context Loader] Loaded scenario: {scenario_name}")
    return content


def load_scenario_group(operation_type):
    """
    Load all scenario files for a given operation type group.
    Used to pre-load relevant scenarios into Bill's cached context.

    Args:
        operation_type: 'onboarding', 'planning', or 'session'

    Returns:
        str: Concatenated scenario file contents, or empty string
    """
    names = SCENARIO_GROUPS.get(operation_type, [])
    if not names:
        return ""

    parts = []
    parts.append("=" * 60)
    parts.append(f"SCENARIO CONTRACTS — {operation_type.upper()} GROUP")
    parts.append("=" * 60)
    parts.append("")

    for name in names:
        content = load_scenario(name)
        if content:
            parts.append(content)
            parts.append("")

    loaded = sum(1 for n in names if os.path.exists(
        os.path.join(Config.SCENARIOS_DIR, f'{n}.txt')))
    print(f"[Context Loader] Scenario group '{operation_type}': {loaded}/{len(names)} files loaded")
    return "\n".join(parts)


def load_bill_core_instructions():
    """
    Load core Bill instructions (always loaded)

    Includes:
    - Section 0: Priority order & core principles
    - Section 1: Operating modes, identity, safety

    Returns:
        str: Core instruction content
    """
    filepath = Config.BILL_INSTRUCTIONS_PATH
    return load_section_from_file(filepath)


def load_bill_calculations():
    """
    Load Bill's calculations reference (always loaded alongside core instructions).
    Contains e1RM formulas, protein/calorie targets, VO2max, RPE/RIR tables, etc.

    Returns:
        str: Calculations reference content, or empty string if not found
    """
    filepath = Config.BILL_CALCULATIONS_PATH
    content = load_section_from_file(filepath)
    if content:
        print(f"[Context Loader] Loaded calculations reference: ~{len(content)} chars")
    else:
        print(f"[Context Loader] WARNING: Calculations reference not found at {filepath}")
    return content


def load_bill_instructions(mode, client_state, operation_type='chat'):
    """
    Load Bill instructions selectively based on context.

    Always includes:
    - Core Bill instructions (Bill_Instructions_V2.txt)
    - Scenario index (slim ~2KB — tells Bill what webhooks exist and when to call them)

    Pre-loads scenario group files when operation_type matches a known group:
    - 'onboarding' → client mgmt + contraindication scenarios
    - 'planning'   → training block + exercise filter + population scenarios
    - 'session'    → load context + session update scenarios

    Exercise library is NOT loaded here — it lives in Google Sheets and is
    delivered via the exercise_filter webhook at plan-generation time.

    Args:
        mode: OperatingMode value ('coach', 'tech', 'developer')
        client_state: ClientState value ('stranger', 'onboarding', 'ready')
        operation_type: 'chat', 'onboarding', 'planning', 'session'

    Returns:
        str: Assembled instruction text
    """

    instructions_parts = []

    # ALWAYS: Core identity and rules
    instructions_parts.append("=" * 60)
    instructions_parts.append("BILL D'BETTABODY - CORE INSTRUCTIONS")
    instructions_parts.append("=" * 60)
    instructions_parts.append("")

    core_instructions = load_bill_core_instructions()
    if core_instructions:
        instructions_parts.append(core_instructions)

    # ALWAYS: Calculations reference (companion to V2 instructions)
    calculations = load_bill_calculations()
    if calculations:
        instructions_parts.append("")
        instructions_parts.append("=" * 60)
        instructions_parts.append("CALCULATIONS REFERENCE")
        instructions_parts.append("=" * 60)
        instructions_parts.append("")
        instructions_parts.append(calculations)

    # Mode/state/operation header
    instructions_parts.append("")
    instructions_parts.append("=" * 60)
    instructions_parts.append(f"CURRENT OPERATING MODE: {mode.upper()}")
    instructions_parts.append(f"CLIENT STATE: {client_state.upper()}")
    instructions_parts.append(f"OPERATION TYPE: {operation_type.upper()}")
    instructions_parts.append("=" * 60)
    instructions_parts.append("")

    # ALWAYS: Scenario index (Bill needs to know what webhooks exist)
    instructions_parts.append("=" * 60)
    instructions_parts.append("SCENARIO INDEX (load full file before calling any webhook)")
    instructions_parts.append("=" * 60)
    instructions_parts.append("")
    scenario_index = load_scenario_index()
    if scenario_index:
        instructions_parts.append(scenario_index)
    else:
        instructions_parts.append("WARNING: Scenario index not loaded — webhook calls may fail.")
    instructions_parts.append("")

    # CONDITIONAL: Pre-load scenario group files for the operation type
    if operation_type in SCENARIO_GROUPS:
        scenario_group = load_scenario_group(operation_type)
        if scenario_group:
            instructions_parts.append(scenario_group)

    return "\n".join(instructions_parts)


def build_client_context_text(session):
    """
    Build client context section as text for Claude's system prompt.

    Formats the Load Client Context V2 webhook output into readable text.
    The V2 response uses numeric keys (from Make.com data stores) for
    sessions, steps, and exercise bests arrays.

    This is separated from instructions so it can be:
    - NOT cached (changes frequently)
    - Kept separate in the system message array

    Args:
        session: Session dict with context, state, etc.

    Returns:
        str: Client context text (or empty string if not applicable)
    """
    state = session.get('state', ClientState.STRANGER)

    if state != ClientState.READY:
        return ""

    context = session.get('context', {})
    if not context:
        return ""

    parts = []

    # CRITICAL: Always inject today's date so Bill calculates session_dates correctly.
    # Without this, Bill uses stale/hallucinated dates when calling populate_training_week.
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    parts.append("=" * 60)
    parts.append(f"TODAY'S DATE: {today_str}  ← USE THIS FOR ALL DATE CALCULATIONS")
    parts.append("All session_date values you generate must be >= this date unless explicitly editing historical data.")
    parts.append("=" * 60)
    parts.append("CURRENT CLIENT CONTEXT")
    parts.append(f"Last refreshed: {session.get('last_refresh', 'Never')}")
    parts.append(f"Engagement state: {context.get('client_engagement_state', 'unknown')}")
    parts.append("=" * 60)

    # --- CLIENT PROFILE ---
    profile = context.get('client_profile', {})
    if profile:
        parts.append("")
        parts.append("CLIENT PROFILE:")
        parts.append(f"  Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
        parts.append(f"  Client ID: {profile.get('client_id', '')}")
        parts.append(f"  Age: {profile.get('age_years', '?')} | Sex: {profile.get('sex', '?')}")
        parts.append(f"  Height: {profile.get('height_cm', '?')}cm | Weight: {profile.get('weight_kg', '?')}kg | Waist: {profile.get('waist_circumference_cm', '?')}cm")
        parts.append(f"  Timezone: {profile.get('timezone', '?')}")
        parts.append(f"  Goals: {profile.get('goal_primary', 'not set')}")
        if profile.get('goal_secondary'):
            parts.append(f"    Secondary: {profile['goal_secondary']}")
        if profile.get('goal_tertiary'):
            parts.append(f"    Tertiary: {profile['goal_tertiary']}")
        if profile.get('goal_timeframe_months'):
            parts.append(f"    Timeframe: {profile['goal_timeframe_months']} months")
        parts.append(f"  Training experience: {profile.get('training_experience', '?')}")
        parts.append(f"  Strength: {profile.get('strength_level', '?')} | Cardio: {profile.get('cardio_fitness_level', '?')} | Movement: {profile.get('movement_quality', '?')}")
        parts.append(f"  Last trained: {profile.get('last_trained_date', '?')}")
        parts.append(f"  Days/week: {profile.get('days_per_week', '?')} | Typical recent: {profile.get('typical_sessions_per_week_last_3_months', '?')}/wk")
        parts.append(f"  Equipment: {profile.get('equipment_preference', '?')}")
        if profile.get('equipment_gym'):
            parts.append(f"    Gym: {profile['equipment_gym']}")
        if profile.get('equipment_home'):
            parts.append(f"    Home: {profile['equipment_home']}")
        parts.append(f"  Diet: {profile.get('diet_style', '?')}")
        parts.append(f"  Sleep: {profile.get('sleep_quality', '?')} | Stress: {profile.get('stress_level', '?')}")
        parts.append(f"  Work: {profile.get('work_pattern', '?')}")
        if profile.get('family_responsibilities'):
            parts.append(f"  Family: {profile['family_responsibilities']}")
        if profile.get('notes'):
            parts.append(f"  Notes: {profile['notes']}")

    # --- CONTRAINDICATIONS ---
    _format_contraindications(parts, profile, context)

    # --- NUTRITION ---
    nutrition = context.get('nutrition', {})
    if nutrition:
        parts.append("")
        parts.append("NUTRITION & SUPPLEMENTS:")
        targets = nutrition.get('nutrition_targets', {})
        if targets:
            if isinstance(targets, dict):
                parts.append(f"  Calories: {targets.get('calories', '?')} | Protein: {targets.get('protein', targets.get('protein_min', '?'))}g | Carbs: {targets.get('carbs', '?')}g | Fat: {targets.get('fat', '?')}g")
            else:
                parts.append(f"  Targets: {targets}")
        supps = nutrition.get('supplement_protocol', [])
        if supps:
            if isinstance(supps, list):
                for s in supps:
                    if isinstance(s, dict):
                        parts.append(f"  - {s.get('name', '?')} {s.get('dosage', '')} ({s.get('timing', '')})")
                    else:
                        parts.append(f"  - {s}")
            else:
                parts.append(f"  Supplements: {supps}")

    # --- ACTIVE TRAINING BLOCK ---
    plan = context.get('plan_context', {})
    active_block = plan.get('active_block', plan) if isinstance(plan, dict) else {}
    if active_block and active_block.get('plan_id'):
        parts.append("")
        parts.append("ACTIVE TRAINING BLOCK:")
        parts.append(f"  Plan: {active_block.get('plan_id', '?')}")
        parts.append(f"  Phase: {active_block.get('phase_name', '?')}")
        parts.append(f"  Goal: {active_block.get('phase_goal', '?')}")
        parts.append(f"  Duration: {active_block.get('duration_weeks', '?')} weeks | Days/week: {active_block.get('days_per_week', '?')}")
        parts.append(f"  Week start: {active_block.get('week_start', '?')}")
        parts.append(f"  Status: {active_block.get('plan_status', '?')}")
        parts.append(f"  Block ID: {active_block.get('block_id', '?')}")
        if active_block.get('constraints'):
            parts.append(f"  Constraints: {active_block['constraints']}")

    # --- ACTIVE WEEK ---
    weeks = context.get('weeks', {})
    active_week = weeks.get('active', {}) if isinstance(weeks, dict) else {}
    if active_week and active_week.get('week_id'):
        parts.append("")
        parts.append("CURRENT WEEK:")
        parts.append(f"  Week {active_week.get('week_number', '?')}: {active_week.get('week_id', '')}")
        parts.append(f"  Dates: {active_week.get('week_start_date', '?')} to {active_week.get('week_end_date', '?')}")
        parts.append(f"  Status: {active_week.get('week_status', '?')} | Type: {active_week.get('week_type', '?')}")
        parts.append(f"  Focus: {active_week.get('primary_focus', '?')}")
        if active_week.get('secondary_focus'):
            parts.append(f"  Secondary: {active_week['secondary_focus']}")
        parts.append(f"  Intensity: {active_week.get('intensity_pattern', '?')}")

    # --- SESSIONS ---
    sessions = context.get('sessions', {})
    if isinstance(sessions, dict):
        _format_sessions(parts, sessions)
    elif isinstance(sessions, list):
        # Fallback: flat list format
        _format_sessions(parts, {'active': sessions})

    # --- EXERCISE BESTS ---
    exercise_bests = context.get('Exercise Bests', [])
    if exercise_bests:
        _format_exercise_bests(parts, exercise_bests)

    # --- HISTORY SUMMARY ---
    history = context.get('history_summary', {})
    if history:
        parts.append("")
        parts.append("TRAINING HISTORY:")
        parts.append(f"  Completed blocks: {history.get('completed_blocks', 0)} | Weeks: {history.get('completed_weeks', 0)} | Sessions: {history.get('completed_sessions', 0)} | Steps: {history.get('completed_steps', 0)}")

    # --- CONTEXT VALIDITY ---
    validity = context.get('context_validity', {})
    if validity:
        parts.append("")
        parts.append("CONTEXT COUNTS:")
        parts.append(f"  Active sessions: {validity.get('active_sessions_count', 0)} | Completed: {validity.get('completed_sessions_count', 0)}")
        parts.append(f"  Active steps: {validity.get('active_steps_count', 0)} | Completed: {validity.get('completed_steps_count', 0)}")

    return "\n".join(parts)


# ============================================================
# CONTEXT FORMATTING HELPERS
# ============================================================

def _format_contraindications(parts, profile, context):
    """Format contraindications from both profile and dedicated arrays."""
    has_contras = False

    chronic = profile.get('chronic_contraindications', '')
    chronic_arr = context.get('Contraindications Chronic', [])
    temp_arr = context.get('Contraindications Temp', [])
    injuries = profile.get('injuries', '')

    if chronic or chronic_arr or temp_arr or injuries:
        parts.append("")
        parts.append("CONTRAINDICATIONS:")

    if chronic:
        parts.append(f"  Chronic: {chronic}")
        has_contras = True

    # Dedicated chronic array (Make.com numeric-key rows)
    if isinstance(chronic_arr, list):
        for item in chronic_arr:
            if isinstance(item, dict) and any(v for k, v in item.items() if not k.startswith('_')):
                parts.append(f"  Chronic condition: {_row_summary(item)}")
                has_contras = True

    # Temporary injuries array
    if isinstance(temp_arr, list):
        for item in temp_arr:
            if isinstance(item, dict) and any(v for k, v in item.items() if not k.startswith('_')):
                parts.append(f"  Temp injury: {_row_summary(item)}")
                has_contras = True

    if injuries and not has_contras:
        parts.append(f"  Injuries: {injuries}")

    if profile.get('risk_summary'):
        parts.append(f"  Risk: {profile['risk_summary']}")


def _format_sessions(parts, sessions_data):
    """Format sessions from V2 context (numeric-key Make.com rows).

    Session column mapping:
      0=plan_id, 1=block_id, 2=client_id, 3=week_number, 4=week_id,
      5=day_of_week, 6=session_id, 7=phase_name, 8=location,
      9=focus/title, 10=exercises, 11=secondary_focus, 12=supplements,
      13=session_summary, 14=session_date, 16=session_global_number,
      19=estimated_duration, 21=status
    """
    active = sessions_data.get('active', [])
    completed = sessions_data.get('completed', [])

    if active:
        parts.append("")
        parts.append(f"ACTIVE SESSIONS ({len(active)}):")
        for sess in active[:8]:  # Show up to 8 active sessions
            if isinstance(sess, dict):
                sid = sess.get('6', sess.get('session_id', '?'))
                date = sess.get('14', sess.get('session_date', ''))
                focus = sess.get('9', sess.get('focus', ''))
                exercises = sess.get('10', sess.get('exercises', ''))
                location = sess.get('8', sess.get('location', ''))
                summary = sess.get('13', sess.get('session_summary', ''))
                status = sess.get('21', sess.get('session_status', ''))
                duration = sess.get('19', sess.get('estimated_duration_minutes', ''))
                week = sess.get('3', sess.get('week_number', ''))
                day = sess.get('5', sess.get('day', ''))

                line = f"  [{sid}] Wk{week} Day{day}"
                if date:
                    line += f" ({date})"
                if focus:
                    line += f" — {focus}"
                if status:
                    line += f" [{status}]"
                parts.append(line)
                if exercises:
                    parts.append(f"    Exercises: {exercises}")
                if summary:
                    parts.append(f"    Summary: {str(summary)[:200]}")
                if location:
                    parts.append(f"    Location: {location}")
                if duration:
                    parts.append(f"    Duration: ~{duration}min")

        if len(active) > 8:
            parts.append(f"  ... and {len(active) - 8} more sessions")

    if completed:
        parts.append("")
        parts.append(f"COMPLETED SESSIONS ({len(completed)}):")
        for sess in completed[:4]:  # Show up to 4 recent completed
            if isinstance(sess, dict):
                sid = sess.get('6', sess.get('session_id', '?'))
                date = sess.get('14', sess.get('session_date', ''))
                focus = sess.get('9', sess.get('focus', ''))
                summary = sess.get('13', sess.get('session_summary', ''))

                line = f"  [{sid}]"
                if date:
                    line += f" ({date})"
                if focus:
                    line += f" — {focus}"
                parts.append(line)
                if summary:
                    parts.append(f"    Summary: {str(summary)[:200]}")

        if len(completed) > 4:
            parts.append(f"  ... and {len(completed) - 4} more completed")


def _format_exercise_bests(parts, bests):
    """Format Exercise Bests for Claude's system prompt.

    Supports data from Google Sheets direct reads (named headers) with
    fallback to old Make.com numeric-key format for backward compatibility.

    Actual Exercise_Bests sheet columns:
      client_id, exercise_name, metric_key, metric_family, better_direction,
      context_key, current_value, current_unit, current_timestamp,
      current_evidence_type, current_evidence_ref, current_confidence,
      first_value, first_unit, first_timestamp, first_evidence_type,
      first_evidence_ref, strength_load_kg, strength_reps, strength_e1rm_kg,
      distance_m, duration_s, avg_power_w, avg_hr_bpm, notes,
      session_count, last_session_timestamp
    """
    if not bests:
        return

    parts.append("")
    parts.append(f"EXERCISE BESTS ({len(bests)} exercises):")

    for entry in bests:
        if not isinstance(entry, dict):
            continue

        # Named keys (Google Sheets direct) with numeric fallbacks (Make.com legacy)
        name = entry.get('exercise_name') or entry.get('1', '?')
        if not name:
            continue

        metric_key   = entry.get('metric_key')   or entry.get('2', '')
        current_val  = entry.get('current_value') or entry.get('6', '')
        current_unit = entry.get('current_unit')  or entry.get('7', '')
        current_date = entry.get('current_timestamp') or entry.get('8', '')
        e1rm         = entry.get('strength_e1rm_kg', '')
        load_kg      = entry.get('strength_load_kg', '')
        reps         = entry.get('strength_reps', '')
        session_count = entry.get('session_count') or entry.get('17', '')

        line = f"  {name}:"

        # Prefer e1RM for strength exercises when available
        if e1rm:
            line += f" e1RM={e1rm}kg"
            if load_kg and reps:
                line += f" (from {load_kg}kg×{reps})"
        elif current_val:
            line += f" best={current_val}{current_unit}"

        if metric_key:
            line += f" [{metric_key}]"
        if current_date:
            line += f" on {str(current_date)[:10]}"
        if session_count:
            line += f" | {session_count} sessions"

        parts.append(line)


def _row_summary(row):
    """Extract readable text from a Make.com numeric-key row, skipping empties."""
    values = []
    for k, v in sorted(row.items(), key=lambda x: str(x[0])):
        if k.startswith('_'):
            continue
        if v and str(v).strip() and str(v).lower() != 'null':
            values.append(str(v))
    return ' | '.join(values[:5]) if values else '(empty)'


def build_system_prompt(session, include_context=True, user_message=None):
    """
    Build complete system prompt for Claude WITH PROMPT CACHING
    
    CRITICAL CHANGE: Returns ARRAY instead of STRING
    
    Structure:
    [
        {
            "type": "text",
            "text": "Bill's instructions...",
            "cache_control": {"type": "ephemeral"}  # CACHED
        },
        {
            "type": "text",
            "text": "Client context..."  # NOT CACHED (changes frequently)
        }
    ]
    
    Respects Bill's priority hierarchy:
    1. Safety rules (always loaded)
    2. Scenario Helper (for webhook operations)
    3. Data integrity rules (including Exercise Library authority)
    4. Exercise science
    5. Communication style
    
    Args:
        session: Session dict with mode, state, context
        include_context: Whether to include client context in prompt
        user_message: Unused — kept for API compatibility

    Returns:
        list: Structured system messages for Claude API (with cache_control)
    """

    mode = session.get('mode', OperatingMode.COACH)
    state = session.get('state', ClientState.STRANGER)
    operation_type = 'chat'  # Default, can be overridden

    # Load Bill instructions (STABLE - WILL BE CACHED)
    instructions = load_bill_instructions(mode, state, operation_type)
    
    # Build structured system messages array
    system_messages = []
    
    # PART 1: Bill's instructions (CACHED)
    # This is stable and should be cached
    system_messages.append({
        "type": "text",
        "text": instructions,
        "cache_control": {"type": "ephemeral"}
    })
    
    print(f"[Context Loader] Cached section: ~{len(instructions)} chars (~{len(instructions)//4} tokens estimated)")
    
    # PART 2: Client context (NOT CACHED)
    # This changes frequently, so don't cache it
    if include_context:
        client_context_text = build_client_context_text(session)
        
        if client_context_text:
            system_messages.append({
                "type": "text",
                "text": client_context_text
            })
            print(f"[Context Loader] Non-cached section: ~{len(client_context_text)} chars (~{len(client_context_text)//4} tokens estimated)")
    
    print(f"[Context Loader] Total system message blocks: {len(system_messages)}")
    
    return system_messages


def get_greeting_for_state(state, context=None):
    """
    Get appropriate greeting based on client state
    
    Args:
        state: ClientState value
        context: Optional client context
        
    Returns:
        str: Greeting message
    """
    
    if state == ClientState.STRANGER:
        return "Right then, I don't know you yet. If you're here to set up, give yourself a memorable client ID - your favourite animal, a book character, whatever sticks in your head. Something like 'cli_sherlock' or 'cli_tigger'. What'll it be?"
    
    elif state == ClientState.ONBOARDING:
        client_id = context.get('client_id') if context else 'there'
        return f"Right then, {client_id} it is. Let's get you set up properly. First things first - what's your actual name?"
    
    else:  # READY
        first_name = "there"
        if context:
            # V2 uses 'client_profile', V1 used 'profile'
            profile = context.get('client_profile', context.get('profile', {}))
            if profile:
                first_name = profile.get('first_name', 'there')
        return f"Right then, {first_name}, what's the plan today?"