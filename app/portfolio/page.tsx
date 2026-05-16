'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import Image from 'next/image'
import { fmt, fmtPct } from '@/lib/format'
import { supabase } from '@/lib/supabase'
import AuthButton from '@/components/AuthButton'
import type { User } from '@supabase/supabase-js'

interface Coin {
  id: string
  name: string
  symbol: string
  image: string
  current_price: number
  price_change_percentage_24h: number
}

interface Holding {
  id: string
  coin_id: string
  amount: number
  buy_price: number
  user_id: string
  coin?: Coin
}

interface CoinRow {
  coinId: string
  amount: string
  buyPrice: string
}

function getOrCreateAnonId(): string {
  let uid = localStorage.getItem('portfolio_uid')
  if (!uid) {
    uid = crypto.randomUUID()
    localStorage.setItem('portfolio_uid', uid)
  }
  return uid
}

export default function PortfolioPage() {
  const [coins, setCoins] = useState<Coin[]>([])
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [coinCount, setCoinCount] = useState(1)
  const [rows, setRows] = useState<CoinRow[]>([{ coinId: '', amount: '', buyPrice: '' }])
  const [loading, setLoading] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [holdingsLoading, setHoldingsLoading] = useState(false)
  const [userId, setUserId] = useState<string>('')
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [migrating, setMigrating] = useState(false)
  const [notifyEnabled, setNotifyEnabled] = useState(true)
  const [notifySaved, setNotifySaved] = useState(false)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstanceRef = useRef<unknown>(null)

  // Load coins
  useEffect(() => {
    fetch('/api/coins')
      .then((r) => r.json())
      .then(setCoins)
      .catch(() => {})
  }, [])

  // Sync row count with coinCount
  useEffect(() => {
    setRows((prev) => {
      const next = Array.from({ length: coinCount }, (_, i) => prev[i] || { coinId: '', amount: '', buyPrice: '' })
      return next
    })
  }, [coinCount])

  const updateRow = (idx: number, field: keyof CoinRow, value: string) => {
    setRows((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], [field]: value }
      if (field === 'coinId') {
        const coin = coins.find((c) => c.id === value)
        if (coin) next[idx].buyPrice = coin.current_price.toString()
      }
      return next
    })
  }

  // Save email to notifications table
  const saveNotification = useCallback(async (uid: string, email: string, enabled: boolean) => {
    await supabase.from('notifications').upsert({ user_id: uid, email, enabled }, { onConflict: 'user_id' })
  }, [])

  // Load notification preference
  const loadNotifPref = useCallback(async (uid: string) => {
    const { data } = await supabase.from('notifications').select('enabled').eq('user_id', uid).single()
    if (data) setNotifyEnabled(data.enabled)
  }, [])

  const migrateAnonHoldings = useCallback(async (authenticatedUserId: string) => {
    const anonId = localStorage.getItem('portfolio_uid')
    if (!anonId) return
    const { data: anonHoldings } = await supabase.from('portfolios').select('id').eq('user_id', anonId)
    if (!anonHoldings || anonHoldings.length === 0) return
    setMigrating(true)
    try {
      await supabase.from('portfolios').update({ user_id: authenticatedUserId }).eq('user_id', anonId)
      localStorage.removeItem('portfolio_uid')
    } finally {
      setMigrating(false)
    }
  }, [])

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const authedUser = data.user
      setUser(authedUser)
      if (authedUser) {
        migrateAnonHoldings(authedUser.id).then(() => {
          setUserId(authedUser.id)
          setAuthLoading(false)
        })
        loadNotifPref(authedUser.id)
        if (authedUser.email) saveNotification(authedUser.id, authedUser.email, notifyEnabled)
      } else {
        setUserId(getOrCreateAnonId())
        setAuthLoading(false)
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const authedUser = session?.user ?? null
      setUser(authedUser)
      if (authedUser) {
        migrateAnonHoldings(authedUser.id).then(() => setUserId(authedUser.id))
        loadNotifPref(authedUser.id)
        if (authedUser.email) saveNotification(authedUser.id, authedUser.email, notifyEnabled)
      } else {
        setUserId(getOrCreateAnonId())
      }
    })

    return () => subscription.unsubscribe()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [migrateAnonHoldings])

  const loadHoldings = useCallback(async (uid: string) => {
    if (!uid) return
    setHoldingsLoading(true)
    const { data } = await supabase.from('portfolios').select('*').eq('user_id', uid)
    if (data) setHoldings(data)
    setHoldingsLoading(false)
  }, [])

  useEffect(() => {
    if (userId) loadHoldings(userId)
  }, [userId, loadHoldings])

  const enrichedHoldings: (Holding & { coin?: Coin })[] = holdings.map((h) => ({
    ...h,
    coin: coins.find((c) => c.id === h.coin_id),
  }))

  const totalValue = enrichedHoldings.reduce((sum, h) => h.coin ? sum + h.amount * h.coin.current_price : sum, 0)
  const totalCost = enrichedHoldings.reduce((sum, h) => sum + h.amount * h.buy_price, 0)
  const totalPnl = totalValue - totalCost
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  // Chart
  useEffect(() => {
    if (!chartRef.current || enrichedHoldings.length === 0) return
    const buildChart = async () => {
      const { Chart, registerables } = await import('chart.js')
      Chart.register(...registerables)
      if (chartInstanceRef.current) (chartInstanceRef.current as { destroy(): void }).destroy()
      const ctx = chartRef.current!.getContext('2d')!
      const labels = enrichedHoldings.map((h) => h.coin?.symbol.toUpperCase() || h.coin_id)
      const data = enrichedHoldings.map((h) => h.coin ? h.amount * h.coin.current_price : 0)
      const colors = ['#00d4ff', '#a855f7', '#f59e0b', '#00e676', '#ff3d57', '#84cc16', '#f97316', '#06b6d4']
      chartInstanceRef.current = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: colors.slice(0, data.length), borderColor: 'rgba(4,7,15,0.8)', borderWidth: 3 }] },
        options: {
          responsive: true, maintainAspectRatio: true,
          plugins: {
            legend: { position: 'right', labels: { color: '#8899bb', padding: 12, font: { size: 12 } } },
            tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${fmt(ctx.parsed)}` } },
          },
          cutout: '70%',
        },
      })
    }
    buildChart()
    return () => { if (chartInstanceRef.current) (chartInstanceRef.current as { destroy(): void }).destroy() }
  }, [enrichedHoldings])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userId) return
    setAddError(null)

    const inserts = rows.filter((r) => r.coinId && r.amount && r.buyPrice).map((r) => {
      const amt = parseFloat(r.amount)
      const price = parseFloat(r.buyPrice)
      return { coin_id: r.coinId, amount: amt, buy_price: price, user_id: userId }
    })

    if (inserts.length === 0) { setAddError('Συμπληρώστε τουλάχιστον ένα νόμισμα'); return }
    if (inserts.some((i) => i.amount <= 0 || i.buy_price <= 0 || isNaN(i.amount) || isNaN(i.buy_price))) {
      setAddError('Εισάγετε έγκυρες τιμές σε όλες τις γραμμές'); return
    }

    setLoading(true)
    try {
      const { data, error } = await supabase.from('portfolios').insert(inserts).select()
      if (error) { setAddError('Σφάλμα αποθήκευσης. Δοκιμάστε ξανά.') }
      else if (data) {
        setHoldings((prev) => [...prev, ...data])
        setRows([{ coinId: '', amount: '', buyPrice: '' }])
        setCoinCount(1)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (id: string) => {
    const { error } = await supabase.from('portfolios').delete().eq('id', id)
    if (!error) setHoldings((prev) => prev.filter((h) => h.id !== id))
  }

  const handleToggleNotify = async (enabled: boolean) => {
    setNotifyEnabled(enabled)
    setNotifySaved(false)
    if (user?.id && user.email) {
      await saveNotification(user.id, user.email, enabled)
      setNotifySaved(true)
      setTimeout(() => setNotifySaved(false), 2000)
    }
  }

  if (authLoading || migrating) {
    return (
      <div className="page-content page-enter">
        <div className="hero-section">
          <div className="section-label">Portfolio</div>
          <h1 className="page-section-title">Χαρτοφυλάκιο</h1>
        </div>
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
          {migrating ? 'Μεταφορά δεδομένων...' : 'Φόρτωση...'}
        </div>
      </div>
    )
  }

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Portfolio</div>
        <h1 className="page-section-title">Χαρτοφυλάκιο</h1>
        <p className="page-section-subtitle">Παρακολουθήστε τις επενδύσεις σας και υπολογίστε το P&amp;L σας.</p>
      </div>

      {!user && (
        <div className="portfolio-auth-banner">
          <div className="portfolio-auth-banner-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
              <path d="M12 2a5 5 0 1 0 0 10A5 5 0 0 0 12 2zm0 12c-5.33 0-8 2.67-8 4v2h16v-2c0-1.33-2.67-4-8-4z" fill="currentColor" opacity="0.7"/>
            </svg>
            <span>Συνδέσου για να αποθηκεύσεις το χαρτοφυλάκιό σου και να λαμβάνεις ημερήσιες ειδοποιήσεις</span>
          </div>
          <AuthButton />
        </div>
      )}

      <div className="portfolio-layout">
        <div className="portfolio-form">
          <h2>Προσθήκη Νομισμάτων</h2>

          {/* Coin count selector */}
          <div className="form-group" style={{ marginBottom: 20 }}>
            <label className="form-label">Πόσα νομίσματα θέλετε να προσθέσετε;</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setCoinCount(n)}
                  style={{
                    padding: '6px 16px',
                    borderRadius: 8,
                    border: '1px solid',
                    borderColor: coinCount === n ? 'var(--blue)' : 'var(--border)',
                    background: coinCount === n ? 'rgba(0,212,255,0.12)' : 'var(--surface)',
                    color: coinCount === n ? 'var(--blue)' : 'var(--muted)',
                    fontWeight: coinCount === n ? 700 : 400,
                    cursor: 'pointer',
                    fontSize: 14,
                  }}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleAdd}>
            {rows.map((row, idx) => (
              <div key={idx} style={{ marginBottom: 20, padding: coinCount > 1 ? '14px' : 0, background: coinCount > 1 ? 'var(--surface)' : 'transparent', borderRadius: coinCount > 1 ? 12 : 0, border: coinCount > 1 ? '1px solid var(--border)' : 'none' }}>
                {coinCount > 1 && <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10, fontWeight: 600 }}>Νόμισμα {idx + 1}</div>}
                <div className="form-group">
                  <label className="form-label">Κρυπτονόμισμα</label>
                  <select className="form-select" value={row.coinId} onChange={(e) => updateRow(idx, 'coinId', e.target.value)} required>
                    <option value="">Επιλέξτε...</option>
                    {coins.map((c) => (
                      <option key={c.id} value={c.id}>{c.name} ({c.symbol.toUpperCase()})</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div className="form-group">
                    <label className="form-label">Ποσότητα</label>
                    <input type="number" step="any" min="0" className="form-input" placeholder="π.χ. 0.5" value={row.amount} onChange={(e) => updateRow(idx, 'amount', e.target.value)} required />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Τιμή Αγοράς (€)</label>
                    <input type="number" step="any" min="0" className="form-input" placeholder="π.χ. 45000" value={row.buyPrice} onChange={(e) => updateRow(idx, 'buyPrice', e.target.value)} required />
                  </div>
                </div>
              </div>
            ))}

            {addError && <div style={{ color: 'var(--red)', fontSize: '0.82rem', marginBottom: 8 }}>{addError}</div>}
            <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Αποθήκευση...' : `+ Προσθήκη${coinCount > 1 ? ` ${coinCount} νομισμάτων` : ''}`}
            </button>
          </form>

          {/* Notification toggle — only for logged-in users */}
          {user && (
            <div style={{ marginTop: 20, padding: 16, background: 'var(--surface2)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Ημερήσιες Ειδοποιήσεις</div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>Email κάθε μέρα στις 17:00 (Δευ–Παρ)</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {notifySaved && <span style={{ fontSize: 11, color: 'var(--green)' }}>✓</span>}
                <button
                  type="button"
                  onClick={() => handleToggleNotify(!notifyEnabled)}
                  style={{
                    width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
                    background: notifyEnabled ? 'var(--blue)' : 'var(--surface3)',
                    position: 'relative', transition: 'background 0.2s',
                  }}
                >
                  <span style={{
                    position: 'absolute', top: 3, left: notifyEnabled ? 23 : 3,
                    width: 18, height: 18, borderRadius: '50%', background: '#fff',
                    transition: 'left 0.2s',
                  }} />
                </button>
              </div>
            </div>
          )}

          <div style={{ marginTop: 16, padding: 16, background: 'var(--surface2)', borderRadius: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Σύνολο P&amp;L</div>
            <div style={{ fontSize: 28, fontWeight: 800, fontFamily: 'var(--font-space)', color: totalPnl >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {totalPnl >= 0 ? '+' : ''}{fmt(totalPnl)}
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted2)', marginTop: 4 }}>
              {fmtPct(totalPnlPct)} | Κόστος: {fmt(totalCost)}
            </div>
          </div>
        </div>

        <div className="portfolio-chart-wrap">
          <h2>Κατανομή</h2>
          {enrichedHoldings.length > 0 ? (
            <>
              <div className="portfolio-total">
                <div className="portfolio-total-value">{fmt(totalValue)}</div>
                <div className="portfolio-total-label">Συνολική Αξία</div>
              </div>
              <canvas ref={chartRef} style={{ maxWidth: '100%', maxHeight: 220 }} />
            </>
          ) : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 14 }}>
              Δεν υπάρχουν ακόμα holdings.<br />Προσθέστε το πρώτο σας!
            </div>
          )}
        </div>
      </div>

      <div className="holdings-list">
        <h2>Holdings</h2>
        {holdingsLoading ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)' }}>Φόρτωση...</div>
        ) : enrichedHoldings.length === 0 ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)' }}>Δεν υπάρχουν αποθηκευμένα holdings.</div>
        ) : (
          enrichedHoldings.map((h) => {
            const currentVal = h.coin ? h.amount * h.coin.current_price : 0
            const costVal = h.amount * h.buy_price
            const pnl = currentVal - costVal
            const pnlPct = costVal > 0 ? (pnl / costVal) * 100 : 0
            return (
              <div key={h.id} className="holding-item">
                {h.coin && <Image src={h.coin.image} alt={h.coin.name} width={36} height={36} style={{ borderRadius: '50%' }} unoptimized />}
                <div className="holding-info">
                  <div className="holding-name">
                    {h.coin?.name || h.coin_id}
                    <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 6 }}>{h.coin?.symbol.toUpperCase()}</span>
                  </div>
                  <div className="holding-amount">{h.amount} × {fmt(h.buy_price)} = {fmt(costVal)}</div>
                </div>
                <div className="holding-value">
                  <div className="holding-current">{fmt(currentVal)}</div>
                  <div className={`holding-pnl ${pnl >= 0 ? 'pos' : 'neg'}`}>{pnl >= 0 ? '+' : ''}{fmt(pnl)} ({fmtPct(pnlPct)})</div>
                </div>
                <button className="btn-remove" onClick={() => handleRemove(h.id)}>✕</button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
