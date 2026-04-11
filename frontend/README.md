# SkillsAI React Frontend

React + Vite frontend that prototypes the SkillsAI product vision as a two-surface enterprise app on a shared design system.

## Implemented frontend scope

The UI now models the core product structure:

- **Skills Control Center** for HR Admins and Analysts
- **Growth Workspace** for Managers and Employees
- **Role-aware primary navigation** (Home, Skills, Assessments, Coaching, Mobility, Analytics, Governance, Admin)
- **Shared entity model** chips (person, skill, role/job family, assessment, coaching plan, opportunity, audit event)
- **Trust-forward recommendation cards** with rationale, evidence chips, confidence, model/version, lineage, and audit actions

## Core screens included

- Persona landing pages for Admin, Analyst, Manager, and Employee
- Signature Skill Profile screen with:
  - header context
  - domain-grouped skill map
  - evidence timeline
  - explanation panel
  - actions rail
- Job family setup wizard table (9-step pilot-first flow)
- Assessment experience sections:
  - authoring studio (three-pane concept)
  - delivery requirements
  - results summary
- Analytics and longitudinal workspace with first-class controls and drill-down guidance
- Governance center with consent/policy KPIs and audit activity
- Mobility readiness and opportunity rationale content

## Design and UX intent

- Enterprise-grade and data-rich visual tone
- Denser control-center patterns with lighter growth-workspace messaging
- Explainability and governance visibility surfaced across screens
- Reusable domain components highlighted for future extraction into a design system

## Setup

```bash
cd frontend
npm install
npm run dev
```

## Build and lint

```bash
npm run lint
npm run build
```
