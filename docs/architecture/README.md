# SkillsAI Architecture Option 17

This directory contains a C4-style architecture specification for SkillsAI Option 17 using plain PlantUML (no external C4 library required).

## Diagram set

1. `01-system-context.puml` - Level 1: system context
2. `02-container-diagram.puml` - Level 2: container diagram
3. `03b-core-intelligence-components.puml` - Level 3B: core intelligence components
4. `03c-assessments-components.puml` - Level 3C: assessments components
5. `03d-analytics-longitudinal-components.puml` - Level 3D: analytics and longitudinal components
6. `03a-federation-gateway-components.puml` - Level 3A: federation gateway components

## Recommended reading order

For architecture decks and technical specification walkthroughs, present the diagrams in this order:

1. Level 1 - System Context
2. Level 2 - Container
3. Level 3B - Core Intelligence
4. Level 3C - SkillsAI Assessments
5. Level 3D - Analytics & Longitudinal
6. Level 3A - Federation Gateway

This sequence first establishes platform boundaries, then deployment shape, then core inference logic, then evidence ingestion, then KPI/history production, and finally request entry/orchestration.

## Suggested presentation-friendly container naming

- Core Intelligence -> Skills Intelligence Core
- Activation Services -> Talent Activation Services
- Analytics & Longitudinal -> Workforce Analytics Platform
- SkillsAI Assessments -> Assessment Platform
