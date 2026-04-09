/**
 * SkillsAI HTTP client helpers.
 * This module wraps backend request composition so UI components stay focused.
 */

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
 * Send a request to the backend gateway endpoint.
 * // Line comment: this assumes backend exposes POST /api/v1/platform/request.
 */
export async function sendGatewayRequest(requestPayload, backendBaseUrl = '') {
  // Line comment: use runtime override when provided, otherwise use env fallback.
  const effectiveBaseUrl = backendBaseUrl || getBackendBaseUrl()
  const response = await fetch(`${effectiveBaseUrl}/api/v1/platform/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestPayload),
  })

  const textBody = await response.text()
  let parsedBody = null

  // Line comment: parse JSON bodies, but preserve raw text errors when JSON is absent.
  if (textBody) {
    try {
      parsedBody = JSON.parse(textBody)
    } catch (_error) {
      parsedBody = { raw: textBody }
    }
  }

  if (!response.ok) {
    const message = parsedBody?.detail || parsedBody?.error || 'Backend request failed.'
    throw new Error(`${message} (HTTP ${response.status})`)
  }

  return parsedBody
}
