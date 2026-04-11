import { useMemo, useState } from 'react'
import './App.css'

const SURFACE_OPTIONS = [
  { id: 'control', label: 'Skills Control Center', subtitle: 'HR Admins and Analysts' },
  { id: 'growth', label: 'Growth Workspace', subtitle: 'Managers and Employees' },
]

const PERSONA_BY_SURFACE = {
  control: [
    { id: 'admin', label: 'HR Admin' },
    { id: 'analyst', label: 'Analyst' },
  ],
  growth: [
    { id: 'manager', label: 'Manager' },
    { id: 'employee', label: 'Employee' },
  ],
}

const ROLE_NAVIGATION = {
  admin: ['Home', 'Skills', 'Assessments', 'Coaching', 'Mobility', 'Analytics', 'Governance', 'Admin'],
  analyst: ['Home', 'Skills', 'Assessments', 'Mobility', 'Analytics', 'Governance'],
  manager: ['Home', 'Skills', 'Assessments', 'Coaching', 'Mobility', 'Analytics'],
  employee: ['Home', 'Skills', 'Assessments', 'Coaching', 'Mobility'],
}

const ENTITY_MODEL = [
  'person',
  'skill',
  'role / job family',
  'assessment',
  'coaching plan',
  'opportunity',
  'audit event',
]

const LANDING_ROWS = {
  admin: {
    title: 'HR Admin home',
    subtitle: 'Cockpit view for pilot operations, governance, and readiness.',
    rows: [
      {
        title: 'Top row',
        cards: [
          { label: 'Pilot status', value: 'On track', detail: '82% milestones complete' },
          { label: 'Active job families', value: '6', detail: '2 pending launch approval' },
          { label: 'Data freshness', value: '4.2 hours', detail: 'Last sync at 09:42 UTC' },
          { label: 'Governance health', value: '93/100', detail: '2 policy exceptions open' },
        ],
      },
      {
        title: 'Middle row',
        cards: [
          { label: 'Connectors status', value: '14/15 green', detail: 'ATS connector delayed' },
          { label: 'Identity queue', value: '128 records', detail: '34 high-priority duplicates' },
          { label: 'Taxonomy changes', value: '9 pending', detail: 'Awaiting owner approval' },
          { label: 'Inference runs', value: '3 active', detail: 'Latest run at 74%' },
        ],
      },
      {
        title: 'Bottom row',
        cards: [
          { label: 'Executive KPI summary', value: '+6.4 readiness', detail: 'vs baseline' },
          { label: 'Assessment windows', value: '2 this month', detail: 'Customer Ops + Finance' },
          { label: 'Fairness alerts', value: '1 medium', detail: 'Regional confidence skew' },
          { label: 'Audit exports', value: '4 queued', detail: 'SOC2 package due Friday' },
        ],
      },
    ],
  },
  analyst: {
    title: 'Analyst home',
    subtitle: 'Exploratory analytics with intervention-to-outcome context.',
    rows: [
      {
        title: 'Top row',
        cards: [
          { label: 'Coverage', value: '88%', detail: 'Skills inferred for active workforce' },
          { label: 'Readiness index', value: '71', detail: '+4.1 from prior quarter' },
          { label: 'Proficiency uplift', value: '+8%', detail: 'Post-coaching cohorts' },
          { label: 'Mobility readiness', value: '42%', detail: 'At least one role match' },
        ],
      },
      {
        title: 'Main body',
        cards: [
          { label: 'Critical gap heatmap', value: '3 severe domains', detail: 'AI literacy, data governance, risk' },
          { label: 'Trend explorer', value: '12-mo narrative', detail: 'Intervention windows highlighted' },
          { label: 'Cohort comparison', value: '5 active cohorts', detail: 'Control vs intervention enabled' },
          { label: 'Outcome chain', value: '14 linked actions', detail: 'Prompt -> practice -> uplift' },
        ],
      },
    ],
  },
  manager: {
    title: 'Manager home',
    subtitle: 'Weekly action center for team coaching and readiness.',
    rows: [
      {
        title: 'Top row',
        cards: [
          { label: 'Team readiness score', value: '68', detail: 'Up 2 points this week' },
          { label: 'Assessments due', value: '7', detail: '3 overdue' },
          { label: 'New gap alerts', value: '5', detail: 'Most in workflow automation' },
          { label: 'Blocked opportunities', value: '4', detail: 'Skill gaps prevent internal moves' },
        ],
      },
      {
        title: 'Main body',
        cards: [
          { label: "This week's prompts", value: '11 generated', detail: '4 high-confidence suggestions' },
          { label: 'Top 5 team gaps', value: 'Visible', detail: 'Ordered by business impact' },
          { label: 'People needing support', value: '6 teammates', detail: 'Low confidence + low trend' },
          { label: 'Suggested projects', value: '9 tasks', detail: 'Mapped to role targets' },
        ],
      },
    ],
  },
  employee: {
    title: 'Employee home',
    subtitle: 'Personal growth dashboard with explainable progress.',
    rows: [
      {
        title: 'Top row',
        cards: [
          { label: 'Current role readiness', value: '74%', detail: 'On-track for expectations' },
          { label: 'Next role readiness', value: '61%', detail: 'Target: Senior Analyst' },
          { label: 'Assessment status', value: '2 pending', detail: 'One closes in 3 days' },
          { label: 'Weekly progress', value: '+3 points', detail: 'Driven by project artifact' },
        ],
      },
      {
        title: 'Main body',
        cards: [
          { label: 'Skill profile', value: '24 skills tracked', detail: '5 with low confidence' },
          { label: 'Plan for this week', value: '4 guided tasks', detail: '2 coaching prompts' },
          { label: 'Evidence to submit', value: '3 suggestions', detail: 'Artifacts or reflections' },
          { label: 'Opportunities', value: '2 unlocked', detail: '3 close to unlocked' },
        ],
      },
    ],
  },
}

