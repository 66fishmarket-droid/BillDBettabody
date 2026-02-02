#!/usr/bin/env python3
"""
Exercise Library Group Generator
=================================

Reads the Exercises_Library sheet from Google Sheets and creates filtered
JSON files for each exercise group (Upper_Push, Lower_Pull, Swimming, etc.)

This script is designed to run weekly via GitHub Actions to keep exercise
groups up-to-date as the library grows.

Author: Bill D'Bettabody Migration Team
"""

import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd


class ExerciseGroupGenerator:
    """Generates exercise group JSON files from Google Sheets Exercise Library"""
    
    def __init__(self, credentials_json, sheet_id, sheet_name='Exercises_Library'):
        """
        Initialize the generator with Google Sheets credentials
        
        Args:
            credentials_json (str): JSON string of service account credentials
            sheet_id (str): Google Sheets spreadsheet ID
            sheet_name (str): Name of the worksheet containing exercises
        """
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.df = None
        self.output_dir = 'exercise_groups'
        
        # Authorize with Google Sheets
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds_dict = json.loads(credentials_json)
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        self.client = gspread.authorize(credentials)
        
    def fetch_exercises(self):
        """Fetch exercise data from Google Sheets"""
        print(f"Fetching exercises from sheet: {self.sheet_name}...")
        
        spreadsheet = self.client.open_by_key(self.sheet_id)
        worksheet = spreadsheet.worksheet(self.sheet_name)
        data = worksheet.get_all_records()
        
        self.df = pd.DataFrame(data)
        print(f"✅ Loaded {len(self.df)} exercises")
        
        return self.df
    
    def filter_group(self, **criteria):
        """
        Filter exercises based on multiple criteria
        
        Args:
            **criteria: Keyword arguments for filtering (e.g., body_region='upper')
        
        Returns:
            pd.DataFrame: Filtered dataframe
        """
        filtered = self.df.copy()
        
        for field, value in criteria.items():
            if isinstance(value, list):
                # Multiple acceptable values (OR logic)
                filtered = filtered[filtered[field].isin(value)]
            else:
                # Single value
                filtered = filtered[filtered[field] == value]
        
        return filtered
    
    def get_warmup_exercises(self, relevant_body_regions=None, relevant_patterns=None):
        """
        Get warm-up exercises relevant to specific body regions or movement patterns
        
        Args:
            relevant_body_regions (list): Body regions to include (e.g., ['upper'])
            relevant_patterns (list): Movement patterns to include
        
        Returns:
            pd.DataFrame: Warm-up exercises
        """
        # Start with exercises tagged as warmup
        warmups = self.df[self.df['segment_type'].str.contains('warmup', case=False, na=False)]
        
        # Filter by body region if specified
        if relevant_body_regions:
            warmups = warmups[warmups['body_region'].isin(relevant_body_regions)]
        
        # Filter by movement pattern if specified
        if relevant_patterns:
            warmups = warmups[warmups['movement_pattern'].isin(relevant_patterns)]
        
        return warmups
    
    def get_cooldown_exercises(self, relevant_body_regions=None):
        """
        Get cool-down/mobility exercises relevant to specific body regions
        
        Args:
            relevant_body_regions (list): Body regions to include
        
        Returns:
            pd.DataFrame: Cool-down exercises
        """
        # Exercises with mobility category or mobility in training_focus
        cooldowns = self.df[
            (self.df['category'] == 'mobility') |
            (self.df['training_focus'].str.contains('mobility', case=False, na=False))
        ]
        
        # Filter by body region if specified
        if relevant_body_regions:
            cooldowns = cooldowns[cooldowns['body_region'].isin(relevant_body_regions)]
        
        return cooldowns
    
    def create_exercise_dict(self, row, include_fields=None):
        """
        Convert a DataFrame row to a clean exercise dictionary
        
        Args:
            row (pd.Series): Exercise row from DataFrame
            include_fields (list): Fields to include (None = all essential fields)
        
        Returns:
            dict: Clean exercise data
        """
        if include_fields is None:
            # Default essential fields
            include_fields = [
                'exercise_id',
                'exercise_name',
                'category',
                'body_region',
                'movement_pattern',
                'equipment',
                'primary_muscles',
                'segment_type',
                'difficulty',
                'coaching_cues_short',
                'safety_notes',
                'regression',
                'progression',
                'training_focus',
                'secondary_muscles',
                'special_flags'
            ]
        
        # Build dictionary with only non-null values
        exercise_dict = {}
        for field in include_fields:
            if field in row.index and pd.notna(row[field]) and row[field] != '':
                exercise_dict[field] = row[field]
        
        return exercise_dict
    
    def generate_group_file(self, group_name, main_exercises, warmup_exercises, 
                           cooldown_exercises, description):
        """
        Generate a JSON file for an exercise group
        
        Args:
            group_name (str): Name of the group (e.g., 'Upper_Push')
            main_exercises (pd.DataFrame): Main exercises for this group
            warmup_exercises (pd.DataFrame): Relevant warm-up exercises
            cooldown_exercises (pd.DataFrame): Relevant cool-down exercises
            description (str): Human-readable description of the group
        """
        group_data = {
            "group_name": group_name,
            "description": description,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "exercise_count": {
                "main": len(main_exercises),
                "warmup": len(warmup_exercises),
                "cooldown": len(cooldown_exercises),
                "total": len(main_exercises) + len(warmup_exercises) + len(cooldown_exercises)
            },
            "main_exercises": [
                self.create_exercise_dict(row) 
                for _, row in main_exercises.iterrows()
            ],
            "warmup_exercises": [
                self.create_exercise_dict(row) 
                for _, row in warmup_exercises.iterrows()
            ],
            "cooldown_exercises": [
                self.create_exercise_dict(row) 
                for _, row in cooldown_exercises.iterrows()
            ]
        }
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Write JSON file
        filename = f"{self.output_dir}/{group_name}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(group_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created {filename} ({group_data['exercise_count']['total']} exercises)")
        
        return group_data
    
    def generate_all_groups(self):
        """Generate all exercise group files"""
        
        print("\n" + "="*80)
        print("GENERATING EXERCISE GROUP FILES")
        print("="*80 + "\n")
        
        groups_created = []
        
        # 1. UPPER PUSH
        main = self.df[
            (self.df['body_region'] == 'upper') &
            (self.df['movement_pattern'].isin(['push_horizontal', 'push_vertical'])) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(
            relevant_body_regions=['upper'],
            relevant_patterns=['push_horizontal', 'push_vertical']
        )
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['upper'])
        
        groups_created.append(self.generate_group_file(
            group_name='Upper_Push',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Upper body pushing movements (horizontal and vertical presses)'
        ))
        
        # 2. UPPER PULL
        main = self.df[
            (self.df['body_region'] == 'upper') &
            (self.df['movement_pattern'].isin(['pull_horizontal', 'pull_vertical'])) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(
            relevant_body_regions=['upper'],
            relevant_patterns=['pull_horizontal', 'pull_vertical']
        )
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['upper'])
        
        groups_created.append(self.generate_group_file(
            group_name='Upper_Pull',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Upper body pulling movements (rows, pull-ups, lat work)'
        ))
        
        # 3. LOWER PUSH
        main = self.df[
            (self.df['body_region'] == 'lower') &
            (self.df['movement_pattern'].isin(['squat', 'lunge'])) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(
            relevant_body_regions=['lower'],
            relevant_patterns=['squat', 'lunge']
        )
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['lower'])
        
        groups_created.append(self.generate_group_file(
            group_name='Lower_Push',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Lower body knee-dominant movements (squats, lunges)'
        ))
        
        # 4. LOWER PULL
        main = self.df[
            (self.df['body_region'] == 'lower') &
            (self.df['movement_pattern'] == 'hinge') &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(
            relevant_body_regions=['lower'],
            relevant_patterns=['hinge']
        )
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['lower'])
        
        groups_created.append(self.generate_group_file(
            group_name='Lower_Pull',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Lower body hip-dominant movements (deadlifts, hip thrusts)'
        ))
        
        # 5. CORE
        main = self.df[
            (
                (self.df['category'] == 'core') |
                (self.df['movement_pattern'].isin([
                    'anti_extension', 'anti_rotation', 'anti_lateral_flexion', 'rotation'
                ]))
            ) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(
            relevant_body_regions=['core'],
            relevant_patterns=['anti_extension', 'anti_rotation', 'anti_lateral_flexion']
        )
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['core'])
        
        groups_created.append(self.generate_group_file(
            group_name='Core',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Core stability and anti-movement exercises'
        ))
        
        # 6. SWIMMING
        main = self.df[
            (
                (self.df['category'] == 'swimming') |
                (self.df['environment'] == 'pool') |
                (self.df['locomotion_type'] == 'swim')
            ) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.df[
            (self.df['environment'] == 'pool') &
            (self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        cooldown = self.df[
            (self.df['environment'] == 'pool') &
            (
                (self.df['category'] == 'mobility') |
                (self.df['training_focus'].str.contains('mobility', case=False, na=False))
            )
        ]
        
        groups_created.append(self.generate_group_file(
            group_name='Swimming',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Swimming strokes, drills, and pool-based exercises'
        ))
        
        # 7. CARDIO
        main = self.df[
            (self.df['locomotion_type'].isin(['run', 'jog', 'walk', 'cycle', 'row', 'ski'])) &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.df[
            (self.df['category'] == 'conditioning') &
            (self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['lower', 'full'])
        
        groups_created.append(self.generate_group_file(
            group_name='Cardio',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Cardiovascular training (running, cycling, rowing, etc.)'
        ))
        
        # 8. FULL BODY
        main = self.df[
            (self.df['body_region'] == 'full') &
            (~self.df['segment_type'].str.contains('warmup', case=False, na=False))
        ]
        warmup = self.get_warmup_exercises(relevant_body_regions=['full'])
        cooldown = self.get_cooldown_exercises(relevant_body_regions=['full'])
        
        groups_created.append(self.generate_group_file(
            group_name='Full_Body',
            main_exercises=main,
            warmup_exercises=warmup,
            cooldown_exercises=cooldown,
            description='Full-body compound movements and athletic exercises'
        ))
        
        # Generate summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        total_exercises = 0
        for group in groups_created:
            total_exercises += group['exercise_count']['total']
            print(f"{group['group_name']:15} | Main: {group['exercise_count']['main']:3d} | "
                  f"Warmup: {group['exercise_count']['warmup']:3d} | "
                  f"Cooldown: {group['exercise_count']['cooldown']:3d} | "
                  f"Total: {group['exercise_count']['total']:3d}")
        
        print(f"\n✅ Generated {len(groups_created)} group files")
        print(f"✅ Total exercise instances: {total_exercises}")
        print(f"✅ Source library size: {len(self.df)} exercises\n")
        
        return groups_created


def main():
    """Main execution function for GitHub Actions"""
    
    # Get credentials from environment variables
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
    sheet_id = os.environ.get('SHEET_ID')
    sheet_name = os.environ.get('SHEET_NAME', 'Exercises_Library')
    
    if not credentials_json or not sheet_id:
        print("❌ ERROR: Missing required environment variables")
        print("   Required: GOOGLE_CREDENTIALS, SHEET_ID")
        exit(1)
    
    # Initialize generator
    generator = ExerciseGroupGenerator(
        credentials_json=credentials_json,
        sheet_id=sheet_id,
        sheet_name=sheet_name
    )
    
    # Fetch exercises
    generator.fetch_exercises()
    
    # Generate all group files
    generator.generate_all_groups()
    
    print("✅ Exercise group generation complete!")


if __name__ == '__main__':
    main()
