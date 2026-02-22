"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { controlplaneFetch } from "../lib/controlplane"
import { formatAge } from "../lib/format"

type ActionResult = {
  ok?: boolean
  finished_at?: string
  output?: string
  exit_code?: number
}

type ProjectRow = {
  name?: string
  role?: string
  verification_key?: string
  local_path?: string
  status?: {
    present?: boolean
    git?: boolean
    dirty?: boolean
    branch?: string
    commit?: string
    committed_at?: string
  }
}

type OrchestrationPayload = {
  generated_at?: string
  project_count?: number
  dirty_repo_count?: number
  missing_repo_count?: number
  projects?: ProjectRow[]
  last_actions?: {
    bootstrap?: ActionResult | null
    smoke?: ActionResult | null
    update?: ActionResult | null
  }
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

export default function OrchestrationPage() {
  const [payload, setPayload] = useState<OrchestrationPayload>({})
  const [busyAction, setBusyAction] = useState<"bootstrap" | "smoke" | "update" | null>(null)
  const [operatorMessage, setOperatorMessage] = useState("")
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null)

  const load = useCallback(async () => {
    const response = await controlplaneFetch("/orchestration/summary", { cache: "no-store" })
    if (!response.ok) {
      return
    }
    const nextPayload = (await response.json()) as OrchestrationPayload
    setPayload(nextPayload)
    setLastSyncAt(Date.now())
  }, [])

  useEffect(() => {
    load().catch(() => undefined)
    const timer = setInterval(() => {
      load().catch(() => undefined)
    }, 15000)
    return () => clearInterval(timer)
  }, [load])

  const runAction = useCallback(
    async (action: "bootstrap" | "smoke" | "update") => {
      setBusyAction(action)
      setOperatorMessage("")
      try {
        const response = await controlplaneFetch(`/orchestration/actions/${action}`, {
          method: "POST",
          cache: "no-store",
        })
        if (!response.ok) {
          setOperatorMessage(`${action} failed (${response.status})`)
          return
        }
        const result = (await response.json()) as ActionResult
        setOperatorMessage(result.ok ? `${action} completed` : `${action} failed`)
      } catch {
        setOperatorMessage(`${action} failed`)
      } finally {
        setBusyAction(null)
        load().catch(() => undefined)
      }
    },
    [load]
  )

  const projects = useMemo(() => payload.projects ?? [], [payload.projects])

  return (
    <main className="cp-page">
      <header className="cp-hero">
        <div>
          <p className="cp-kicker">Orchestration</p>
          <h1>Workspace Control</h1>
          <p className="cp-subtitle">Run cross-repo smoke/update workflows and inspect repository hygiene from one operator surface.</p>
        </div>
        <div className="cp-hero-status">
          <span className={`cp-badge ${(payload.missing_repo_count ?? 0) === 0 ? "up" : "warn"}`}>
            {(payload.missing_repo_count ?? 0) === 0 ? "Repo set complete" : "Missing repos"}
          </span>
          <div className="cp-health-strip">
            <button className="cp-link-pill cp-link-pill-button" onClick={() => runAction("bootstrap")} disabled={busyAction !== null}>
              {busyAction === "bootstrap" ? "Running bootstrap" : "Run bootstrap"}
            </button>
            <button className="cp-link-pill cp-link-pill-button" onClick={() => runAction("smoke")} disabled={busyAction !== null}>
              {busyAction === "smoke" ? "Running smoke" : "Run smoke"}
            </button>
            <button className="cp-link-pill cp-link-pill-button" onClick={() => runAction("update")} disabled={busyAction !== null}>
              {busyAction === "update" ? "Running update" : "Run update"}
            </button>
          </div>
          <small>
            {operatorMessage ||
              `Last sync: ${formatAge(lastSyncAt === null ? null : Math.max(0, Date.now() - lastSyncAt))}`}
          </small>
        </div>
      </header>

      <section className="cp-stats">
        <article>
          <h2>Projects</h2>
          <p>{payload.project_count ?? 0}</p>
          <span>Missing: {payload.missing_repo_count ?? 0}</span>
        </article>
        <article>
          <h2>Dirty repos</h2>
          <p>{payload.dirty_repo_count ?? 0}</p>
          <span>Requires review</span>
        </article>
        <article>
          <h2>Last bootstrap</h2>
          <p>{payload.last_actions?.bootstrap?.ok ? "pass" : "n/a"}</p>
          <span>Age: {asAgeLabel(payload.last_actions?.bootstrap?.finished_at ?? undefined)}</span>
        </article>
        <article>
          <h2>Last smoke</h2>
          <p>{payload.last_actions?.smoke?.ok ? "pass" : "n/a"}</p>
          <span>Age: {asAgeLabel(payload.last_actions?.smoke?.finished_at ?? undefined)}</span>
        </article>
        <article>
          <h2>Last update</h2>
          <p>{payload.last_actions?.update?.ok ? "pass" : "n/a"}</p>
          <span>Age: {asAgeLabel(payload.last_actions?.update?.finished_at ?? undefined)}</span>
        </article>
      </section>

      <section className="cp-grid cp-grid-secondary">
        <article className="cp-card">
          <h3>Repository state</h3>
          <ul className="cp-list cp-list-small">
            {projects.length === 0 ? <li><strong>No projects discovered</strong></li> : null}
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
          <h3>Bootstrap output</h3>
          <pre className="cp-handoff-markdown">{payload.last_actions?.bootstrap?.output || "No bootstrap run yet."}</pre>
        </article>

        <article className="cp-card">
          <h3>Smoke output</h3>
          <pre className="cp-handoff-markdown">{payload.last_actions?.smoke?.output || "No smoke run yet."}</pre>
        </article>

        <article className="cp-card">
          <h3>Update output</h3>
          <pre className="cp-handoff-markdown">{payload.last_actions?.update?.output || "No update run yet."}</pre>
        </article>
      </section>
    </main>
  )
}