const DECISION_CARDS = {
  admin: [
    {
      headline: 'Prioritize identity remediation in Customer Support',
      rationale: 'Unmatched identities are reducing evidence confidence in two job families.',
      evidence: ['HRIS sync delta', 'IdP overlap report', 'Assessment attempts'],
      confidence: 0.9,
      sourceCount: 4,
      updatedAt: '2026-04-10 14:20 UTC',
      modelInfo: 'IdentityResolver v2.4',
      advisory: 'Decision-impacting',
    },
    {
      headline: 'Approve taxonomy update for AI workflow skills',
      rationale: 'Recent project evidence shows repeated signals not represented in current taxonomy.',
      evidence: ['Project artifacts', 'Manager feedback', 'Inference conflict report'],
      confidence: 0.82,
      sourceCount: 3,
      updatedAt: '2026-04-11 08:12 UTC',
      modelInfo: 'TaxonomyAssist v1.9',
      advisory: 'Advisory',
    },
  ],
  analyst: [
    {
      headline: 'Investigate confidence skew for EMEA cohort',
      rationale: 'Readiness uplift appears strong, but confidence range is significantly wider than peers.',
      evidence: ['Cohort trend line', 'Evidence composition chart', 'Data quality flags'],
      confidence: 0.79,
      sourceCount: 5,
      updatedAt: '2026-04-11 09:05 UTC',
      modelInfo: 'AnalyticsNarrative v3.1',
      advisory: 'Decision-impacting',
    },
  ],
  manager: [
    {
      headline: 'Assign targeted practice to unblock role readiness',
      rationale: 'Three team members are within one proficiency level of target role requirements.',
      evidence: ['Skill gap matrix', 'Assessment outcomes', 'Project task history'],
      confidence: 0.86,
      sourceCount: 6,
      updatedAt: '2026-04-11 07:40 UTC',
      modelInfo: 'CoachingPlanner v2.0',
      advisory: 'Advisory',
    },
    {
      headline: 'Hold 1:1 on data storytelling competency',
      rationale: 'Performance trend dipped after recent project transition.',
      evidence: ['Trend arrow', 'Manager observations', 'Presentation rubric'],
      confidence: 0.72,
      sourceCount: 3,
      updatedAt: '2026-04-10 17:52 UTC',
      modelInfo: 'SignalFusion v1.5',
      advisory: 'Advisory',
    },
  ],
  employee: [
    {
      headline: 'Complete scenario assessment for workflow optimization',
      rationale: 'Completing this assessment can increase next-role readiness by an estimated 6 points.',
      evidence: ['Role benchmark', 'Learning completion history', 'Current skill confidence'],
      confidence: 0.84,
      sourceCount: 5,
      updatedAt: '2026-04-11 06:15 UTC',
      modelInfo: 'GrowthGuide v1.7',
      advisory: 'Advisory',
    },
  ],
}

