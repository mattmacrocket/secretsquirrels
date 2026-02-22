"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { controlplaneFetch } from "../lib/controlplane"
import { formatAge } from "../lib/format"

type DeceptionStatus = {
  ok?: boolean
  error?: string
  status?: {
    services?: Array<{ name?: string; running?: boolean }>
    sessions?: { sessions?: number; events?: number }
    network?: { compliant?: boolean; warnings?: string[] }
  }
}

type SentrySummary = {
  ok?: boolean
  stale?: boolean
  source?: string
  status_age_seconds?: number | null
  highlights?: {
    findings_total?: number
    findings_pending?: number
    devices_unknown?: number
    learning_status?: string
    alert_delivery_failures_24h?: number
    enabled_agents?: string[]
  }
}

type OrchestrationProject = {
  name?: string
  role?: string
  local_path?: string
  status?: {
    present?: boolean
    git?: boolean
    dirty?: boolean
    branch?: string
    committed_at?: string
  }
}

type OrchestrationAction = {
  ok?: boolean
  finished_at?: string
}

type OrchestrationSummary = {
  project_count?: number
  dirty_repo_count?: number
  missing_repo_count?: number
  projects?: OrchestrationProject[]
  last_actions?: {
    smoke?: OrchestrationAction | null
    update?: OrchestrationAction | null
  }
}

type SentryFinding = {
  id?: number
  created_at?: string
  severity?: string
  agent?: string
  title?: string
  device_ip?: string
  device_mac?: string
}

type OverviewPayload = {
  generated_at?: string
  overall_ok?: boolean
  deception?: DeceptionStatus
  sentry?: SentrySummary
  sentry_findings?: {
    ok?: boolean
    count?: number
    findings?: SentryFinding[]
  }
  orchestration?: OrchestrationSummary
}

const asAgeLabel = (value: string | undefined): string => {
  if (!value) {
    return "none yet"
  }
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) {
    return "unknown"
  }
  return formatAge(Math.max(0, Date.now() - parsed))
}

