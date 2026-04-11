import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  fetchAdminSummary,
  fetchAnalyticsSnapshot,
  fetchAssessmentWorkspace,
  fetchBackendHealth,
  fetchCoachingRecommendations,
  fetchGovernanceSummary,
  fetchIdentityProfile,
  fetchSkillStates,
} from './api/skillsaiClient'

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
  analyst: ['Home', 'Skills', 'Assessments', 'Mobility', 'Analytics', 'Governance', 'Admin'],
  manager: ['Home', 'Skills', 'Assessments', 'Coaching', 'Mobility', 'Analytics', 'Governance', 'Admin'],
  employee: ['Home', 'Skills', 'Assessments', 'Coaching', 'Mobility', 'Analytics'],
}

const ENTITY_MODEL = ['person', 'skill', 'assessment', 'recommendation', 'analytics snapshot', 'audit event']

const PERSONA_SESSION = {
  admin: { actorId: 'manager-1', employeeId: 'emp-1', token: 'manager-1:default', viewAs: 'HR Admin' },
  analyst: { actorId: 'manager-1', employeeId: 'emp-1', token: 'manager-1:default', viewAs: 'Analyst' },
  manager: { actorId: 'manager-1', employeeId: 'emp-1', token: 'manager-1:default', viewAs: 'Manager' },
  employee: { actorId: 'emp-1', employeeId: 'emp-1', token: 'emp-1:default', viewAs: 'Employee' },
}

/**
 * Create the empty backend workspace state used before live data is loaded.
 * // Line comment: this prevents render-time null checks from spreading throughout the UI.
 */
function createEmptyWorkspaceData() {
  // Line comment: keep every page backed by a predictable object shape.
  return {
    health: {},
    identity: {},
    skills: {},
    coaching: { employee_id: '', recommendations: [] },
    assessment: {},
    assessmentAttempt: {},
    analytics: {
      kpi: {},
      trend: {},
      planning: {},
    },
    governance: {},
    admin: {},
  }
}

/**
 * Format one backend ratio or decimal into a readable percentage.
 * // Line comment: the backend returns fractional values for skill and analytics metrics.
 */
function formatPercentage(value) {
  // Line comment: fallback to a placeholder when the backend has no value yet.
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'n/a'
  }
  return `${Math.round(Number(value) * 100)}%`
}

/**
 * Convert a seeded skill id into a human-readable label.
 * // Line comment: seed-data uses ids like `skill:python` that are not presentation friendly.
 */