const SKILL_MAP = [
  { domain: 'Technical', skill: 'Data modeling', inferred: 'L3', target: 'L4', gap: 1, confidence: 'High', trend: 'Up', evidence: 9 },
  { domain: 'Technical', skill: 'Workflow automation', inferred: 'L2', target: 'L4', gap: 2, confidence: 'Medium', trend: 'Flat', evidence: 6 },
  { domain: 'Domain', skill: 'Regulatory literacy', inferred: 'L2', target: 'L3', gap: 1, confidence: 'High', trend: 'Up', evidence: 7 },
  { domain: 'Leadership', skill: 'Coaching peers', inferred: 'L2', target: 'L3', gap: 1, confidence: 'Medium', trend: 'Up', evidence: 4 },
  { domain: 'Workflow / Process', skill: 'Cross-team planning', inferred: 'L3', target: 'L4', gap: 1, confidence: 'Medium', trend: 'Flat', evidence: 5 },
  { domain: 'AI / Digital', skill: 'Prompt engineering', inferred: 'L1', target: 'L3', gap: 2, confidence: 'Low', trend: 'Up', evidence: 3 },
]

const EVIDENCE_TIMELINE = [
  { type: 'Assessment result', detail: 'Scenario assessment: 78%', date: '2026-04-05' },
  { type: 'Learning completion', detail: 'Advanced analytics pathway', date: '2026-04-03' },
  { type: 'Project artifact', detail: 'Quarterly forecast notebook', date: '2026-03-29' },
  { type: 'Manager feedback', detail: 'Strong communication in stakeholder review', date: '2026-03-26' },
  { type: 'External certification', detail: 'Data governance practitioner', date: '2026-03-14' },
]

const SETUP_STEPS = [
  { name: 'Connect source systems', eta: '15 min', permissions: 'Tenant admin', data: 'HRIS, LMS, ATS, IdP', mutable: 'Can re-auth and add connectors later' },
  { name: 'Select business unit / scope', eta: '5 min', permissions: 'BU owner', data: 'Org hierarchy', mutable: 'Can expand or narrow scope later' },
  { name: 'Pick job family', eta: '5 min', permissions: 'HR admin', data: 'Role catalog', mutable: 'Additional families can be onboarded' },
  { name: 'Review imported roles', eta: '10 min', permissions: 'HR analyst', data: 'Role metadata', mutable: 'Role mappings are editable post-launch' },
  { name: 'Generate/import skills taxonomy', eta: '20 min', permissions: 'Taxonomy editor', data: 'Existing skill dictionary', mutable: 'Versioned taxonomy allows rollback' },
  { name: 'Set proficiency scale', eta: '5 min', permissions: 'HR admin', data: 'Scale configuration', mutable: 'Scale updates trigger version history' },
  { name: 'Review evidence rules', eta: '15 min', permissions: 'Governance lead', data: 'Evidence source policy', mutable: 'Rules can be tuned with audit logs' },
  { name: 'Preview sample profiles', eta: '8 min', permissions: 'Pilot manager', data: 'Synthetic + pilot records', mutable: 'Can regenerate preview anytime' },
  { name: 'Approve and launch baseline', eta: '3 min', permissions: 'Program owner', data: 'Launch checklist', mutable: 'Baseline snapshots stay immutable' },
]

