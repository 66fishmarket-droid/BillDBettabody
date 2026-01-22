// Bill D'Bettabody - Mock Data
// Simulates backend API responses with real schema structure

const MOCK_DATA = {
  // Client profile (from Clients sheet)
  profile: {
    client_id: 'cli_demo',
    first_name: 'Demo',
    last_name: 'User',
    email: 'demo@billdbet.com',
    timezone: 'Europe/London',
    sex: 'M',
    age_years: 35,
    height_cm: 180,
    weight_kg: 82,
    training_experience: '2-3 years',
    primary_background: 'Recreational gym-goer',
    typical_sessions_per_week_last_3_months: 3,
    goals: 'Build strength, improve body composition, feel better',
    goal_primary: 'Strength',
    goal_secondary: 'Body composition',
    equipment_gym: 'Full commercial gym access',
    sessions_completed: 47,
    current_phase: 'Strength Foundation - Week 4'
  },

  // Daily nutrition targets
  nutrition: {
    calories: 2400,
    protein: 180,
    carbs: 240,
    fats: 80,
    hydration_l: 3.0
  },

  // Today's session (from Plans_Sessions)
  todaySession: {
    session_id: 'sess_20260121_001',
    client_id: 'cli_demo',
    plan_id: 'plan_2026_q1',
    block_id: 'block_strength_foundation',
    week_id: 'week_4',
    week: 4,
    day: 2,
    session_date: '2026-01-21',
    session_day_of_week: 'Tuesday',
    phase: 'Strength Foundation',
    location: 'gym',
    focus: 'Lower Body Strength + Posterior Chain',
    estimated_duration_minutes: 55,
    intended_intensity_rpe: 8,
    session_status: 'scheduled'
  },

  // Session steps (from Plans_Steps) - exercises for today's session
  sessionSteps: [
    // Warm-up
    {
      step_id: 'step_001',
      session_id: 'sess_20260121_001',
      step_order: 1,
      segment_type: 'warmup',
      step_type: 'mobility',
      exercise_name: 'Hip Hinge Mobility Drill',
      duration_type: 'time',
      duration_value: 5,
      target_type: 'duration',
      target_value: '5 minutes easy flow',
      sets: 1,
      reps: null,
      notes_coach: 'Focus on hip flexion pattern, not rushing'
    },
    {
      step_id: 'step_002',
      session_id: 'sess_20260121_001',
      step_order: 2,
      segment_type: 'warmup',
      step_type: 'pulse_raise',
      exercise_name: 'Assault Bike',
      duration_type: 'time',
      duration_value: 6,
      target_type: 'hr_zone',
      target_value: 'Zone 2 (easy conversation pace)',
      sets: 1,
      reps: null,
      notes_coach: 'Build gradually, don\'t sprint out the gate'
    },
    {
      step_id: 'step_003',
      session_id: 'sess_20260121_001',
      step_order: 3,
      segment_type: 'warmup',
      step_type: 'activation',
      exercise_name: 'Glute Bridge',
      sets: 2,
      reps: 12,
      load_kg: 0,
      tempo_pattern: '2-1-2-0',
      rest_seconds: 30,
      notes_coach: 'Squeeze at top, don\'t rush the tempo'
    },
    {
      step_id: 'step_004',
      session_id: 'sess_20260121_001',
      step_order: 4,
      segment_type: 'warmup',
      step_type: 'activation',
      exercise_name: 'Band Pull-Apart',
      sets: 2,
      reps: 15,
      load_kg: 0,
      rest_seconds: 30,
      notes_coach: 'Light band, focus on scapular retraction'
    },

    // Main work
    {
      step_id: 'step_005',
      session_id: 'sess_20260121_001',
      step_order: 5,
      segment_type: 'main',
      step_type: 'strength',
      exercise_name: 'Barbell Back Squat',
      sets: 4,
      reps: 6,
      load_kg: 100,
      tempo_pattern: '3-0-1-0',
      rest_seconds: 180,
      target_type: 'rpe',
      target_value: 8,
      notes_coach: 'Control descent, explode up. Leave 2 reps in tank.',
      pattern_type: 'straight',
      has_pb: true
    },
    {
      step_id: 'step_006',
      session_id: 'sess_20260121_001',
      step_order: 6,
      segment_type: 'main',
      step_type: 'strength',
      exercise_name: 'Romanian Deadlift',
      sets: 3,
      reps: 8,
      load_kg: 80,
      tempo_pattern: '3-1-1-0',
      rest_seconds: 150,
      target_type: 'rpe',
      target_value: 7,
      notes_coach: 'Feel the hamstring stretch, bar close to legs',
      pattern_type: 'straight'
    },
    {
      step_id: 'step_007',
      session_id: 'sess_20260121_001',
      step_order: 7,
      segment_type: 'main',
      step_type: 'accessory',
      exercise_name: 'Bulgarian Split Squat',
      sets: 3,
      reps: 10,
      load_kg: 20,
      tempo_pattern: '2-0-1-0',
      rest_seconds: 90,
      notes_coach: 'Per leg. Torso upright, knee tracking over toes.'
    },
    {
      step_id: 'step_008',
      session_id: 'sess_20260121_001',
      step_order: 8,
      segment_type: 'main',
      step_type: 'accessory',
      exercise_name: 'Leg Curl',
      sets: 3,
      reps: 12,
      load_kg: 40,
      tempo_pattern: '2-1-2-0',
      rest_seconds: 90,
      notes_coach: 'Controlled reps, full range of motion'
    },
    {
      step_id: 'step_009',
      session_id: 'sess_20260121_001',
      step_order: 9,
      segment_type: 'main',
      step_type: 'accessory',
      exercise_name: 'Standing Calf Raise',
      sets: 3,
      reps: 15,
      load_kg: 60,
      rest_seconds: 60,
      notes_coach: 'Full stretch at bottom, squeeze at top'
    },

    // Cool-down
    {
      step_id: 'step_010',
      session_id: 'sess_20260121_001',
      step_order: 10,
      segment_type: 'cooldown',
      step_type: 'breathing',
      exercise_name: 'Box Breathing',
      duration_type: 'time',
      duration_value: 3,
      sets: 1,
      notes_coach: '4 seconds in, hold 4, out 4, hold 4. Calm the system.'
    },
    {
      step_id: 'step_011',
      session_id: 'sess_20260121_001',
      step_order: 11,
      segment_type: 'cooldown',
      step_type: 'stretch',
      exercise_name: 'Hamstring Stretch',
      duration_type: 'time',
      duration_value: 2,
      sets: 1,
      notes_coach: 'Per leg, gentle hold, no bouncing'
    },
    {
      step_id: 'step_012',
      session_id: 'sess_20260121_001',
      step_order: 12,
      segment_type: 'cooldown',
      step_type: 'mobility',
      exercise_name: 'Thoracic Rotation',
      duration_type: 'time',
      duration_value: 2,
      sets: 1,
      notes_coach: 'Slow, controlled rotations. Feel the mid-back open up.'
    }
  ],

  // Exercise bests (from Exercise_Bests sheet)
  bests: [
    {
      client_id: 'cli_demo',
      exercise_name: 'Barbell Back Squat',
      metric_key: 'e1rm_kg',
      current_value: 125,
      current_unit: 'kg',
      current_timestamp: '2026-01-14',
      strength_load_kg: 110,
      strength_reps: 5
    },
    {
      client_id: 'cli_demo',
      exercise_name: 'Romanian Deadlift',
      metric_key: 'e1rm_kg',
      current_value: 105,
      current_unit: 'kg',
      current_timestamp: '2026-01-12',
      strength_load_kg: 90,
      strength_reps: 6
    },
    {
      client_id: 'cli_demo',
      exercise_name: 'Assault Bike',
      metric_key: 'max_calories_10min',
      current_value: 142,
      current_unit: 'cal',
      current_timestamp: '2026-01-10'
    }
  ]
};

// Helper function to get mock data (simulates API calls)
function getMockData(endpoint) {
  console.log('[Mock Data] Fetching:', endpoint);
  
  if (endpoint === '/sessions/today') {
    return {
      session: MOCK_DATA.todaySession,
      stepCount: {
        warmup: 4,
        main: 5,
        cooldown: 3
      }
    };
  }
  
  if (endpoint.startsWith('/sessions/') && endpoint.endsWith('/steps')) {
    return {
      session: MOCK_DATA.todaySession,
      steps: MOCK_DATA.sessionSteps
    };
  }
  
  if (endpoint === '/profile') {
    return MOCK_DATA.profile;
  }
  
  if (endpoint === '/nutrition/daily') {
    return MOCK_DATA.nutrition;
  }
  
  if (endpoint === '/bests') {
    return MOCK_DATA.bests;
  }
  
  return null;
}
