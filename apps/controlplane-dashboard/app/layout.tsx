import "./globals.css"
import type { Metadata } from "next"
import Link from "next/link"
import TopbarNav from "./components/topbar-nav"

export const metadata: Metadata = {
  title: "SquirrelOps Control Plane",
  description: "Multi-product operations dashboard for ClownPeanuts and PingTing",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="cp-shell">
          <div className="cp-main">
            <header className="cp-topbar">
              <Link href="/overview" className="cp-topbar-brand" aria-label="SquirrelOps home" />
              <strong className="cp-topbar-title">Control Plane</strong>
              <TopbarNav />
            </header>
            <div className="cp-content">{children}</div>
            <footer className="cp-footer">
              <a
                href="https://github.com/rocketweb/squirrelops"
                target="_blank"
                rel="noreferrer"
                className="cp-footer-link"
              >
                Repo
              </a>
            </footer>
          </div>
        </div>
      </body>
    </html>
  )
}