const ASSESSMENT_ITEM_TYPES = ['Multiple choice', 'Scenario response', 'Artifact upload', 'Reflection', 'Live rubric input']
const ASSESSMENT_VALIDATIONS = ['Blueprint coverage check', 'Skill mapping completeness', 'Rubric weight balance', 'Accessibility warnings']
const ANALYTICS_TABS = [
  'Coverage',
  'Gap hotspots',
  'Proficiency distribution',
  'Readiness trend',
  'Assessment outcomes',
  'Coaching effectiveness',
  'Mobility readiness',
  'Governance / fairness',
]
const DOMAIN_COMPONENTS = [
  'Skill proficiency matrix',
  'Evidence timeline',
  'Confidence meter',
  'Lineage drawer',
  'Recommendation card',
  'Cohort compare table',
  'Gap heatmap',
  'Assessment blueprint builder',
  'Role-to-skill mapper',
  'Opportunity match rationale panel',
  'Governance rule editor',
  'Audit log explorer',
  'KPI card with baseline delta',
  'Intervention timeline',
]

/**
 * Render one trust-forward recommendation card.
 * // Line comment: this reusable card keeps explainability visible in every workflow.
 */
function DecisionCard({ card }) {
  // Line comment: confidence is formatted into a readable percentage badge.
  const confidenceText = `${Math.round(card.confidence * 100)}% confidence`
  return (
    <article className="decision-card">
      <div className="decision-header">
        <h4>{card.headline}</h4>
        <span className="confidence-badge">{confidenceText}</span>
      </div>
      <p>{card.rationale}</p>
      <div className="chip-row">
        {card.evidence.map((item) => (
          <span key={item} className="pill">
            {item}
          </span>
        ))}
      </div>
      <div className="decision-metadata">
        <span>Source count: {card.sourceCount}</span>
        <span>Last updated: {card.updatedAt}</span>
        <span>Model: {card.modelInfo}</span>
        <span>{card.advisory}</span>
      </div>
      <div className="decision-actions">
        <button type="button">View lineage</button>
        <button type="button">Override / acknowledge</button>
        <button type="button">Audit details</button>
      </div>
    </article>
  )
}

/**
 * Render one KPI card for cockpit and workspace surfaces.
 * // Line comment: cards are intentionally dense but structured for quick scanning.
 */
function KpiCard({ card }) {
  // Line comment: detail text surfaces context without opening a side panel.
  return (
    <article className="kpi-card">
      <h4>{card.label}</h4>
      <p className="kpi-value">{card.value}</p>
      <p className="kpi-detail">{card.detail}</p>
    </article>
  )
}

/**
 * Render persona-specific home content rows.
 * // Line comment: home pages mirror the product spec's role-based landing experience.
 */
function LandingPage({ persona }) {
  // Line comment: fallback prevents rendering issues when persona is switched quickly.
  const content = LANDING_ROWS[persona] || LANDING_ROWS.manager
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>{content.title}</h2>
        <p className="muted-text">{content.subtitle}</p>
      </div>
      {content.rows.map((row) => (
        <div key={row.title} className="panel">
          <h3>{row.title}</h3>
          <div className="kpi-grid">
            {row.cards.map((card) => (
              <KpiCard key={card.label} card={card} />
            ))}
          </div>
        </div>
      ))}
      <div className="panel">
        <h3>Decision cards</h3>
        <div className="decision-grid">
          {(DECISION_CARDS[persona] || []).map((card) => (
            <DecisionCard key={card.headline} card={card} />
          ))}
        </div>
      </div>
    </section>
  )
}

/**
 * Render the signature skill profile screen with five vertical sections.
 * // Line comment: this layout anchors evidence, confidence, and actionability together.
 */
