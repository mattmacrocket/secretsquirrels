"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

type NavItem = {
  href: string
  label: string
  matches: (pathname: string) => boolean
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/overview",
    label: "Overview",
    matches: (pathname) => pathname === "/" || pathname.startsWith("/overview"),
  },
  {
    href: "/deception",
    label: "Deception",
    matches: (pathname) => pathname.startsWith("/deception") && !pathname.startsWith("/deception/theater"),
  },
  {
    href: "/deception/theater",
    label: "Theater",
    matches: (pathname) => pathname.startsWith("/deception/theater") || pathname.startsWith("/theater"),
  },
  {
    href: "/sentry",
    label: "Sentry",
    matches: (pathname) => pathname.startsWith("/sentry"),
  },
  {
    href: "/orchestration",
    label: "Orchestration",
    matches: (pathname) => pathname.startsWith("/orchestration"),
  },
]

export default function TopbarNav() {
  const pathname = usePathname() ?? ""
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  const navClassName = useMemo(
    () => `cp-topbar-links${menuOpen ? " is-open" : ""}`,
    [menuOpen]
  )

  return (
    <>
      <button
        type="button"
        className="cp-topbar-menu-button"
        aria-controls="cp-topbar-links"
        aria-expanded={menuOpen}
        aria-label="Toggle navigation"
        onClick={() => setMenuOpen((current) => !current)}
      >
        {menuOpen ? "Close" : "Menu"}
      </button>
      <nav id="cp-topbar-links" className={navClassName} aria-label="Dashboard sections">
        {NAV_ITEMS.map((item) => {
          const active = item.matches(pathname)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`cp-topbar-link${active ? " cp-topbar-link-active" : ""}`}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </>
  )
}
