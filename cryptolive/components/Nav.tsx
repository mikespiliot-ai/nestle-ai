'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, useCallback } from 'react'

const LINKS = [
  { href: '/',           label: 'Αρχική' },
  { href: '/market',     label: 'Αγορά' },
  { href: '/movers',     label: 'Movers' },
  { href: '/compare',    label: 'Σύγκριση' },
  { href: '/portfolio',  label: 'Χαρτοφυλάκιο' },
  { href: '/converter',  label: 'Μετατροπέας' },
]

export default function Nav() {
  const pathname = usePathname()
  const [spinning, setSpinning] = useState(false)

  const handleRefresh = useCallback(() => {
    if (spinning) return
    setSpinning(true)
    setTimeout(() => setSpinning(false), 800)
    window.location.reload()
  }, [spinning])

  return (
    <nav>
      <Link href="/" className="nav-logo">₿ CryptoLive</Link>
      <div className="nav-links">
        {LINKS.map(({ href, label }) => (
          <Link key={href} href={href} className={pathname === href || (href !== '/' && pathname.startsWith(href)) ? 'active' : ''}>
            {label}
          </Link>
        ))}
      </div>
      <button
        onClick={handleRefresh}
        style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: '8px', padding: '0.35rem 0.85rem', fontSize: '0.82rem', color: 'var(--muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', transition: 'all 0.2s', flexShrink: 0 }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={spinning ? { animation: 'spin 0.8s linear infinite' } : {}}>
          <path d="M1 4v6h6M23 20v-6h-6"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        Refresh
      </button>
    </nav>
  )
}