function SkillProfilePage() {
  // Line comment: skill rows are grouped by domain to keep scan patterns predictable.
  const groupedRows = SKILL_MAP.reduce((collection, row) => {
    const nextCollection = { ...collection }
    const current = nextCollection[row.domain] || []
    nextCollection[row.domain] = [...current, row]
    return nextCollection
  }, {})

  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Skill Profile: Maya Chen</h2>
        <div className="profile-header-grid">
          <p>Role: Senior Operations Analyst</p>
          <p>Job family: Operations Excellence</p>
          <p>Manager: Tomas Reid</p>
          <p>Last updated: 2026-04-11 08:02 UTC</p>
          <p>Overall readiness: 74%</p>
          <p>Governance state: Consent active / explainable mode</p>
        </div>
      </div>
      <div className="panel">
        <h3>Skill map</h3>
        {Object.entries(groupedRows).map(([domain, rows]) => (
          <div key={domain} className="domain-block">
            <h4>{domain}</h4>
            <table>
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Inferred</th>
                  <th>Target</th>
                  <th>Gap</th>
                  <th>Confidence</th>
                  <th>Trend</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={`${domain}-${row.skill}`}>
                    <td>{row.skill}</td>
                    <td>{row.inferred}</td>
                    <td>{row.target}</td>
                    <td>{row.gap}</td>
                    <td>{row.confidence}</td>
                    <td>{row.trend}</td>
                    <td>{row.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
      <div className="panel">
        <h3>Evidence panel</h3>
        <ul className="timeline-list">
          {EVIDENCE_TIMELINE.map((item) => (
            <li key={`${item.type}-${item.date}`}>
              <span>{item.date}</span>
              <strong>{item.type}</strong>
              <p>{item.detail}</p>
            </li>
          ))}
        </ul>
      </div>
      <div className="panel">
        <h3>Explanation panel</h3>
        <p>
          This skill estimate is based on recent assessments, work artifacts, and manager observations.
        </p>
        <ul className="simple-list">
          <li>Confidence drivers: recent project evidence, role-aligned assessments, improved trend.</li>
          <li>Conflicting signals: low evidence density for AI / Digital skills.</li>
          <li>Freshness warning: last external certification is older than 90 days.</li>
          <li>Version lineage: SignalFusion v1.5 with Taxonomy v2026.04.</li>
        </ul>
      </div>
      <div className="panel">
        <h3>Actions rail</h3>
        <div className="action-grid">
          <button type="button">Assign assessment</button>
          <button type="button">Create coaching plan</button>
          <button type="button">Suggest learning</button>
          <button type="button">Compare to target role</button>
          <button type="button">Export profile</button>
          <button type="button">Request review / challenge inference</button>
        </div>
      </div>
    </section>
  )
}

/**
 * Render first-class assessments authoring, delivery, and results.
 * // Line comment: the UI mirrors backend separation across authoring and evidence publishing.
 */
function AssessmentsPage() {
  // Line comment: all three sections stay visible to communicate lifecycle connectivity.
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Assessment Studio</h2>
        <div className="three-pane">
          <div>
            <h3>Blueprint structure</h3>
            <ul className="simple-list">
              <li>Section 1: Role fundamentals</li>
              <li>Section 2: Workflow simulation</li>
              <li>Section 3: Reflection and artifact</li>
            </ul>
          </div>
          <div>
            <h3>Item editor</h3>
            <ul className="simple-list">
              {ASSESSMENT_ITEM_TYPES.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Rubric and skill mapping</h3>
            <ul className="simple-list">
              <li>Role-specific forms enabled</li>
              <li>Version compare available</li>
              <li>Publish workflow with approvals</li>
            </ul>
          </div>
        </div>
      </div>
      <div className="panel">
        <h3>Validation warnings</h3>
        <div className="chip-row">
          {ASSESSMENT_VALIDATIONS.map((item) => (
            <span key={item} className="pill">
              {item}
            </span>
          ))}
        </div>
        <h3>Delivery mode</h3>
        <ul className="simple-list">
          <li>One-question or section-based mode</li>
          <li>Visible progress with autosave and resume</li>
          <li>Accommodation support and optional time rules</li>
          <li>Clear explanation of how responses are used</li>
        </ul>
      </div>
      <div className="panel">
        <h3>Results screen</h3>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Score summary', value: '78%', detail: 'Reliability: 0.84' }} />
          <KpiCard card={{ label: 'Strengths', value: '3', detail: 'Analysis, communication, planning' }} />
          <KpiCard card={{ label: 'Growth areas', value: '2', detail: 'Automation and AI literacy' }} />
          <KpiCard card={{ label: 'Next actions', value: '4', detail: 'Mapped to weekly plan' }} />
        </div>
      </div>
    </section>
  )
}

/**
 * Render coaching workflows for manager and employee action loops.
 * // Line comment: coaching cards link team gaps directly to interventions.
 */
function CoachingPage({ persona }) {
  // Line comment: manager and employee copy tone shifts while using shared design patterns.
  const isManagerSurface = persona === 'manager'
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>{isManagerSurface ? 'Weekly coaching pack' : 'Personalized weekly plan'}</h2>
        <p className="muted-text">
          {isManagerSurface
            ? 'Top team gaps, prompts, and 1:1 talking points in one operational flow.'
            : 'Clear weekly actions tied to role targets, evidence quality, and confidence.'}
        </p>
      </div>
      <div className="panel">
        <h3>Trust-forward recommendations</h3>
        <div className="decision-grid">
          {(DECISION_CARDS[persona] || DECISION_CARDS.employee).map((card) => (
            <DecisionCard key={card.headline} card={card} />
          ))}
        </div>
      </div>
    </section>
  )
}

/**
 * Render internal mobility readiness and opportunity rationale.
 * // Line comment: opportunity matching keeps evidence and confidence visible.
 */
function MobilityPage() {
  // Line comment: list layout makes it easy to compare near-match opportunities.
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Mobility readiness</h2>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Open opportunities', value: '12', detail: 'Filtered by role family and region' }} />
          <KpiCard card={{ label: 'Ready now', value: '3', detail: 'Match confidence above 85%' }} />
          <KpiCard card={{ label: 'Close to unlock', value: '5', detail: 'Within one skill level of target' }} />
          <KpiCard card={{ label: 'Blocked', value: '4', detail: 'Requires assessment evidence refresh' }} />
        </div>
      </div>
      <div className="panel">
        <h3>Opportunity match rationale panel</h3>
        <ul className="simple-list">
          <li>Role: Senior Process Analyst - Match 88% (confidence high)</li>
          <li>Why you match: strong planning and stakeholder evidence, verified in last 30 days</li>
          <li>Gap to close: workflow automation L2 to L3</li>
          <li>Recommended intervention: scenario assessment + guided project</li>
          <li>Governance note: advisory recommendation, manager approval required</li>
        </ul>
      </div>
    </section>
  )
}

/**
 * Render narrative-friendly analytics and longitudinal exploration.
 * // Line comment: controls and drill-downs make intervention history first-class.
 */
function AnalyticsPage() {
  // Line comment: tabs mirror the product-level analytics domains from the spec.
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Analytics and longitudinal views</h2>
        <div className="control-grid">
          <label>
            Time range
            <input defaultValue="Last 12 months" />
          </label>
          <label>
            Job family
            <input defaultValue="Operations Excellence" />
          </label>
          <label>
            Team / region / level
            <input defaultValue="All / Global / IC+Manager" />
          </label>
          <label>
            Evidence type
            <input defaultValue="Assessment + project + feedback" />
          </label>
          <label>
            Assessment cohort
            <input defaultValue="Q2 pilot cohort" />
          </label>
          <label>
            Control vs intervention
            <input defaultValue="Control enabled" />
          </label>
        </div>
      </div>
      <div className="panel">
        <h3>Main canvas tabs</h3>
        <div className="chip-row">
          {ANALYTICS_TABS.map((item) => (
            <span key={item} className="pill">
              {item}
            </span>
          ))}
        </div>
        <h3>Drill-down behavior</h3>
        <ul className="simple-list">
          <li>Cohort details with evidence composition</li>
          <li>Intervention history linked to trend inflections</li>
          <li>Data quality notes and confidence bands</li>
          <li>Export package for compliance and reviews</li>
        </ul>
      </div>
      <div className="panel">
        <h3>Longitudinal analysis patterns</h3>
        <ul className="simple-list">
          <li>Trend lines and cohort retention curves</li>
          <li>Before/after intervention comparisons</li>
          <li>Waterfall chart for gap closure</li>
          <li>Confidence-banded readiness forecast</li>
          <li>Last successful snapshot with audit-linked completion events</li>
        </ul>
      </div>
    </section>
  )
}

