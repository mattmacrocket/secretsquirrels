"use client"

import { useCallback, useEffect, useState } from "react"
import { controlplaneFetch } from "../lib/controlplane"
import { formatAge } from "../lib/format"

type SentrySummaryPayload = {
  ok?: boolean
  stale?: boolean
  source?: string
  status_age_seconds?: number | null
  errors?: string[]
  highlights?: {
    findings_total?: number
    findings_pending?: number
    devices_total?: number
    devices_unknown?: number
    learning_status?: string
    alert_channel_count?: number
    alert_delivery_failures_24h?: number
    findings_24h?: { critical?: number; high?: number; medium?: number; low?: number }
    enabled_agents?: string[]
  }
}

type SentryFindingsPayload = {
  ok?: boolean
  count?: number
  findings?: Array<{
    id?: number
    created_at?: string
    severity?: string
    agent?: string
    title?: string
    device_ip?: string
    device_mac?: string
    acknowledged?: boolean
    during_learning?: boolean
  }>
}

type SentryRunsPayload = {
  ok?: boolean
  count?: number
  runs?: Array<{
    id?: number
    agent?: string
    started_at?: string
    completed_at?: string
    status?: string
    findings_count?: number
    error_message?: string
  }>
}

export default function SentryPage() {
  const [payload, setPayload] = useState<SentrySummaryPayload>({})
  const [findings, setFindings] = useState<SentryFindingsPayload>({})
  const [runs, setRuns] = useState<SentryRunsPayload>({})
  const [findingSeverity, setFindingSeverity] = useState("all")
  const [includeAcknowledged, setIncludeAcknowledged] = useState(false)
  const [includeLearning, setIncludeLearning] = useState(true)
  const [runsAgent, setRunsAgent] = useState("all")
  const [runsStatus, setRunsStatus] = useState("all")
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null)
  const [refreshBusy, setRefreshBusy] = useState(false)
  const [operatorMessage, setOperatorMessage] = useState("")

  const load = useCallback(async (forceRefresh = false) => {
    const response = await controlplaneFetch(forceRefresh ? "/sentry/summary?refresh=true" : "/sentry/summary", {
      cache: "no-store",
    })
    if (!response.ok) {
      return
    }
    setPayload((await response.json()) as SentrySummaryPayload)
    setLastSyncAt(Date.now())
  }, [])

  const loadFindings = useCallback(async () => {
    const params = new URLSearchParams({
      limit: "25",
      include_acknowledged: includeAcknowledged ? "true" : "false",
      include_learning: includeLearning ? "true" : "false",
    })
    if (findingSeverity !== "all") {
      params.set("severity", findingSeverity)
    }
    const response = await controlplaneFetch(`/sentry/findings?${params.toString()}`, { cache: "no-store" })
    if (!response.ok) {
      return
    }
    setFindings((await response.json()) as SentryFindingsPayload)
  }, [findingSeverity, includeAcknowledged, includeLearning])

  const loadRuns = useCallback(async () => {
    const params = new URLSearchParams({ limit: "25" })
    if (runsAgent !== "all") {
      params.set("agent", runsAgent)
    }
    if (runsStatus !== "all") {
      params.set("status", runsStatus)
    }
    const response = await controlplaneFetch(`/sentry/runs?${params.toString()}`, { cache: "no-store" })
    if (!response.ok) {
      return
    }
    setRuns((await response.json()) as SentryRunsPayload)
  }, [runsAgent, runsStatus])

  useEffect(() => {
    load(false).catch(() => undefined)
    loadFindings().catch(() => undefined)
    loadRuns().catch(() => undefined)
    const timer = setInterval(() => {
      load(false).catch(() => undefined)
      loadFindings().catch(() => undefined)
      loadRuns().catch(() => undefined)
    }, 20000)
    return () => clearInterval(timer)
  }, [load, loadFindings, loadRuns])

  const forceRefresh = useCallback(async () => {
    setRefreshBusy(true)
    setOperatorMessage("")
    try {
      await load(true)
      await loadFindings()
      await loadRuns()
      setOperatorMessage("status refreshed")
    } catch {
      setOperatorMessage("refresh failed")
    } finally {
      setRefreshBusy(false)
    }
  }, [load, loadFindings, loadRuns])

  return (
    <main className="cp-page">
      <header className="cp-hero">
        <div>
          <p className="cp-kicker">Sentry</p>
          <h1>PingTing Monitoring</h1>
          <p className="cp-subtitle">Operational view of findings volume, device drift, and learning status from PingTing.</p>
        </div>
        <div className="cp-hero-status">
          <span className={`cp-badge ${payload.ok ? (payload.stale ? "warn" : "up") : "down"}`}>
            {payload.ok ? (payload.stale ? "Status stale" : "Status healthy") : "Status unavailable"}
          </span>
          <div className="cp-health-strip">
            <span className={`cp-pill ${payload.ok ? "good" : "bad"}`}>Sentry</span>
            <span className={`cp-pill ${payload.stale ? "warn" : "good"}`}>Freshness</span>
            <button className="cp-link-pill cp-link-pill-button" onClick={forceRefresh} disabled={refreshBusy}>
              {refreshBusy ? "Refreshing" : "Force refresh"}
            </button>
          </div>
          <small>
            {operatorMessage ||
              `Last sync: ${formatAge(lastSyncAt === null ? null : Math.max(0, Date.now() - lastSyncAt))}`}
          </small>
        </div>
      </header>

      <section className="cp-controls">
        <label>
          Severity
          <select value={findingSeverity} onChange={(event) => setFindingSeverity(event.target.value)}>
            <option value="all">all</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label>
          Acknowledged
          <select
            value={includeAcknowledged ? "include" : "exclude"}
            onChange={(event) => setIncludeAcknowledged(event.target.value === "include")}
          >
            <option value="exclude">exclude</option>
            <option value="include">include</option>
          </select>
        </label>
        <label>
          Learning
          <select
            value={includeLearning ? "include" : "exclude"}
            onChange={(event) => setIncludeLearning(event.target.value === "include")}
          >
            <option value="include">include</option>
            <option value="exclude">exclude</option>
          </select>
        </label>
        <label>
          Run agent
          <select value={runsAgent} onChange={(event) => setRunsAgent(event.target.value)}>
            <option value="all">all</option>
            <option value="network_scanner">network_scanner</option>
            <option value="breach_monitor">breach_monitor</option>
            <option value="log_monitor">log_monitor</option>
          </select>
        </label>
        <label>
          Run status
          <select value={runsStatus} onChange={(event) => setRunsStatus(event.target.value)}>
            <option value="all">all</option>
            <option value="running">running</option>
            <option value="success">success</option>
            <option value="error">error</option>
          </select>
        </label>
        <div className="cp-controls-actions">
          <button onClick={() => loadFindings().catch(() => undefined)}>Reload findings</button>
          <button onClick={() => loadRuns().catch(() => undefined)}>Reload runs</button>
        </div>
      </section>

      <section className="cp-stats">
        <article>
          <h2>Pending findings</h2>
          <p>{payload.highlights?.findings_pending ?? 0}</p>
          <span>Total findings: {payload.highlights?.findings_total ?? 0}</span>
        </article>
        <article>
          <h2>Unknown devices</h2>
          <p>{payload.highlights?.devices_unknown ?? 0}</p>
          <span>Total devices: {payload.highlights?.devices_total ?? 0}</span>
        </article>
        <article>
          <h2>Learning</h2>
          <p>{payload.highlights?.learning_status ?? "unknown"}</p>
          <span>Status age: {payload.status_age_seconds ?? "n/a"}s</span>
        </article>
        <article>
          <h2>Channels</h2>
          <p>{payload.highlights?.alert_channel_count ?? 0}</p>
          <span>Failures(24h): {payload.highlights?.alert_delivery_failures_24h ?? 0}</span>
        </article>
      </section>

      <section className="cp-grid cp-grid-secondary">
        <article className="cp-card">
          <h3>Recent findings</h3>
          <ul className="cp-feed">
            {(findings.findings ?? []).length === 0 ? (
              <li>
                <span>Findings</span>
                <strong>No findings for current filters</strong>
                <small>count={findings.count ?? 0}</small>
              </li>
            ) : null}
            {(findings.findings ?? []).map((item) => {
              const findingId = String(item.id ?? "")
              const severity = String(item.severity ?? "unknown")
              const title = String(item.title ?? "finding")
              const device = String(item.device_ip || item.device_mac || "n/a")
              return (
                <li key={findingId || `${title}-${device}`}>
                  <span>{severity}</span>
                  <strong>{title}</strong>
                  <small>{device} · {item.agent || "agent"} · {item.created_at || "unknown time"}</small>
                </li>
              )
            })}
          </ul>
        </article>

        <article className="cp-card">
          <h3>Recent agent runs</h3>
          <ul className="cp-feed">
            {(runs.runs ?? []).length === 0 ? (
              <li>
                <span>Runs</span>
                <strong>No runs for current filters</strong>
                <small>count={runs.count ?? 0}</small>
              </li>
            ) : null}
            {(runs.runs ?? []).map((item) => {
              const runId = String(item.id ?? "")
              const status = String(item.status ?? "unknown")
              const agent = String(item.agent ?? "agent")
              const findingsCount = Number(item.findings_count ?? 0)
              const startedAt = String(item.started_at ?? "unknown time")
              const errorMessage = String(item.error_message ?? "")
              return (
                <li key={runId || `${agent}-${startedAt}`}>
                  <span>{status}</span>
                  <strong>{agent} · findings={findingsCount}</strong>
                  <small>{startedAt}{errorMessage ? ` · ${errorMessage}` : ""}</small>
                </li>
              )
            })}
          </ul>
        </article>

        <article className="cp-card">
          <h3>24h severity mix</h3>
          <ul className="cp-list cp-list-small">
            <li>
              <span>Critical</span>
              <strong>{payload.highlights?.findings_24h?.critical ?? 0}</strong>
            </li>
            <li>
              <span>High</span>
              <strong>{payload.highlights?.findings_24h?.high ?? 0}</strong>
            </li>
            <li>
              <span>Medium</span>
              <strong>{payload.highlights?.findings_24h?.medium ?? 0}</strong>
            </li>
            <li>
              <span>Low</span>
              <strong>{payload.highlights?.findings_24h?.low ?? 0}</strong>
            </li>
          </ul>
        </article>

        <article className="cp-card">
          <h3>Enabled agents</h3>
          <ul className="cp-list cp-list-small">
            {(payload.highlights?.enabled_agents ?? []).length === 0 ? <li><strong>No enabled agents</strong></li> : null}
            {(payload.highlights?.enabled_agents ?? []).map((agent) => (
              <li key={agent}>
                <span>agent</span>
                <strong>{agent}</strong>
              </li>
            ))}
          </ul>
        </article>

        <article className="cp-card">
          <h3>Adapter diagnostics</h3>
          <ul className="cp-feed">
            <li>
              <span>Source</span>
              <strong>{payload.source ?? "n/a"}</strong>
              <small>age={payload.status_age_seconds ?? "n/a"}s</small>
            </li>
            {(payload.errors ?? []).length === 0 ? (
              <li>
                <span>Errors</span>
                <strong>none</strong>
                <small>adapter healthy</small>
              </li>
            ) : null}
            {(payload.errors ?? []).map((item) => (
              <li key={item}>
                <span>Error</span>
                <strong>{item}</strong>
                <small>needs operator review</small>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  )
}