export default function OverviewPage() {
  const [payload, setPayload] = useState<OverviewPayload>({})
  const [error, setError] = useState("")
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      const response = await controlplaneFetch("/overview/summary", { cache: "no-store" })
      if (!response.ok) {
        setError(`overview unavailable (${response.status})`)
        return
      }
      const nextPayload = (await response.json()) as OverviewPayload
      setPayload(nextPayload)
      setError("")
      setLastSyncAt(Date.now())
    } catch {
      setError("overview unavailable")
    }
  }, [])

  useEffect(() => {
    load().catch(() => undefined)
    const timer = setInterval(() => {
      load().catch(() => undefined)
    }, 15000)
    return () => clearInterval(timer)
  }, [load])

  const projects = useMemo(() => payload.orchestration?.projects ?? [], [payload.orchestration?.projects])
  const services = useMemo(() => payload.deception?.status?.services ?? [], [payload.deception?.status?.services])
  const sentryFindings = useMemo(() => payload.sentry_findings?.findings ?? [], [payload.sentry_findings?.findings])

  return (
    <main className="cp-page">
      <header className="cp-hero">
        <div>
          <p className="cp-kicker">Overview</p>
          <h1>Cross-Repo Operations Posture</h1>
          <p className="cp-subtitle">
            SquirrelOps aggregates ClownPeanuts deception telemetry, PingTing sentry signals, and orchestration repo
            health.
          </p>
        </div>
        <div className="cp-hero-status">
          <span className={`cp-badge ${payload.overall_ok ? "up" : "warn"}`}>
            {payload.overall_ok ? "Workspace healthy" : "Needs attention"}
          </span>
          <div className="cp-health-strip">
            <span className={`cp-pill ${payload.deception?.ok ? "good" : "bad"}`}>Deception</span>
            <span className={`cp-pill ${payload.sentry?.ok ? (payload.sentry?.stale ? "warn" : "good") : "bad"}`}>Sentry</span>
            <span className={`cp-pill ${(payload.orchestration?.missing_repo_count ?? 0) > 0 ? "bad" : "good"}`}>
              Orchestration
            </span>
          </div>
          <small>Last sync: {formatAge(lastSyncAt === null ? null : Math.max(0, Date.now() - lastSyncAt))}</small>
        </div>
      </header>

      <section className="cp-stats">
        <article>
          <h2>ClownPeanuts sessions</h2>
          <p>{payload.deception?.status?.sessions?.sessions ?? 0}</p>
          <span>Events: {payload.deception?.status?.sessions?.events ?? 0}</span>
        </article>
        <article>
          <h2>PingTing pending findings</h2>
          <p>{payload.sentry?.highlights?.findings_pending ?? 0}</p>
          <span>Total findings: {payload.sentry?.highlights?.findings_total ?? 0}</span>
        </article>
        <article>
          <h2>Managed repos</h2>
          <p>{payload.orchestration?.project_count ?? 0}</p>
          <span>Missing: {payload.orchestration?.missing_repo_count ?? 0}</span>
        </article>
        <article>
          <h2>Dirty repos</h2>
          <p>{payload.orchestration?.dirty_repo_count ?? 0}</p>
          <span>Update age: {asAgeLabel(payload.orchestration?.last_actions?.update?.finished_at ?? undefined)}</span>
        </article>
      </section>

      <section className="cp-grid cp-grid-secondary">
        <article className="cp-card">
          <h3>Service health</h3>
          <ul className="cp-list cp-list-small">
            {services.length === 0 ? <li><strong>No service data</strong></li> : null}
            {services.map((service) => {
              const name = String(service.name ?? "service")
              const running = Boolean(service.running)
              return (
                <li key={name}>
                  <span>{name}</span>
                  <strong>{running ? "running" : "stopped"}</strong>
                </li>
              )
            })}
          </ul>
        </article>

        <article className="cp-card">
          <h3>Managed repositories</h3>
          <ul className="cp-list cp-list-small">
            {projects.length === 0 ? <li><strong>No project data</strong></li> : null}
            {projects.map((project) => {
              const name = String(project.name ?? "project")
              const branch = String(project.status?.branch ?? "n/a")
              const dirty = Boolean(project.status?.dirty)
              return (
                <li key={name}>
                  <span>{name}</span>
                  <strong>{dirty ? `${branch} (dirty)` : branch}</strong>
                </li>
              )
            })}
          </ul>
        </article>

        <article className="cp-card">
          <h3>Sentry queue</h3>
          <ul className="cp-feed">
            {sentryFindings.length === 0 ? (
              <li>
                <span>Findings</span>
                <strong>No pending sentry findings</strong>
                <small>count={payload.sentry_findings?.count ?? 0}</small>
              </li>
            ) : null}
            {sentryFindings.map((item) => {
              const id = String(item.id ?? "")
              const severity = String(item.severity ?? "unknown")
              const title = String(item.title ?? "finding")
              const device = String(item.device_ip || item.device_mac || "n/a")
              return (
                <li key={id || `${severity}-${title}`}>
                  <span>{severity}</span>
                  <strong>{title}</strong>
                  <small>{device} · {item.agent || "agent"} · {item.created_at || "unknown time"}</small>
                </li>
              )
            })}
          </ul>
        </article>

        <article className="cp-card">
          <h3>Sentry posture</h3>
          <ul className="cp-feed">
            <li>
              <span>Learning</span>
              <strong>{payload.sentry?.highlights?.learning_status ?? "unknown"}</strong>
              <small>Source: {payload.sentry?.source ?? "n/a"}</small>
            </li>
            <li>
              <span>Unknown devices</span>
              <strong>{payload.sentry?.highlights?.devices_unknown ?? 0}</strong>
              <small>Status age: {payload.sentry?.status_age_seconds ?? "n/a"}s</small>
            </li>
            <li>
              <span>Delivery failures (24h)</span>
              <strong>{payload.sentry?.highlights?.alert_delivery_failures_24h ?? 0}</strong>
              <small>Enabled agents: {(payload.sentry?.highlights?.enabled_agents ?? []).join(", ") || "none"}</small>
            </li>
          </ul>
        </article>
      </section>

      {error ? <section className="cp-card"><h3>Overview errors</h3><p>{error}</p></section> : null}
    </main>
  )
}
