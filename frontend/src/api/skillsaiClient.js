/**
 * SkillsAI HTTP client helpers.
 * This module wraps backend request composition so UI components stay focused.
 */

const HEALTH_ENDPOINT = '/api/v1/health'
const PLATFORM_REQUEST_ENDPOINT = '/api/v1/platform/request'

/**
 * Build the backend URL from env config.
 * // Line comment: fall back to localhost backend when no env var is provided.
 */
export function getBackendBaseUrl() {
  return import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8000'
}

/**
 * Build one platform gateway request payload.
 * // Line comment: shape mirrors PlatformRequest from the Python backend.
 */
export function buildGatewayRequest(method, path, actorId, token, payload) {
  return {
    method,
    path,
    actor_id: actorId,
    token,
    payload,
  }
}

/**
 * Parse an HTTP response body as JSON when possible.
 * // Line comment: preserve raw text body when server returns non-JSON content.
 */
async function parseResponseBody(response) {
  // Line comment: read full body text once so it can be parsed or echoed.
  const textBody = await response.text()
  if (!textBody) {
    return null
  }
  // Line comment: parse JSON payloads and fallback to raw text object.
  try {
    return JSON.parse(textBody)
  } catch {
    return { raw: textBody }
  }
}

/**
 * Check FastAPI backend health endpoint.
 * // Line comment: this is used by the frontend connection panel for readiness checks.
 */
export async function fetchBackendHealth(backendBaseUrl = '') {
  // Line comment: use runtime override when provided, otherwise use env fallback.
  const effectiveBaseUrl = backendBaseUrl || getBackendBaseUrl()
  const response = await fetch(`${effectiveBaseUrl}${HEALTH_ENDPOINT}`, {
    method: 'GET',
  })
  const parsedBody = await parseResponseBody(response)
  if (!response.ok) {
    const message = parsedBody?.detail || parsedBody?.error || 'Backend health check failed.'
    throw new Error(`${message} (HTTP ${response.status})`)
  }
  return parsedBody
}

/**
 * Send a request to the backend gateway endpoint.
 * // Line comment: this targets the FastAPI route POST /api/v1/platform/request.
 */
export async function sendGatewayRequest(requestPayload, backendBaseUrl = '') {
  // Line comment: use runtime override when provided, otherwise use env fallback.
  const effectiveBaseUrl = backendBaseUrl || getBackendBaseUrl()
  const response = await fetch(`${effectiveBaseUrl}${PLATFORM_REQUEST_ENDPOINT}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestPayload),
  })
  const parsedBody = await parseResponseBody(response)

  if (!response.ok) {
    const message = parsedBody?.detail || parsedBody?.error || 'Backend request failed.'
    throw new Error(`${message} (HTTP ${response.status})`)
  }

  return parsedBody
}

/**
 * Normalize actor token configuration for gateway requests.
 * // Line comment: the backend accepts synthetic `actor:tenant` tokens in local development.
 */
function resolveGatewayToken(actorId, token) {
  // Line comment: prefer explicit caller token overrides when provided.
  if (token) {
    return token
  }
  // Line comment: default to the repo's seeded tenant naming convention.
  return `${actorId}:default`
}

/**
 * Unwrap the FastAPI gateway envelope into the nested `data` payload.
 * // Line comment: every successful gateway response is shaped as body.status/body.data.
 */
function unwrapGatewayData(responseBody) {
  // Line comment: safely walk the nested gateway response envelope.
  return responseBody?.body?.data || {}
}

/**
 * Execute one normalized gateway request for a seeded local environment.
 * // Line comment: this keeps actor id, token, path, and payload wiring consistent across the app.
 */
export async function executeGatewayRequest({
  method = 'GET',
  path,
  actorId = 'emp-1',
  token = '',
  payload = {},
  backendBaseUrl = '',
}) {
  // Line comment: build the backend PlatformRequest payload expected by the FastAPI route.
  const requestPayload = buildGatewayRequest(
    method,
    path,
    actorId,
    resolveGatewayToken(actorId, token),
    payload,
  )
  return sendGatewayRequest(requestPayload, backendBaseUrl)
}

/**
 * Fetch one seeded identity profile from the backend.
 * // Line comment: identity records power persona, tenant, and header metadata in the UI.
 */
export async function fetchIdentityProfile({
  employeeId = 'emp-1',
  actorId = employeeId,
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request canonical identity data for the selected employee.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/identity',
    actorId,
    token,
    payload: { employee_id: employeeId },
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).identity || {}
}

/**
 * Fetch seeded skill-state data from the backend.
 * // Line comment: the frontend renders the raw inferred skill states returned by the core API.
 */
export async function fetchSkillStates({
  employeeId = 'emp-1',
  actorId = employeeId,
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request all skill states for the selected employee.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/skills',
    actorId,
    token,
    payload: { employee_id: employeeId },
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).skills || {}
}

/**
 * Fetch coaching recommendations from the backend activation API.
 * // Line comment: this call is used for both coaching and mobility-style recommendation views.
 */
export async function fetchCoachingRecommendations({
  employeeId = 'emp-1',
  actorId = employeeId,
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request coaching recommendations for the selected employee.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/coaching',
    actorId,
    token,
    payload: { employee_id: employeeId },
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).coaching || { employee_id: employeeId, recommendations: [] }
}

/**
 * Fetch the seeded assessment package and attempt data from the backend.
 * // Line comment: one request can now return both package metadata and attempt state.
 */
export async function fetchAssessmentWorkspace({
  assessmentId = 'asm-1',
  attemptId = 'attempt-1',
  actorId = 'emp-1',
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request assessment package metadata plus one attempt record.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/assessments',
    actorId,
    token,
    payload: {
      assessment_id: assessmentId,
      attempt_id: attemptId,
    },
    backendBaseUrl,
  })
  const data = unwrapGatewayData(responseBody)
  return {
    assessment: data.assessment || {},
    assessmentAttempt: data.assessment_attempt || {},
  }
}

/**
 * Fetch one analytics query result from the backend.
 * // Line comment: metric, cohort, and range stay generic so the app can reuse one helper.
 */
export async function fetchAnalyticsSnapshot({
  metric = 'skill_coverage',
  cohort = 'all',
  start = '2026-01-01',
  end = '2026-12-31',
  actorId = 'manager-1',
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: issue one gateway analytics query using the provided metric filters.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/analytics',
    actorId,
    token,
    payload: { metric, cohort, start, end },
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).analytics || {}
}

/**
 * Fetch governance summary data from the backend.
 * // Line comment: this powers the governance page without frontend-owned mock audit data.
 */
export async function fetchGovernanceSummary({
  actorId = 'manager-1',
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request governance-oriented summary information from the backend.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/governance',
    actorId,
    token,
    payload: {},
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).governance || {}
}

/**
 * Fetch backend admin and seed-data metadata from the backend.
 * // Line comment: this powers the admin page with live seed-module information.
 */
export async function fetchAdminSummary({
  actorId = 'manager-1',
  token = '',
  backendBaseUrl = '',
} = {}) {
  // Line comment: request backend seed-data/admin summary information.
  const responseBody = await executeGatewayRequest({
    method: 'GET',
    path: '/admin',
    actorId,
    token,
    payload: {},
    backendBaseUrl,
  })
  return unwrapGatewayData(responseBody).admin || {}
}