/**
 * Render governance, audit, and fairness controls.
 * // Line comment: governance state is visible from shell down to record-level actions.
 */
function GovernancePage() {
  // Line comment: queue-style sections highlight operational compliance workflows.
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Governance center</h2>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Consent coverage', value: '97.2%', detail: '1.1% awaiting refresh' }} />
          <KpiCard card={{ label: 'Access policy', value: 'Compliant', detail: 'No critical violations open' }} />
          <KpiCard card={{ label: 'Retention policy', value: '2 exceptions', detail: 'Escalated to data steward' }} />
          <KpiCard card={{ label: 'Bias review cadence', value: 'Monthly', detail: 'Next review in 6 days' }} />
        </div>
      </div>
      <div className="panel">
        <h3>Audit log explorer</h3>
        <ul className="simple-list">
          <li>2026-04-11 08:11 UTC - Recommendation overridden by HR Admin (ticket GOV-1182)</li>
          <li>2026-04-10 15:44 UTC - Fairness threshold update approved by Governance Lead</li>
          <li>2026-04-10 09:23 UTC - Role mapping export generated for compliance review</li>
          <li>2026-04-09 18:02 UTC - Retention rule exception acknowledged</li>
        </ul>
      </div>
    </section>
  )
}

/**
 * Render admin setup workflows, integrations, and design-system primitives.
 * // Line comment: setup wizard is optimized for pilot-first onboarding speed.
 */
