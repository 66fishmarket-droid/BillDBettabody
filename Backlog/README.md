# BACKLOG — README

A structured backlog of upcoming features, enhancements, architectural decisions, and future capabilities for Bill D’Bettabody, the AI-powered fitness and automation coach.

This folder acts as the single source of truth for everything that is planned but not yet built. Each backlog item is stored as a standalone .txt file for easy editing, referencing, and versioning.

## FOLDER PURPOSE

The Backlog is designed to:
- Track future improvements clearly and transparently
- Keep development scoped and manageable
- Prevent good ideas from being lost during large conversations
- Provide a roadmap for future commercialisation
- Break the system into discrete, discussable components
- Support GitHub-based planning (issues → milestones → tags → releases)

## BACKLOG ITEM FORMAT

Each .txt file should follow this structure:

TITLE: <Short name of feature or enhancement>

DESCRIPTION:
High-level summary of what this feature is and why it exists.

REQUIREMENTS or ACTIONS:
List any technical, architectural, or behavioural components needed.

DEPENDENCIES:
Any other backlog items, actions, or system modules this depends on.

STATUS:
Backlog | In Progress | Done | Deprecated

PRIORITY:
High | Medium | Low

Additional optional fields:
- RISKS
- NOTES
- OPEN QUESTIONS
- API IMPACT
- USER IMPACT
- METRICS / SUCCESS CRITERIA

## WORKFLOW: HOW BACKLOG ITEMS MOVE THROUGH THE SYSTEM

The intended lifecycle for backlog items is:

Backlog → Refinement → Design → Implementation → Review → Done

1. Backlog  
   Raw idea or architectural note. Stored in this folder.

2. Refinement  
   Discussed with Bill (Tech Mode). Scope, inputs, outputs clarified.

3. Design  
   JSON/OpenAPI updates drafted; Make.com skeleton created; data model updates defined.

4. Implementation  
   Scenario construction, sheet mapping, API testing, logic building.

5. Review  
   Validate functionality, safety, consistency with Bill’s coaching philosophy, and clean outputs.

6. Done  
   Either moved to a /Completed folder (future) or marked Done inside the file.

## PRIORITISATION GUIDE

General rules:

HIGH PRIORITY:
- Core architecture missing pieces
- Essential coaching flows
- Required by the weekly generator
- Anything needed for correctness or user safety

MEDIUM PRIORITY:
- UX improvements
- Automation enhancements
- Integrations unlocking valuable workflows

LOW PRIORITY:
- Long-term commercial features
- Optional enhancements
- Precision/premium capabilities

## HOW BACKLOG ITEMS CONNECT TO BILL’S INSTRUCTION SET

Each backlog item may require updates to:
- Bill’s system instructions
- Bill’s action logic (OpenAPI definitions)
- Bill’s behavioural rules
- Make.com scenarios and webhooks

General pattern:
1. Item enters Backlog  
2. Refined with Bill → instructions updated  
3. API specs updated → Make scenarios built  
4. Feature becomes part of working behaviour

This ensures traceability from idea → behaviour → implementation.

## CURRENT ITEMS IN THIS FOLDER

1. weekly-session-fueling-cues.txt
2. scheduled-bill-weekly-nudge.txt
3. scientific-integrity-review-engine.txt
4. coaching-philosophy-section.txt
5. client-lookup-capabilities.txt
6. precision-nutrition-mode.txt
7. step-generation-refactor.txt
8. database-migration-future.txt
9. garmin-integration-architecture.txt
10. per-user-scheduling-engine.txt

## NAMING CONVENTION

Use kebab-case filenames, e.g.:

feature-name-description.txt

## NEXT STEPS

I can also generate:
- A Backlog Index file summarising all items
- A GitHub Issue template
- A Milestone plan (v1, v2, commercialisation roadmap)

Just say:
“Generate backlog index”
or
“Generate issues template”
or
“Create milestones”
