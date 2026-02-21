const CONTROLPLANE_BASE = process.env.NEXT_PUBLIC_CONTROLPANE_API ?? "http://127.0.0.1:8199"
const CONTROLPLANE_WS_BASE = process.env.NEXT_PUBLIC_CONTROLPANE_WS ?? "ws://127.0.0.1:8199"
const API_BASE =
  process.env.NEXT_PUBLIC_DECEPTION_API ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_API ??
  `${CONTROLPLANE_BASE}/deception`
const WS_BASE =
  process.env.NEXT_PUBLIC_DECEPTION_WS ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_WS ??
  `${CONTROLPLANE_WS_BASE}/deception/ws/events`
const WS_THEATER_BASE =
  process.env.NEXT_PUBLIC_DECEPTION_WS_THEATER ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_WS_THEATER ??
  `${CONTROLPLANE_WS_BASE}/deception/ws/theater/live`
const API_AUTH_TOKEN = (
  process.env.NEXT_PUBLIC_CONTROLPANE_API_TOKEN ??
  process.env.NEXT_PUBLIC_DECEPTION_API_TOKEN ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_API_TOKEN ??
  ""
).trim()
const WS_AUTH_TOKEN = (
  process.env.NEXT_PUBLIC_CONTROLPANE_API_TOKEN ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_WS_TOKEN ??
  process.env.NEXT_PUBLIC_DECEPTION_WS_TOKEN ??
  process.env.NEXT_PUBLIC_DECEPTION_API_TOKEN ??
  process.env.NEXT_PUBLIC_CLOWNPEANUTS_API_TOKEN ??
  ""
).trim()

const withApiAuthHeaders = (headers?: HeadersInit): Headers => {
  const merged = new Headers(headers)
  if (API_AUTH_TOKEN && !merged.has("Authorization") && !merged.has("X-API-Key")) {
    merged.set("Authorization", `Bearer ${API_AUTH_TOKEN}`)
  }
  return merged
}

const cpFetch = (url: string, init?: RequestInit): Promise<Response> => {
  const nextInit = { ...(init ?? {}) }
  nextInit.headers = withApiAuthHeaders(init?.headers)
  return fetch(url, nextInit)
}

const withApiTokenQuery = (url: string): string => {
  if (!WS_AUTH_TOKEN) {
    return url
  }
  try {
    const parsed = new URL(url)
    if (!parsed.searchParams.has("token")) {
      parsed.searchParams.set("token", WS_AUTH_TOKEN)
    }
    return parsed.toString()
  } catch {
    return url
  }
}

const withQueryParams = (url: string, params: Record<string, string>): string => {
  try {
    const parsed = new URL(url)
    for (const [key, value] of Object.entries(params)) {
      parsed.searchParams.set(key, value)
    }
    return parsed.toString()
  } catch {
    return url
  }
}

export { API_BASE, WS_BASE, WS_THEATER_BASE, cpFetch, withApiTokenQuery, withQueryParams }