function formatSkillLabel(skillId) {
  // Line comment: normalize the technical seed identifier into title-like text.
  return String(skillId)
    .replace(/^skill:/, '')
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

/**
 * Build the home-page KPI cards from live backend responses.
 * // Line comment: the landing page should summarize backend state instead of fixed mock metrics.
 */
function createHomeCards(workspace) {
  // Line comment: derive lightweight KPIs from the fetched backend payloads.
  const skillRows = Object.values(workspace.skills || {})
  const recommendationCount = workspace.coaching?.recommendations?.length || 0
  const attemptScore = workspace.assessmentAttempt?.scores?.final
  const analyticsValue = workspace.analytics?.kpi?.data?.value
  return [
    {
      label: 'Backend status',
      value: workspace.health?.status || 'unknown',
      detail: workspace.health?.service || 'FastAPI health endpoint',
    },
    {
      label: 'Skills tracked',
      value: String(skillRows.length),
      detail: `Subject employee: ${workspace.coaching?.employee_id || 'emp-1'}`,
    },
    {
      label: 'Coaching recommendations',
      value: String(recommendationCount),
      detail: 'Returned from activation-services seed data',
    },
    {
      label: 'Latest assessment score',
      value: formatPercentage(attemptScore),
      detail: workspace.assessmentAttempt?.session?.status || 'No attempt status available',
    },
    {
      label: 'Coverage KPI',
      value: formatPercentage(analyticsValue),
      detail: workspace.analytics?.kpi?.metric || 'skill_coverage',
    },
    {
      label: 'Audit events',
      value: String(workspace.governance?.audit_count || 0),
      detail: `Taxonomy: ${workspace.governance?.active_taxonomy_version || 'unknown'}`,
    },
  ]
}

/**
 * Render one trust-forward recommendation card.
 * // Line comment: recommendation cards now reflect live activation-service responses.
 */
function DecisionCard({ recommendation, personaLabel }) {
  // Line comment: convert backend priority scores into a readable confidence-style badge.
  const confidenceText = formatPercentage(recommendation.priority)
  return (
    <article className="decision-card">
      <div className="decision-header">
        <h4>{formatSkillLabel(recommendation.skill_id)}</h4>
        <span className="confidence-badge">{confidenceText}</span>
      </div>
      <p>
        {personaLabel} should focus on <strong>{formatSkillLabel(recommendation.skill_id)}</strong> next.
      </p>
      <div className="chip-row">
        <span className="pill">{recommendation.type || 'coaching'}</span>
        <span className="pill">Seed-backed recommendation</span>
        <span className="pill">Live backend API</span>
      </div>
      <div className="decision-metadata">
        <span>Skill id: {recommendation.skill_id}</span>
        <span>Priority: {recommendation.priority}</span>
        <span>Source: activation-services</span>
        <span>Advisory only</span>
      </div>
    </article>
  )
}

/**
 * Render one KPI card for cockpit and workspace surfaces.
 * // Line comment: cards keep backend response summaries easy to scan.
 */
function KpiCard({ card }) {
  // Line comment: detail text surfaces context without requiring a secondary panel.
  return (
    <article className="kpi-card">
      <h4>{card.label}</h4>
      <p className="kpi-value">{card.value}</p>
      <p className="kpi-detail">{card.detail}</p>
    </article>
  )
}

/**
 * Render the live backend-backed landing page.
 * // Line comment: this page summarizes identity, skills, coaching, analytics, and governance responses.
 */
function LandingPage({ personaLabel, workspace }) {
  // Line comment: derive top-level KPI cards from the aggregated backend workspace state.
  const cards = createHomeCards(workspace)
  const recommendations = workspace.coaching?.recommendations || []
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>{personaLabel} home</h2>
        <p className="muted-text">
          This page is now assembled from live backend APIs seeded from the shared `seed-data` folder.
        </p>
      </div>
      <div className="panel">
        <h3>Workspace summary</h3>
        <div className="kpi-grid">
          {cards.map((card) => (
            <KpiCard key={card.label} card={card} />
          ))}
        </div>
      </div>
      <div className="panel">
        <h3>Identity and tenant context</h3>
        <div className="profile-header-grid">
          <p>Actor id: {workspace.identity?.actor_id || 'n/a'}</p>
          <p>Tenant: {workspace.identity?.tenant_id || 'n/a'}</p>
          <p>Roles: {(workspace.identity?.roles || []).join(', ') || 'n/a'}</p>
          <p>Seed data dir: {workspace.admin?.seed_data_dir || 'n/a'}</p>
        </div>
      </div>
      <div className="panel">
        <h3>Live recommendations</h3>
        <div className="decision-grid">
          {recommendations.length > 0 ? (
            recommendations.map((recommendation) => (
              <DecisionCard
                key={`${recommendation.skill_id}-${recommendation.priority}`}
                recommendation={recommendation}
                personaLabel={personaLabel}
              />
            ))
          ) : (
            <p className="muted-text">No coaching recommendations were returned by the backend.</p>
          )}
        </div>
      </div>
    </section>
  )
}

/**
 * Render the live skill profile from backend skill-state data.
 * // Line comment: this page shows the direct output of the core-intelligence read API.
 */
