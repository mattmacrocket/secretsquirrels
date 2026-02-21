const CONTROLPLANE_API_BASE = process.env.NEXT_PUBLIC_CONTROLPANE_API ?? "http://127.0.0.1:8199"
const CONTROLPLANE_API_TOKEN = (process.env.NEXT_PUBLIC_CONTROLPANE_API_TOKEN ?? "").trim()

const withControlPlaneHeaders = (headers?: HeadersInit): Headers => {
  const merged = new Headers(headers)
  if (CONTROLPLANE_API_TOKEN && !merged.has("Authorization") && !merged.has("X-API-Key")) {
    merged.set("Authorization", `Bearer ${CONTROLPLANE_API_TOKEN}`)
  }
  return merged
}

const controlplaneFetch = (path: string, init?: RequestInit): Promise<Response> => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  const nextInit = { ...(init ?? {}) }
  nextInit.headers = withControlPlaneHeaders(init?.headers)
  return fetch(`${CONTROLPLANE_API_BASE}${normalizedPath}`, nextInit)
}

export { CONTROLPLANE_API_BASE, controlplaneFetch }
