'use client'
import { useRouter, usePathname } from 'next/navigation'
import { useState, useEffect, useCallback } from 'react'
import AuthButton from '@/components/AuthButton'

const PAGES = [
  { num: '01', label: { el: 'Αρχική', en: 'Home' }, href: '/' },
  { num: '02', label: { el: 'Αγορά', en: 'Market' }, href: '/market' },
  { num: '03', label: { el: 'Trending', en: 'Trending' }, href: '/trending' },
  { num: '04', label: { el: 'Κερδισμένοι', en: 'Top Movers' }, href: '/gainers' },
  { num: '05', label: { el: 'Χαρτοφυλάκιο', en: 'Portfolio' }, href: '/portfolio' },
  { num: '06', label: { el: 'Μετατροπέας', en: 'Converter' }, href: '/converter' },
  { num: '07', label: { el: 'Εργαλεία', en: 'Tools' }, href: '/tools' },
]

export default function NavWithMenu() {
  const router = useRouter()
  const pathname = usePathname()
  const [menuOpen, setMenuOpen] = useState(false)
  const [lang, setLang] = useState<'el' | 'en'>('el')

  useEffect(() => {
    const saved = localStorage.getItem('lang') as 'el' | 'en' | null
    if (saved) setLang(saved)
  }, [])

  const switchLang = useCallback((l: 'el' | 'en') => {
    setLang(l)
    localStorage.setItem('lang', l)
  }, [])

  const openMenu = useCallback(() => setMenuOpen(true), [])
  const closeMenu = useCallback(() => setMenuOpen(false), [])

  const navigate = useCallback(
    (href: string) => {
      closeMenu()
      router.push(href)
    },
    [closeMenu, router]
  )

  // Close menu on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeMenu()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [closeMenu])

  // Prevent body scroll when menu open
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

  return (
    <>
      <nav className="main-nav">
        <div className="nav-inner">
          <div className="nav-logo" onClick={() => navigate('/')}>
            <div className="nav-logo-icon">₿</div>
            <span className="nav-logo-text">CryptoLive</span>
          </div>
          <div className="nav-right">
            <div className="live-indicator">
              <div className="live-dot" />
              <span>LIVE</span>
            </div>
            <AuthButton />
            <button
              className={`nav-menu-btn${menuOpen ? ' open' : ''}`}
              onClick={menuOpen ? closeMenu : openMenu}
              aria-label="Toggle menu"
            >
              <div className="nmb-line" />
              <div className="nmb-line" />
              <div className="nmb-line" />
            </button>
          </div>
        </div>
      </nav>

      <div className={`menu-overlay${menuOpen ? ' open' : ''}`} onClick={(e) => {
        if (e.target === e.currentTarget) closeMenu()
      }}>
        <div className="menu-overlay-inner">
          <div className="menu-overlay-links">
            {PAGES.map((page) => (
              <div
                key={page.href}
                className={`mol-link${pathname === page.href ? ' active' : ''}`}
                onClick={() => navigate(page.href)}
              >
                <span className="mol-num">{page.num}</span>
                <span className="mol-label">{page.label[lang]}</span>
                <span className="mol-arrow">→</span>
              </div>
            ))}
          </div>
          <div className="menu-overlay-footer">
            <div className="lang-switcher">
              <button
                className={`lang-btn${lang === 'el' ? ' active' : ''}`}
                onClick={() => switchLang('el')}
              >
                ΕΛ
              </button>
              <button
                className={`lang-btn${lang === 'en' ? ' active' : ''}`}
                onClick={() => switchLang('en')}
              >
                EN
              </button>
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>
              © 2025 CryptoLive
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
