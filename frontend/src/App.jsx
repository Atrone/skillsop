import { useMemo, useState } from 'react'
import { buildGatewayRequest, fetchBackendHealth, sendGatewayRequest } from './api/skillsaiClient'
import './App.css'

/**
 * SkillsAI frontend root component.
 * // Line comment: this view provides a route workbench for backend gateway APIs.
 */
function App() {
  // Line comment: initialize default connection settings for the gateway workbench.
  const [baseUrl, setBaseUrl] = useState(import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8000')
  const [healthStatus, setHealthStatus] = useState('')
  const [healthPayload, setHealthPayload] = useState(null)
  const [healthError, setHealthError] = useState('')
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)
  const [actorId, setActorId] = useState('emp-1')
  const [token, setToken] = useState('valid-token')
  const [activeRoute, setActiveRoute] = useState('/analytics')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [identityPayload, setIdentityPayload] = useState({
    employee_id: 'emp-1',
  })
  const [skillsPayload, setSkillsPayload] = useState({
    employee_id: 'emp-1',
  })
  const [coachingPayload, setCoachingPayload] = useState({
    employee_id: 'emp-1',
  })
  const [assessmentReadPayload, setAssessmentReadPayload] = useState({
    attempt_id: 'attempt-1',
  })
  const [analyticsPayload, setAnalyticsPayload] = useState({
    metric: 'skill_coverage',
    cohort: 'all',
    start: '2026-01-01',
    end: '2026-12-31',
  })
  const [identityLinkPayload, setIdentityLinkPayload] = useState({
    external_id: 'hris-emp-1',
    employee_id: 'emp-1',
  })
  const [inferPayload, setInferPayload] = useState({
    employee_id: 'emp-1',
    skill_id: 'skill:python',
    value: '0.8',
    source: 'frontend',
    confidence_hint: '0.7',
    model_version: 'v1',
  })
  const [coachingCommandPayload, setCoachingCommandPayload] = useState({
    employee_id: 'emp-1',
    goal_skill: 'skill:python',
  })
  const [assessmentSubmitPayload, setAssessmentSubmitPayload] = useState({
    attempt_id: 'attempt-1',
    assessment_id: 'asm-1',
    employee_id: 'emp-1',
    responses: '{ "q1": true, "q2": false }',
  })
  const [materializePayload, setMaterializePayload] = useState({
    trigger: 'manual',
  })

  const routeDefinitions = useMemo(
    () => [
      { route: '/identity', method: 'GET', label: 'Read identity profile' },
      { route: '/skills', method: 'GET', label: 'Read inferred skills' },
      { route: '/coaching', method: 'GET', label: 'Read coaching recommendations' },
      { route: '/assessments', method: 'GET', label: 'Read assessment attempt' },
      { route: '/analytics', method: 'GET', label: 'Read analytics dashboard' },
      { route: '/command/identity/link', method: 'POST', label: 'Link external identity' },
      { route: '/command/core/infer', method: 'POST', label: 'Submit inference evidence' },
      { route: '/command/activation/coaching', method: 'POST', label: 'Create coaching action' },
      { route: '/command/assessments/submit', method: 'POST', label: 'Submit assessment attempt' },
      { route: '/command/analytics/materialize', method: 'POST', label: 'Trigger KPI materialization' },
    ],
    [],
  )

  /**
   * Build route payload from current UI state.
   * // Line comment: each route maps to backend command/query payload requirements.
   */
  function getPayloadForRoute(route) {
    if (route === '/identity') {
      return { employee_id: identityPayload.employee_id }
    }
    if (route === '/skills') {
      return { employee_id: skillsPayload.employee_id }
    }
    if (route === '/coaching') {
      return { employee_id: coachingPayload.employee_id }
    }
    if (route === '/assessments') {
      return { attempt_id: assessmentReadPayload.attempt_id }
    }
    if (route === '/analytics') {
      return {
        metric: analyticsPayload.metric,
        cohort: analyticsPayload.cohort,
        start: analyticsPayload.start,
        end: analyticsPayload.end,
      }
    }
    if (route === '/command/identity/link') {
      return {
        external_id: identityLinkPayload.external_id,
        employee_id: identityLinkPayload.employee_id,
      }
    }
    if (route === '/command/core/infer') {
      return {
        employee_id: inferPayload.employee_id,
        skill_id: inferPayload.skill_id,
        value: Number.parseFloat(inferPayload.value),
        source: inferPayload.source,
        confidence_hint: Number.parseFloat(inferPayload.confidence_hint),
        model_version: inferPayload.model_version,
      }
    }
    if (route === '/command/activation/coaching') {
      return {
        employee_id: coachingCommandPayload.employee_id,
        goal_skill: coachingCommandPayload.goal_skill,
      }
    }
    if (route === '/command/assessments/submit') {
      return {
        attempt_id: assessmentSubmitPayload.attempt_id,
        assessment_id: assessmentSubmitPayload.assessment_id,
        employee_id: assessmentSubmitPayload.employee_id,
        responses: safeParseJson(assessmentSubmitPayload.responses),
      }
    }
    if (route === '/command/analytics/materialize') {
      return { trigger: materializePayload.trigger }
    }
    return {}
  }

  /**
   * Parse JSON text into a value with fallback.
   * // Line comment: invalid JSON defaults to an empty object so request still sends.
   */
  function safeParseJson(value) {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }

  /**
   * Execute the selected gateway route against backend.
   * // Line comment: sends request using either form-provided or env base URL.
   */
  async function handleRunRequest(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    setResult(null)

    const definition = routeDefinitions.find((item) => item.route === activeRoute)
    const requestPayload = buildGatewayRequest(
      definition?.method || 'GET',
      activeRoute,
      actorId,
      token,
      getPayloadForRoute(activeRoute),
    )

    try {
      const data = await sendGatewayRequest(requestPayload, baseUrl)
      setResult({
        request: requestPayload,
        response: data,
      })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Request failed.')
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Check backend health against the FastAPI health endpoint.
   * // Line comment: this confirms connectivity before sending gateway requests.
   */
  async function handleHealthCheck() {
    setIsCheckingHealth(true)
    setHealthError('')
    setHealthPayload(null)
    setHealthStatus('')
    try {
      const data = await fetchBackendHealth(baseUrl)
      setHealthPayload(data)
      setHealthStatus('Healthy')
    } catch (requestError) {
      setHealthError(requestError instanceof Error ? requestError.message : 'Health check failed.')
      setHealthStatus('Unhealthy')
    } finally {
      setIsCheckingHealth(false)
    }
  }

  /**
   * Render the fieldset used by currently selected route.
   * // Line comment: keeps the route-specific form blocks easy to manage.
   */
  function renderRouteFields() {
    if (activeRoute === '/identity') {
      return (
        <label>
          Employee ID
          <input
            value={identityPayload.employee_id}
            onChange={(event) => {
              setIdentityPayload({ employee_id: event.target.value })
            }}
          />
        </label>
      )
    }

    if (activeRoute === '/skills') {
      return (
        <label>
          Employee ID
          <input
            value={skillsPayload.employee_id}
            onChange={(event) => {
              setSkillsPayload({ employee_id: event.target.value })
            }}
          />
        </label>
      )
    }

    if (activeRoute === '/coaching') {
      return (
        <label>
          Employee ID
          <input
            value={coachingPayload.employee_id}
            onChange={(event) => {
              setCoachingPayload({ employee_id: event.target.value })
            }}
          />
        </label>
      )
    }

    if (activeRoute === '/assessments') {
      return (
        <label>
          Attempt ID
          <input
            value={assessmentReadPayload.attempt_id}
            onChange={(event) => {
              setAssessmentReadPayload({ attempt_id: event.target.value })
            }}
          />
        </label>
      )
    }

    if (activeRoute === '/analytics') {
      return (
        <div className="field-grid">
          <label>
            Metric
            <input
              value={analyticsPayload.metric}
              onChange={(event) => {
                setAnalyticsPayload({
                  ...analyticsPayload,
                  metric: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Cohort
            <input
              value={analyticsPayload.cohort}
              onChange={(event) => {
                setAnalyticsPayload({
                  ...analyticsPayload,
                  cohort: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Start date
            <input
              value={analyticsPayload.start}
              onChange={(event) => {
                setAnalyticsPayload({
                  ...analyticsPayload,
                  start: event.target.value,
                })
              }}
            />
          </label>
          <label>
            End date
            <input
              value={analyticsPayload.end}
              onChange={(event) => {
                setAnalyticsPayload({
                  ...analyticsPayload,
                  end: event.target.value,
                })
              }}
            />
          </label>
        </div>
      )
    }

    if (activeRoute === '/command/identity/link') {
      return (
        <div className="field-grid">
          <label>
            External ID
            <input
              value={identityLinkPayload.external_id}
              onChange={(event) => {
                setIdentityLinkPayload({
                  ...identityLinkPayload,
                  external_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Employee ID
            <input
              value={identityLinkPayload.employee_id}
              onChange={(event) => {
                setIdentityLinkPayload({
                  ...identityLinkPayload,
                  employee_id: event.target.value,
                })
              }}
            />
          </label>
        </div>
      )
    }

    if (activeRoute === '/command/core/infer') {
      return (
        <div className="field-grid">
          <label>
            Employee ID
            <input
              value={inferPayload.employee_id}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  employee_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Skill ID
            <input
              value={inferPayload.skill_id}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  skill_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Value (0-1)
            <input
              value={inferPayload.value}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  value: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Source
            <input
              value={inferPayload.source}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  source: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Confidence
            <input
              value={inferPayload.confidence_hint}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  confidence_hint: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Model version
            <input
              value={inferPayload.model_version}
              onChange={(event) => {
                setInferPayload({
                  ...inferPayload,
                  model_version: event.target.value,
                })
              }}
            />
          </label>
        </div>
      )
    }

    if (activeRoute === '/command/activation/coaching') {
      return (
        <div className="field-grid">
          <label>
            Employee ID
            <input
              value={coachingCommandPayload.employee_id}
              onChange={(event) => {
                setCoachingCommandPayload({
                  ...coachingCommandPayload,
                  employee_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Goal Skill
            <input
              value={coachingCommandPayload.goal_skill}
              onChange={(event) => {
                setCoachingCommandPayload({
                  ...coachingCommandPayload,
                  goal_skill: event.target.value,
                })
              }}
            />
          </label>
        </div>
      )
    }

    if (activeRoute === '/command/assessments/submit') {
      return (
        <div className="field-grid">
          <label>
            Attempt ID
            <input
              value={assessmentSubmitPayload.attempt_id}
              onChange={(event) => {
                setAssessmentSubmitPayload({
                  ...assessmentSubmitPayload,
                  attempt_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Assessment ID
            <input
              value={assessmentSubmitPayload.assessment_id}
              onChange={(event) => {
                setAssessmentSubmitPayload({
                  ...assessmentSubmitPayload,
                  assessment_id: event.target.value,
                })
              }}
            />
          </label>
          <label>
            Employee ID
            <input
              value={assessmentSubmitPayload.employee_id}
              onChange={(event) => {
                setAssessmentSubmitPayload({
                  ...assessmentSubmitPayload,
                  employee_id: event.target.value,
                })
              }}
            />
          </label>
          <label className="field-span">
            Responses (JSON)
            <textarea
              value={assessmentSubmitPayload.responses}
              onChange={(event) => {
                setAssessmentSubmitPayload({
                  ...assessmentSubmitPayload,
                  responses: event.target.value,
                })
              }}
            />
          </label>
        </div>
      )
    }

    if (activeRoute === '/command/analytics/materialize') {
      return (
        <label>
          Trigger source
          <input
            value={materializePayload.trigger}
            onChange={(event) => {
              setMaterializePayload({ trigger: event.target.value })
            }}
          />
        </label>
      )
    }

    return null
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <h1>SkillsAI Frontend</h1>
        <p>
          React workbench for query and command routes in the federation gateway.
        </p>
      </header>

      <section className="panel">
        <h2>Connection</h2>
        <div className="field-grid">
          <label className="field-span">
            Backend base URL
            <input
              value={baseUrl}
              onChange={(event) => {
                setBaseUrl(event.target.value)
              }}
              placeholder="http://localhost:8000"
            />
          </label>
          <label>
            Actor ID
            <input
              value={actorId}
              onChange={(event) => {
                setActorId(event.target.value)
              }}
            />
          </label>
          <label>
            Token
            <input
              value={token}
              onChange={(event) => {
                setToken(event.target.value)
              }}
            />
          </label>
        </div>
        <div className="connection-actions">
          <button
            className="run-button"
            type="button"
            onClick={handleHealthCheck}
            disabled={isCheckingHealth}
          >
            {isCheckingHealth ? 'Checking health...' : 'Check API health'}
          </button>
          {healthStatus ? (
            <p className={healthStatus === 'Healthy' ? 'status-text status-ok' : 'status-text status-error'}>
              Status: {healthStatus}
            </p>
          ) : null}
        </div>
        {healthError ? <p className="error-text">{healthError}</p> : null}
        {healthPayload ? (
          <div>
            <h3>Health response</h3>
            <pre>{JSON.stringify(healthPayload, null, 2)}</pre>
          </div>
        ) : null}
      </section>

      <form className="panel" onSubmit={handleRunRequest}>
        <h2>Gateway Request</h2>
        <label>
          Route
          <select
            value={activeRoute}
            onChange={(event) => {
              setActiveRoute(event.target.value)
            }}
          >
            {routeDefinitions.map((definition) => (
              <option key={definition.route} value={definition.route}>
                {definition.method} {definition.route} - {definition.label}
              </option>
            ))}
          </select>
        </label>
        {renderRouteFields()}
        <button className="run-button" type="submit" disabled={isLoading}>
          {isLoading ? 'Running...' : 'Send request'}
        </button>
      </form>

      <section className="panel">
        <h2>Response</h2>
        {error ? <p className="error-text">{error}</p> : null}
        {!error && !result ? <p>No request sent yet.</p> : null}
        {result ? (
          <div className="result-grid">
            <div>
              <h3>Request payload</h3>
              <pre>{JSON.stringify(result.request, null, 2)}</pre>
            </div>
            <div>
              <h3>Backend response</h3>
              <pre>{JSON.stringify(result.response, null, 2)}</pre>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  )
}

export default App
