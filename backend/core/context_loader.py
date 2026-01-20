"""
Bill D'Bettabody - Context Loader
Selective instruction loading to optimize token usage
Implements smart loading based on mode, state, and operation type
"""

import os
from config import Config
from core.bill_config import OperatingMode, ClientState


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


def load_scenario_helper():
    """
    Load Scenario Helper Instructions (webhook contracts)
    Section 3.0: SCENARIO HELPER IS EXECUTION LAW
    
    Returns:
        str: Scenario helper content
    """
    filepath = Config.SCENARIO_HELPER_PATH
    return load_section_from_file(filepath)


def load_exercise_library_quick_ref():
    """
    Load Exercise Library Quick Reference
    
    PURPOSE: Exercise name lookup for prescription/selection
    Contains: Exercise names, basic classification, equipment
    
    WHEN TO USE: Always when prescribing training
    
    Returns:
        str: Exercise library quick reference content
    """
    quick_ref_path = os.path.join(
        Config.DOCS_DIR,
        'Exercise_Instructions',
        'Exercise_Library_QuickRef_v2.txt'
    )
    
    if os.path.exists(quick_ref_path):
        print("[Context Loader] Loading Exercise Library Quick Reference")
        return load_section_from_file(quick_ref_path)
    
    print("[Context Loader] WARNING: Exercise Library QuickRef not found!")
    return ""


def load_exercise_library_canonical():
    """
    Load Exercise Library Canonical (Full Details)
    
    PURPOSE: Detailed exercise information for user education
    Contains: Full descriptions, coaching cues, safety notes, 
              common mistakes, progressions/regressions, YouTube links
    
    WHEN TO USE: When user asks about specific exercises
    
    Returns:
        str: Exercise library canonical content
    """
    canonical_path = os.path.join(
        Config.DOCS_DIR,
        'Exercise_Instructions',
        'Exercise_Library_Canonical_v2_full.txt'
    )
    
    if os.path.exists(canonical_path):
        print("[Context Loader] Loading Exercise Library Canonical (Full Details)")
        return load_section_from_file(canonical_path)
    
    print("[Context Loader] WARNING: Exercise Library Canonical not found!")
    return ""


def load_bill_core_instructions():
    """
    Load core Bill instructions (always loaded)
    
    Includes:
    - Section 0: Priority order & core principles
    - Section 1: Operating modes, identity, safety
    
    Returns:
        str: Core instruction content
    """
    # For V1, load full file
    # TODO: Optimize to load only Sections 0-1
    filepath = Config.BILL_INSTRUCTIONS_PATH
    return load_section_from_file(filepath)


def load_bill_instructions(mode, client_state, operation_type='chat', 
                          include_exercise_quickref=False, 
                          include_exercise_canonical=False):
    """
    Load Bill instructions selectively based on context
    
    OPTIMIZATION STRATEGY:
    - Always load: Sections 0 (priorities) and 1 (identity/safety)
    - Mode-specific: Coach vs Developer vs Tech
    - State-specific: Stranger vs Onboarding vs Ready
    - Operation-specific: Chat vs Webhook vs Planning
    - Exercise QuickRef: When prescribing training
    - Exercise Canonical: When explaining exercises in detail
    
    Args:
        mode: OperatingMode value ('coach', 'tech', 'developer')
        client_state: ClientState value ('stranger', 'onboarding', 'ready')
        operation_type: Type of operation ('chat', 'webhook', 'planning')
        include_exercise_quickref: Load exercise names for prescription
        include_exercise_canonical: Load full exercise details for education
        
    Returns:
        str: Assembled instruction text
    """
    
    instructions_parts = []
    
    # ALWAYS LOAD: Core identity and rules
    instructions_parts.append("=" * 60)
    instructions_parts.append("BILL D'BETTABODY - CORE INSTRUCTIONS")
    instructions_parts.append("=" * 60)
    instructions_parts.append("")
    
    # Load full Bill instructions for V1
    # TODO: Optimize to load selective sections
    core_instructions = load_bill_core_instructions()
    if core_instructions:
        instructions_parts.append(core_instructions)
    
    # Add mode-specific context
    instructions_parts.append("")
    instructions_parts.append("=" * 60)
    instructions_parts.append(f"CURRENT OPERATING MODE: {mode.upper()}")
    instructions_parts.append(f"CLIENT STATE: {client_state.upper()}")
    instructions_parts.append(f"OPERATION TYPE: {operation_type.upper()}")
    instructions_parts.append("=" * 60)
    instructions_parts.append("")
    
    # EXERCISE LIBRARY QUICK REFERENCE (for prescription)
    # Section 4.1a: Bill MUST ONLY use exercises from this library
    if include_exercise_quickref or operation_type in ['planning', 'training', 'session']:
        instructions_parts.append("=" * 60)
        instructions_parts.append("EXERCISE LIBRARY - QUICK REFERENCE")
        instructions_parts.append("(Exercise names for prescription - VERBATIM MATCH REQUIRED)")
        instructions_parts.append("=" * 60)
        instructions_parts.append("")
        
        exercise_quickref = load_exercise_library_quick_ref()
        if exercise_quickref:
            instructions_parts.append(exercise_quickref)
        else:
            instructions_parts.append("ERROR: Exercise QuickRef not loaded!")
            instructions_parts.append("Bill CANNOT prescribe training without canonical exercise names.")
        
        instructions_parts.append("")
    
    # EXERCISE LIBRARY CANONICAL (for detailed explanations)
    # Load when user asks about exercises
    if include_exercise_canonical:
        instructions_parts.append("=" * 60)
        instructions_parts.append("EXERCISE LIBRARY - CANONICAL (FULL DETAILS)")
        instructions_parts.append("(Detailed descriptions, cues, safety notes, videos)")
        instructions_parts.append("=" * 60)
        instructions_parts.append("")
        
        exercise_canonical = load_exercise_library_canonical()
        if exercise_canonical:
            instructions_parts.append(exercise_canonical)
        else:
            instructions_parts.append("WARNING: Exercise Canonical not loaded!")
        
        instructions_parts.append("")
    
    # Load Scenario Helper if webhook operation
    if operation_type == 'webhook' or mode == OperatingMode.DEVELOPER:
        instructions_parts.append("=" * 60)
        instructions_parts.append("SCENARIO HELPER INSTRUCTIONS (EXECUTION LAW)")
        instructions_parts.append("=" * 60)
        instructions_parts.append("")
        
        scenario_helper = load_scenario_helper()
        if scenario_helper:
            instructions_parts.append(scenario_helper)
    
    return "\n".join(instructions_parts)


