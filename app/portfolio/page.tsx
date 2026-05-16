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
  const [selectedCoinId, setSelectedCoinId] = useState('')
  const [amount, setAmount] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [loading, setLoading] = useState(false)
  const [userId, setUserId] = useState<string>('')
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [migrating, setMigrating] = useState(false)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstanceRef = useRef<unknown>(null)

  // Load coins
  useEffect(() => {
    fetch('/api/coins')
      .then((r) => r.json())
      .then(setCoins)
      .catch(() => {})
  }, [])

  // Migrate anonymous holdings to authenticated user
  const migrateAnonHoldings = useCallback(async (authenticatedUserId: string) => {
    const anonId = localStorage.getItem('portfolio_uid')
    if (!anonId) return

    const { data: anonHoldings } = await supabase
      .from('portfolios')
      .select('id')
      .eq('user_id', anonId)

    if (!anonHoldings || anonHoldings.length === 0) return

    setMigrating(true)
    try {
      await supabase
        .from('portfolios')
        .update({ user_id: authenticatedUserId })
        .eq('user_id', anonId)

      localStorage.removeItem('portfolio_uid')
    } finally {
      setMigrating(false)
    }
  }, [])

  // Track auth state and set userId
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const authedUser = data.user
      setUser(authedUser)
      if (authedUser) {
        migrateAnonHoldings(authedUser.id).then(() => {
          setUserId(authedUser.id)
          setAuthLoading(false)
        })
      } else {
        setUserId(getOrCreateAnonId())
        setAuthLoading(false)
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      const authedUser = session?.user ?? null
      setUser(authedUser)
      if (authedUser) {
        migrateAnonHoldings(authedUser.id).then(() => {
          setUserId(authedUser.id)
        })
      } else {
        setUserId(getOrCreateAnonId())
      }
    })

    return () => subscription.unsubscribe()
  }, [migrateAnonHoldings])

  // Load holdings from Supabase
  const loadHoldings = useCallback(async (uid: string) => {
    if (!uid) return
    const { data } = await supabase
      .from('portfolios')
      .select('*')
      .eq('user_id', uid)
    if (data) setHoldings(data)
  }, [])

  useEffect(() => {
    if (userId) loadHoldings(userId)
  }, [userId, loadHoldings])

  // Build holdings with coin data
  const enrichedHoldings: (Holding & { coin?: Coin })[] = holdings.map((h) => ({
    ...h,
    coin: coins.find((c) => c.id === h.coin_id),
  }))

  const totalValue = enrichedHoldings.reduce((sum, h) => {
    if (!h.coin) return sum
    return sum + h.amount * h.coin.current_price
  }, 0)

  const totalCost = enrichedHoldings.reduce((sum, h) => sum + h.amount * h.buy_price, 0)
  const totalPnl = totalValue - totalCost
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  // Chart
  useEffect(() => {
    if (!chartRef.current || enrichedHoldings.length === 0) return
    const buildChart = async () => {
      const { Chart, registerables } = await import('chart.js')
      Chart.register(...registerables)
      if (chartInstanceRef.current) {
        ;(chartInstanceRef.current as { destroy(): void }).destroy()
      }
      const ctx = chartRef.current!.getContext('2d')!
      const labels = enrichedHoldings.map((h) => h.coin?.symbol.toUpperCase() || h.coin_id)
      const data = enrichedHoldings.map((h) => h.coin ? h.amount * h.coin.current_price : 0)
      const colors = ['#00d4ff', '#a855f7', '#f59e0b', '#00e676', '#ff3d57', '#84cc16', '#f97316', '#06b6d4']

      chartInstanceRef.current = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: colors.slice(0, data.length),
            borderColor: 'rgba(4,7,15,0.8)',
            borderWidth: 3,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#8899bb', padding: 12, font: { size: 12 } },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.label}: ${fmt(ctx.parsed)}`,
              },
            },
          },
          cutout: '70%',
        },
      })
    }
    buildChart()
    return () => {
      if (chartInstanceRef.current) {
        ;(chartInstanceRef.current as { destroy(): void }).destroy()
      }
    }
  }, [enrichedHoldings])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCoinId || !amount || !buyPrice || !userId) return
    setLoading(true)
    try {
      const { data, error } = await supabase.from('portfolios').insert({
        coin_id: selectedCoinId,
        amount: parseFloat(amount),
        buy_price: parseFloat(buyPrice),
        user_id: userId,
      }).select()
      if (!error && data) {
        setHoldings((prev) => [...prev, data[0]])
        setAmount('')
        setBuyPrice('')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (id: string) => {
    await supabase.from('portfolios').delete().eq('id', id)
    setHoldings((prev) => prev.filter((h) => h.id !== id))
  }

  const handleCoinChange = (coinId: string) => {
    setSelectedCoinId(coinId)
    const coin = coins.find((c) => c.id === coinId)
    if (coin) setBuyPrice(coin.current_price.toString())
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
        <p className="page-section-subtitle">
          Παρακολουθήστε τις επενδύσεις σας και υπολογίστε το P&amp;L σας.
        </p>
      </div>

      {/* Auth banner — shown when NOT logged in */}
      {!user && (
        <div className="portfolio-auth-banner">
          <div className="portfolio-auth-banner-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={{ flexShrink: 0 }}>
              <path d="M12 2a5 5 0 1 0 0 10A5 5 0 0 0 12 2zm0 12c-5.33 0-8 2.67-8 4v2h16v-2c0-1.33-2.67-4-8-4z" fill="currentColor" opacity="0.7"/>
            </svg>
            <span>Συνδέσου με Google για να αποθηκεύσεις το χαρτοφυλάκιό σου</span>
          </div>
          <AuthButton />
        </div>
      )}

      <div className="portfolio-layout">
        <div className="portfolio-form">
          <h2>Προσθήκη Κρυπτονομίσματος</h2>
          <form onSubmit={handleAdd}>
            <div className="form-group">
              <label className="form-label">Κρυπτονόμισμα</label>
              <select
                className="form-select"
                value={selectedCoinId}
                onChange={(e) => handleCoinChange(e.target.value)}
                required
              >
                <option value="">Επιλέξτε κρυπτονόμισμα...</option>
                {coins.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.symbol.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Ποσότητα</label>
              <input
                type="number"
                step="any"
                min="0"
                className="form-input"
                placeholder="π.χ. 0.5"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Τιμή Αγοράς (€)</label>
              <input
                type="number"
                step="any"
                min="0"
                className="form-input"
                placeholder="π.χ. 45000"
                value={buyPrice}
                onChange={(e) => setBuyPrice(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Αποθήκευση...' : '+ Προσθήκη'}
            </button>
          </form>

          <div style={{ marginTop: 24, padding: 16, background: 'var(--surface2)', borderRadius: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Σύνολο P&amp;L</div>
            <div style={{
              fontSize: 28,
              fontWeight: 800,
              fontFamily: 'var(--font-space)',
              color: totalPnl >= 0 ? 'var(--green)' : 'var(--red)',
            }}>
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
        {enrichedHoldings.length === 0 ? (
          <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)' }}>
            Δεν υπάρχουν αποθηκευμένα holdings.
          </div>
        ) : (
          enrichedHoldings.map((h) => {
            const currentVal = h.coin ? h.amount * h.coin.current_price : 0
            const costVal = h.amount * h.buy_price
            const pnl = currentVal - costVal
            const pnlPct = costVal > 0 ? (pnl / costVal) * 100 : 0
            return (
              <div key={h.id} className="holding-item">
                {h.coin && (
                  <Image
                    src={h.coin.image}
                    alt={h.coin.name}
                    width={36}
                    height={36}
                    style={{ borderRadius: '50%' }}
                    unoptimized
                  />
                )}
                <div className="holding-info">
                  <div className="holding-name">
                    {h.coin?.name || h.coin_id}
                    <span style={{ color: 'var(--muted)', fontSize: 12, marginLeft: 6 }}>
                      {h.coin?.symbol.toUpperCase()}
                    </span>
                  </div>
                  <div className="holding-amount">
                    {h.amount} × {fmt(h.buy_price)} = {fmt(costVal)}
                  </div>
                </div>
                <div className="holding-value">
                  <div className="holding-current">{fmt(currentVal)}</div>
                  <div className={`holding-pnl ${pnl >= 0 ? 'pos' : 'neg'}`}>
                    {pnl >= 0 ? '+' : ''}{fmt(pnl)} ({fmtPct(pnlPct)})
                  </div>
                </div>
                <button className="btn-remove" onClick={() => handleRemove(h.id)}>
                  ✕
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