function AdminPage() {
  // Line comment: integration and wizard content aligns to enterprise implementation requirements.
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Integrations and data quality</h2>
        <div className="chip-row">
          <span className="pill">HRIS</span>
          <span className="pill">LMS / LXP</span>
          <span className="pill">ATS</span>
          <span className="pill">IdP</span>
          <span className="pill">External assessments</span>
        </div>
      </div>
      <div className="panel">
        <h3>Job family setup wizard</h3>
        <table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Expected time</th>
              <th>Required permissions</th>
              <th>Data used</th>
              <th>What can change later</th>
            </tr>
          </thead>
          <tbody>
            {SETUP_STEPS.map((step) => (
              <tr key={step.name}>
                <td>{step.name}</td>
                <td>{step.eta}</td>
                <td>{step.permissions}</td>
                <td>{step.data}</td>
                <td>{step.mutable}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h3>Most important reusable components</h3>
        <div className="chip-row">
          {DOMAIN_COMPONENTS.map((component) => (
            <span key={component} className="pill">
              {component}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

/**
 * SkillsAI frontend root component.
 * // Line comment: this shell provides the two-surface enterprise experience on one design system.
 */
function App() {
  // Line comment: track the current product surface and role context.
  const [activeSurface, setActiveSurface] = useState('control')
  const [activePersona, setActivePersona] = useState('admin')
  const [activeNavItem, setActiveNavItem] = useState('Home')
  const [tenant, setTenant] = useState('Acme Global')
  const [searchText, setSearchText] = useState('')
  const [viewAs, setViewAs] = useState('Current role')

  const personaOptions = useMemo(() => PERSONA_BY_SURFACE[activeSurface] || [], [activeSurface])
  const navigationItems = useMemo(() => ROLE_NAVIGATION[activePersona] || ROLE_NAVIGATION.admin, [activePersona])

  /**
   * Update active surface and reset to valid role/navigation defaults.
   * // Line comment: each surface has dedicated personas and role-aware navigation.
   */
  function handleSurfaceChange(surfaceId) {
    // Line comment: first persona in each surface becomes the default when switching surfaces.
    const defaultPersona = PERSONA_BY_SURFACE[surfaceId]?.[0]?.id || 'admin'
    setActiveSurface(surfaceId)
    setActivePersona(defaultPersona)
    setActiveNavItem('Home')
  }

  /**
   * Update the selected persona in the current surface.
   * // Line comment: changing persona resets the page to Home for clarity.
   */
  function handlePersonaChange(personaId) {
    // Line comment: reset keeps navigation state consistent across role transitions.
    setActivePersona(personaId)
    setActiveNavItem('Home')
  }

  /**
   * Render the main workspace page based on current navigation state.
   * // Line comment: every route shares design primitives to preserve coherence.
   */
  function renderActivePage() {
    // Line comment: switch statement keeps route-to-page mapping explicit and readable.
    switch (activeNavItem) {
      case 'Home':
        return <LandingPage persona={activePersona} />
      case 'Skills':
        return <SkillProfilePage />
      case 'Assessments':
        return <AssessmentsPage />
      case 'Coaching':
        return <CoachingPage persona={activePersona} />
      case 'Mobility':
        return <MobilityPage />
      case 'Analytics':
        return <AnalyticsPage />
      case 'Governance':
        return <GovernancePage />
      case 'Admin':
        return <AdminPage />
      default:
        return <LandingPage persona={activePersona} />
    }
  }

  return (
    <main className="skills-shell">
      <header className="shell-header panel">
        <div>
          <p className="eyebrow">SkillsAI</p>
          <h1>Trusted workforce operating system</h1>
          <p className="muted-text">
            Analytical for admins, actionable for managers, motivating for employees, and explainable everywhere.
          </p>
        </div>
        <div className="governance-tag">Governance status: Healthy</div>
      </header>

      <section className="panel shell-controls">
        <label>
          Global search
          <input
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value)
            }}
            placeholder="Search people, skills, roles, assessments, or audit events"
          />
        </label>
        <label>
          Tenant / BU switcher
          <select
            value={tenant}
            onChange={(event) => {
              setTenant(event.target.value)
            }}
          >
            <option>Acme Global</option>
            <option>Acme Europe</option>
            <option>Acme North America</option>
          </select>
        </label>
        <label>
          View as
          <select
            value={viewAs}
            onChange={(event) => {
              setViewAs(event.target.value)
            }}
          >
            <option>Current role</option>
            <option>Manager view</option>
            <option>Employee view</option>
            <option>Analyst view</option>
          </select>
        </label>
        <div className="notification-box" role="status" aria-live="polite">
          Notifications: 7
        </div>
      </section>

      <section className="panel">
        <h2>Surface selector</h2>
        <div className="surface-toggle">
          {SURFACE_OPTIONS.map((surface) => (
            <button
              key={surface.id}
              type="button"
              className={surface.id === activeSurface ? 'active' : ''}
              onClick={() => {
                handleSurfaceChange(surface.id)
              }}
            >
              <strong>{surface.label}</strong>
              <span>{surface.subtitle}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Shared entity model in UI</h2>
        <div className="chip-row">
          {ENTITY_MODEL.map((item) => (
            <span key={item} className="pill">
              {item}
            </span>
          ))}
        </div>
      </section>

      <div className="workspace-layout">
        <aside className="panel sidebar">
          <h3>Role-aware navigation</h3>
          <label>
            Active persona
            <select
              value={activePersona}
              onChange={(event) => {
                handlePersonaChange(event.target.value)
              }}
            >
              {personaOptions.map((persona) => (
                <option key={persona.id} value={persona.id}>
                  {persona.label}
                </option>
              ))}
            </select>
          </label>
          <nav>
            <ul>
              {navigationItems.map((item) => (
                <li key={item}>
                  <button
                    type="button"
                    className={item === activeNavItem ? 'active' : ''}
                    onClick={() => {
                      setActiveNavItem(item)
                    }}
                  >
                    {item}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <section className="workspace-main">{renderActivePage()}</section>
      </div>
    </main>
  )
}

export default App