def detect_exercise_question(message):
    """
    Detect if user is asking about specific exercises
    
    Triggers canonical library loading for:
    - "How do I do X?"
    - "What's a good form for Y?"
    - "Show me how to Z"
    - "Tell me about [exercise]"
    
    Args:
        message: User's message
        
    Returns:
        bool: True if asking about exercise details
    """
    exercise_keywords = [
        'how do i do',
        'how to do',
        'show me how',
        'tell me about',
        'what is a',
        'explain',
        'demonstrate',
        'form check',
        'technique',
        'video for',
        'link to',
        'youtube'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in exercise_keywords)


def build_system_prompt(session, include_context=True, user_message=None):
    """
    Build complete system prompt for Claude
    
    Respects Bill's priority hierarchy:
    1. Safety rules (always loaded)
    2. Scenario Helper (for webhook operations)
    3. Data integrity rules (including Exercise Library authority)
    4. Exercise science
    5. Communication style
    
    SMART LOADING:
    - QuickRef: Auto-loaded for READY clients (might prescribe)
    - Canonical: Loaded only when user asks about exercises
    
    Args:
        session: Session dict with mode, state, context
        include_context: Whether to include client context in prompt
        user_message: Current user message (for exercise question detection)
        
    Returns:
        str: Complete system prompt
    """
    
    mode = session.get('mode', OperatingMode.COACH)
    state = session.get('state', ClientState.STRANGER)
    operation_type = 'chat'  # Default, can be overridden
    
    # Auto-detect exercise library needs
    include_exercise_quickref = False
    include_exercise_canonical = False
    
    # Load QuickRef if client is READY (might discuss/prescribe training)
    if state == ClientState.READY:
        include_exercise_quickref = True
    
    # Load Canonical if user is asking about specific exercises
    if user_message and detect_exercise_question(user_message):
        include_exercise_canonical = True
        print("[Context Loader] Exercise question detected - loading canonical library")
    
    # Load Bill instructions
    instructions = load_bill_instructions(
        mode, 
        state, 
        operation_type,
        include_exercise_quickref=include_exercise_quickref,
        include_exercise_canonical=include_exercise_canonical
    )
    
    prompt_parts = [instructions]
    
    # Add client context if available and in READY state
    if include_context and state == ClientState.READY:
        context = session.get('context', {})
        
        if context:
            prompt_parts.append("")
            prompt_parts.append("=" * 60)
            prompt_parts.append("CURRENT CLIENT CONTEXT")
            prompt_parts.append(f"Last refreshed: {session.get('last_refresh', 'Never')}")
            prompt_parts.append("=" * 60)
            prompt_parts.append("")
            
            # Add key context elements
            # (Don't dump entire context - extract key fields)
            if context.get('profile'):
                prompt_parts.append("CLIENT PROFILE:")
                profile = context['profile']
                prompt_parts.append(f"- Name: {profile.get('first_name', '')} {profile.get('last_name', '')}")
                prompt_parts.append(f"- Goals: {profile.get('goal_primary', '')}")
                prompt_parts.append(f"- Experience: {profile.get('training_experience', '')}")
                prompt_parts.append("")
            
            # Add contraindications if present
            contraindications = context.get('contraindications', {})
            if contraindications:
                prompt_parts.append("ACTIVE CONTRAINDICATIONS:")
                prompt_parts.append(str(contraindications))
                prompt_parts.append("")
    
    return "\n".join(prompt_parts)


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
        if context and context.get('profile'):
            first_name = context['profile'].get('first_name', 'there')
        return f"Right then, {first_name}, what's the plan today?"