function SkillsPage({ workspace, searchText }) {
  // Line comment: filter skills locally so the global search box remains useful.
  const rows = Object.entries(workspace.skills || {})
    .map(([skillId, state]) => ({
      skillId,
      ...state,
    }))
    .filter((row) => {
      const normalizedSearch = searchText.trim().toLowerCase()
      if (!normalizedSearch) {
        return true
      }
      return `${row.skillId} ${row.explanation || ''}`.toLowerCase().includes(normalizedSearch)
    })
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Skill profile</h2>
        <div className="profile-header-grid">
          <p>Actor id: {workspace.identity?.actor_id || 'n/a'}</p>
          <p>Tenant: {workspace.identity?.tenant_id || 'n/a'}</p>
          <p>Active taxonomy: {workspace.governance?.active_taxonomy_version || 'n/a'}</p>
          <p>Skills returned: {rows.length}</p>
        </div>
      </div>
      <div className="panel">
        <h3>Seeded skill states</h3>
        <table>
          <thead>
            <tr>
              <th>Skill</th>
              <th>Proficiency</th>
              <th>Confidence</th>
              <th>Gap</th>
              <th>Model version</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.skillId}>
                <td>{formatSkillLabel(row.skillId)}</td>
                <td>{formatPercentage(row.proficiency)}</td>
                <td>{formatPercentage(row.confidence)}</td>
                <td>{formatPercentage(row.gap)}</td>
                <td>{row.model_version || 'n/a'}</td>
                <td>{row.explanation || 'No explanation provided.'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/**
 * Render the assessment page from live assessment package and attempt data.
 * // Line comment: the frontend now reads package structure and attempt state from backend APIs.
 */
function AssessmentsPage({ workspace }) {
  // Line comment: unpack the package and attempt data loaded from the gateway read path.
  const assessment = workspace.assessment || {}
  const assessmentAttempt = workspace.assessmentAttempt || {}
  const items = assessment.items || []
  const sections = assessment.blueprint?.sections || []
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Assessments</h2>
        <div className="kpi-grid">
          <KpiCard
            card={{
              label: 'Assessment id',
              value: assessment.assessment_id || 'n/a',
              detail: `Version ${assessment.version || 'n/a'}`,
            }}
          />
          <KpiCard
            card={{
              label: 'Attempt status',
              value: assessmentAttempt.session?.status || 'n/a',
              detail: assessmentAttempt.session?.attempt_id || 'No attempt id',
            }}
          />
          <KpiCard
            card={{
              label: 'Final score',
              value: formatPercentage(assessmentAttempt.scores?.final),
              detail: 'Returned from the attempts store',
            }}
          />
          <KpiCard
            card={{
              label: 'Items',
              value: String(items.length),
              detail: `${sections.length} seeded section(s)`,
            }}
          />
        </div>
      </div>
      <div className="panel">
        <h3>Blueprint</h3>
        <ul className="simple-list">
          {sections.map((section) => (
            <li key={section.name}>{section.name}</li>
          ))}
        </ul>
      </div>
      <div className="panel">
        <h3>Published items</h3>
        <table>
          <thead>
            <tr>
              <th>Item id</th>
              <th>Skill</th>
              <th>Prompt</th>
              <th>Seeded response</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{formatSkillLabel(item.skill_id)}</td>
                <td>{item.prompt}</td>
                <td>{String(workspace.assessmentAttempt?.responses?.[item.id] ?? 'n/a')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/**
 * Render coaching workflows from live backend recommendations.
 * // Line comment: activation recommendations replace the previous static decision cards.
 */
function CoachingPage({ workspace, personaLabel }) {
  // Line comment: read recommendations directly from the activation API response.
  const recommendations = workspace.coaching?.recommendations || []
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>{personaLabel} coaching workspace</h2>
        <p className="muted-text">
          Recommendations are now loaded from `/coaching` instead of embedded frontend arrays.
        </p>
      </div>
      <div className="panel">
        <h3>Recommendations</h3>
        <div className="decision-grid">
          {recommendations.length > 0 ? (
            recommendations.map((recommendation) => (
              <DecisionCard
                key={`${recommendation.skill_id}-${recommendation.priority}`}
                recommendation={recommendation}
                personaLabel={personaLabel}
              />
            ))
          ) : (
            <p className="muted-text">No coaching recommendations are available for this actor.</p>
          )}
        </div>
      </div>
    </section>
  )
}

/**
 * Render mobility readiness using the same live backend skill and coaching signals.
 * // Line comment: this page derives near-term mobility actions from skills plus recommendations.
 */
function MobilityPage({ workspace }) {
  // Line comment: combine coaching signals and skill gaps into a lightweight readiness view.
  const recommendations = workspace.coaching?.recommendations || []
  const skillCount = Object.keys(workspace.skills || {}).length
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Mobility readiness</h2>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Tracked skills', value: String(skillCount), detail: 'Pulled from `/skills`' }} />
          <KpiCard
            card={{
              label: 'Recommended actions',
              value: String(recommendations.length),
              detail: 'Pulled from `/coaching`',
            }}
          />
          <KpiCard
            card={{
              label: 'Current readiness signal',
              value: formatPercentage(workspace.analytics?.kpi?.data?.value),
              detail: 'Coverage KPI as a simple mobility proxy',
            }}
          />
          <KpiCard
            card={{
              label: 'Assessment support',
              value: formatPercentage(workspace.assessmentAttempt?.scores?.final),
              detail: 'Most recent seeded attempt score',
            }}
          />
        </div>
      </div>
      <div className="panel">
        <h3>Opportunity rationale</h3>
        <ul className="simple-list">
          {recommendations.map((recommendation) => (
            <li key={`mobility-${recommendation.skill_id}`}>
              Prioritize <strong>{formatSkillLabel(recommendation.skill_id)}</strong> with priority{' '}
              {formatPercentage(recommendation.priority)} to improve next-role readiness.
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/**
 * Render analytics views from live backend analytics queries.
 * // Line comment: each panel corresponds to a real `/analytics` request instead of mock copy.
 */
function AnalyticsPage({ workspace }) {
  // Line comment: unpack KPI, trend, and planning snapshots returned by the analytics container.
  const kpi = workspace.analytics?.kpi || {}
  const trend = workspace.analytics?.trend || {}
  const planning = workspace.analytics?.planning || {}
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Analytics and longitudinal views</h2>
        <div className="kpi-grid">
          <KpiCard
            card={{
              label: kpi.metric || 'Coverage metric',
              value: formatPercentage(kpi.data?.value),
              detail: `${kpi.cohort || 'all'} cohort`,
            }}
          />
          <KpiCard
            card={{
              label: 'Trend average',
              value: formatPercentage(trend.data?.average),
              detail: trend.metric || 'trend.skill_coverage',
            }}
          />
          <KpiCard
            card={{
              label: 'Planning target',
              value: String(planning.data?.target ?? 'n/a'),
              detail: planning.metric || 'plan.hiring_capacity',
            }}
          />
          <KpiCard
            card={{
              label: 'Trend points',
              value: String(trend.data?.series?.length || 0),
              detail: 'Loaded from analytics warehouse seed rows',
            }}
          />
        </div>
      </div>
      <div className="panel">
        <h3>Trend snapshot</h3>
        <ul className="simple-list">
          {(trend.data?.series || []).map((point, index) => (
            <li key={`trend-${index}`}>Point {index + 1}: {formatPercentage(point)}</li>
          ))}
        </ul>
      </div>
      <div className="panel">
        <h3>Planning snapshot</h3>
        <ul className="simple-list">
          <li>Conservative: {String(planning.data?.conservative ?? 'n/a')}</li>
          <li>Target: {String(planning.data?.target ?? 'n/a')}</li>
          <li>Aggressive: {String(planning.data?.aggressive ?? 'n/a')}</li>
        </ul>
      </div>
    </section>
  )
}

/**
 * Render governance state from the live backend governance summary.
 * // Line comment: this page now reads audit metadata rather than showing static audit lines.
 */
function GovernancePage({ workspace }) {
  // Line comment: unpack the governance payload returned by the gateway query path.
  const governance = workspace.governance || {}
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Governance center</h2>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Audit events', value: String(governance.audit_count || 0), detail: 'Total audit rows in store' }} />
          <KpiCard
            card={{
              label: 'Time-series events',
              value: String(governance.time_series_count || 0),
              detail: 'Signals and action history',
            }}
          />
          <KpiCard
            card={{
              label: 'Taxonomy version',
              value: governance.active_taxonomy_version || 'n/a',
              detail: 'Loaded from core-intelligence seed data',
            }}
          />
          <KpiCard
            card={{
              label: 'Seed source',
              value: governance.seed_data_dir || 'n/a',
              detail: 'Shared backend seed-data folder',
            }}
          />
        </div>
      </div>
      <div className="panel">
        <h3>Latest audit events</h3>
        <ul className="simple-list">
          {(governance.latest_audit_events || []).map((event, index) => (
            <li key={`audit-${index}`}>{JSON.stringify(event)}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/**
 * Render admin metadata from the live backend admin summary.
 * // Line comment: this page surfaces seed-data and module-loading metadata instead of hardcoded setup steps.
 */
function AdminPage({ workspace }) {
  // Line comment: unpack admin summary fields from the backend response.
  const admin = workspace.admin || {}
  return (
    <section className="page-grid">
      <div className="panel">
        <h2>Admin and seed-data configuration</h2>
        <div className="kpi-grid">
          <KpiCard card={{ label: 'Identity records', value: String(admin.identity_count || 0), detail: 'Loaded into cache from seed-data' }} />
          <KpiCard card={{ label: 'Assessment packages', value: String(admin.assessment_count || 0), detail: 'Loaded into the item bank' }} />
          <KpiCard card={{ label: 'Seed modules', value: String((admin.seed_modules || []).length), detail: (admin.seed_modules || []).join(', ') || 'n/a' }} />
          <KpiCard card={{ label: 'Request samples', value: String((admin.request_samples || []).length), detail: 'Loaded from platform seed-data' }} />
        </div>
      </div>
      <div className="panel">
        <h3>Available payloads</h3>
        <div className="chip-row">
          {Object.entries(admin.available_payloads || {}).map(([key, value]) => (
            <span key={key} className="pill">
              {key}: {value}
            </span>
          ))}
        </div>
      </div>
      <div className="panel">
        <h3>Published assessment ids</h3>
        <ul className="simple-list">
          {(admin.assessment_ids || []).map((assessmentId) => (
            <li key={assessmentId}>{assessmentId}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}

/**
 * SkillsAI frontend root component.
 * // Line comment: this shell now aggregates all substantive page data from backend API calls.
 */
function App() {
  // Line comment: track current surface, persona, and lightweight UI-only controls.
  const [activeSurface, setActiveSurface] = useState('control')
  const [activePersona, setActivePersona] = useState('admin')
  const [activeNavItem, setActiveNavItem] = useState('Home')
  const [searchText, setSearchText] = useState('')
  const [tenant, setTenant] = useState('default-tenant')
  const [workspace, setWorkspace] = useState(createEmptyWorkspaceData)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')

  const personaOptions = useMemo(() => PERSONA_BY_SURFACE[activeSurface] || [], [activeSurface])
  const navigationItems = useMemo(() => ROLE_NAVIGATION[activePersona] || ROLE_NAVIGATION.admin, [activePersona])
  const session = useMemo(() => PERSONA_SESSION[activePersona] || PERSONA_SESSION.employee, [activePersona])

  /**
   * Update active surface and reset persona/navigation to valid defaults.
   * // Line comment: each surface only supports the personas defined for that surface.
   */
  function handleSurfaceChange(surfaceId) {
    // Line comment: switch persona and navigation back to the first valid route for the selected surface.
    const defaultPersona = PERSONA_BY_SURFACE[surfaceId]?.[0]?.id || 'admin'
    setActiveSurface(surfaceId)
    setActivePersona(defaultPersona)
    setActiveNavItem('Home')
  }

  /**
   * Update active persona and reset navigation to the home page.
   * // Line comment: persona changes should trigger a fresh backend workspace load.
   */
  function handlePersonaChange(personaId) {
    // Line comment: reset the active page so the newly loaded workspace opens predictably.
    setActivePersona(personaId)
    setActiveNavItem('Home')
  }

  /**
   * Load the full backend workspace for the current persona session.
   * // Line comment: all substantive frontend data now flows through this API orchestration step.
   */
  async function loadWorkspaceData() {
    // Line comment: clear stale errors and show loading state before starting backend fetches.
    setLoading(true)
    setErrorMessage('')
    try {
      const [
        health,
        identity,
        skills,
        coaching,
        assessmentWorkspace,
        kpiAnalytics,
        trendAnalytics,
        planningAnalytics,
        governance,
        admin,
      ] = await Promise.all([
        fetchBackendHealth(),
        fetchIdentityProfile({
          employeeId: session.employeeId,
          actorId: session.actorId,
          token: session.token,
        }),
        fetchSkillStates({
          employeeId: session.employeeId,
          actorId: session.actorId,
          token: session.token,
        }),
        fetchCoachingRecommendations({
          employeeId: session.employeeId,
          actorId: session.actorId,
          token: session.token,
        }),
        fetchAssessmentWorkspace({
          assessmentId: 'asm-1',
          attemptId: 'attempt-1',
          actorId: session.actorId,
          token: session.token,
        }),
        fetchAnalyticsSnapshot({
          metric: 'skill_coverage',
          cohort: 'all',
          actorId: session.actorId,
          token: session.token,
        }),
        fetchAnalyticsSnapshot({
          metric: 'trend.skill_coverage',
          cohort: 'all',
          actorId: session.actorId,
          token: session.token,
        }),
        fetchAnalyticsSnapshot({
          metric: 'plan.hiring_capacity',
          cohort: 'engineering',
          actorId: session.actorId,
          token: session.token,
        }),
        fetchGovernanceSummary({
          actorId: session.actorId,
          token: session.token,
        }),
        fetchAdminSummary({
          actorId: session.actorId,
          token: session.token,
        }),
      ])
      // Line comment: store the aggregated backend workspace in one local state object.
      setWorkspace({
        health,
        identity,
        skills,
        coaching,
        assessment: assessmentWorkspace.assessment,
        assessmentAttempt: assessmentWorkspace.assessmentAttempt,
        analytics: {
          kpi: kpiAnalytics,
          trend: trendAnalytics,
          planning: planningAnalytics,
        },
        governance,
        admin,
      })
      setTenant(identity.tenant_id || 'default-tenant')
    } catch (error) {
      // Line comment: surface the backend error so the user can fix configuration quickly.
      setWorkspace(createEmptyWorkspaceData())
      setErrorMessage(error instanceof Error ? error.message : 'Unable to load backend workspace.')
    } finally {
      // Line comment: stop showing the loading state after all requests complete.
      setLoading(false)
    }
  }

  /**
   * Render the active page for the selected navigation item.
   * // Line comment: every page now consumes the same aggregated backend workspace object.
   */
  function renderActivePage() {
    // Line comment: route navigation items to the corresponding backend-driven page components.
    switch (activeNavItem) {
      case 'Home':
        return <LandingPage personaLabel={session.viewAs} workspace={workspace} />
      case 'Skills':
        return <SkillsPage workspace={workspace} searchText={searchText} />
      case 'Assessments':
        return <AssessmentsPage workspace={workspace} />
      case 'Coaching':
        return <CoachingPage workspace={workspace} personaLabel={session.viewAs} />
      case 'Mobility':
        return <MobilityPage workspace={workspace} />
      case 'Analytics':
        return <AnalyticsPage workspace={workspace} />
      case 'Governance':
        return <GovernancePage workspace={workspace} />
      case 'Admin':
        return <AdminPage workspace={workspace} />
      default:
        return <LandingPage personaLabel={session.viewAs} workspace={workspace} />
    }
  }

  useEffect(() => {
    void loadWorkspaceData()
  }, [session])

  return (
    <main className="skills-shell">
      <header className="shell-header panel">
        <div>
          <p className="eyebrow">SkillsAI</p>
          <h1>Trusted workforce operating system</h1>
          <p className="muted-text">
            Frontend pages are now backed by FastAPI routes seeded from the shared `seed-data` folder.
          </p>
        </div>
        <div className="governance-tag">
          Governance status: {workspace.health?.status || (loading ? 'Loading' : 'Unavailable')}
        </div>
      </header>

      <section className="panel shell-controls">
        <label>
          Global search
          <input
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value)
            }}
            placeholder="Filter skills and backend-backed content"
          />
        </label>
        <label>
          Active tenant
          <select value={tenant} onChange={(event) => setTenant(event.target.value)}>
            <option value={tenant}>{tenant}</option>
          </select>
        </label>
        <label>
          View as
          <select value={activePersona} onChange={(event) => handlePersonaChange(event.target.value)}>
            {personaOptions.map((persona) => (
              <option key={persona.id} value={persona.id}>
                {persona.label}
              </option>
            ))}
          </select>
        </label>
        <div className="notification-box" role="status" aria-live="polite">
          {loading ? 'Loading backend data...' : errorMessage ? 'Backend error detected' : 'Backend connected'}
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
        <h2>Backend workspace context</h2>
        <div className="chip-row">
          {ENTITY_MODEL.map((item) => (
            <span key={item} className="pill">
              {item}
            </span>
          ))}
        </div>
        <div className="profile-header-grid" style={{ marginTop: '12px' }}>
          <p>Actor: {session.actorId}</p>
          <p>Subject employee: {session.employeeId}</p>
          <p>Seed source: {workspace.admin?.seed_data_dir || 'n/a'}</p>
          <p>Health service: {workspace.health?.service || 'n/a'}</p>
        </div>
        {errorMessage ? <p className="muted-text">{errorMessage}</p> : null}
      </section>

      <div className="workspace-layout">
        <aside className="panel sidebar">
          <h3>Role-aware navigation</h3>
          <label>
            Active persona
            <select value={activePersona} onChange={(event) => handlePersonaChange(event.target.value)}>
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
