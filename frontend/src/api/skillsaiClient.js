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
