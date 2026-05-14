'use client'
import Image from 'next/image'
import { useEffect, useRef, useState, useCallback } from 'react'
import { fmt, fmtMktCap, fetchCoinChart } from '@/lib/api'
import type { CoinData } from './CoinCard'

const PERIODS = [
  { label: '1D', days: 1 }, { label: '5D', days: 5 }, { label: '1M', days: 30 },
  { label: '6M', days: 180 }, { label: '1Y', days: 365 }, { label: 'Max', days: 'max' as const },
]
type Cache = Record<string, { labels: string[]; prices: number[] }>

export default function PriceModal({ coin, onClose }: { coin: CoinData; onClose: () => void }) {
  const [period, setPeriod] = useState('1D')
  const [loading, setLoading] = useState(false)
  const chartRef = useRef<HTMLCanvasElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartInst = useRef<any>(null)
  const cache = useRef<Cache>({})
  const positive = (coin.price_change_percentage_24h ?? 0) >= 0

  const renderChart = useCallback((labels: string[], prices: number[]) => {
    if (!chartRef.current || !window.Chart) return
    chartInst.current?.destroy()
    const ctx = chartRef.current.getContext('2d')
    if (!ctx) return
    const up = prices[prices.length-1] >= prices[0]
    const color = up ? '#3fb950' : '#f85149'
    const grad = ctx.createLinearGradient(0, 0, 0, 280)
    grad.addColorStop(0, up ? 'rgba(63,185,80,0.25)' : 'rgba(248,81,73,0.25)')
    grad.addColorStop(1, 'rgba(0,0,0,0)')
    const step = Math.ceil(labels.length / 8)
    const dispLabels = labels.map((l, i) => i % step === 0 ? l : '')
    chartInst.current = new window.Chart(ctx, {
      type: 'line',
      data: { labels: dispLabels, datasets: [{ data: prices, borderColor: color, borderWidth: 2, fill: true, backgroundColor: grad, pointRadius: 0, tension: 0.3 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false, callbacks: { label: (c: {parsed:{y:number}}) => `€${fmt(c.parsed.y)}` } } },
        scales: {
          x: { grid: { color: 'rgba(48,54,61,0.5)' }, ticks: { color: '#8b949e', font: { size: 10 }, maxRotation: 0 } },
          y: { position: 'right', grid: { color: 'rgba(48,54,61,0.5)' }, ticks: { color: '#8b949e', font: { size: 10 }, callback: (v: unknown) => `€${fmt(v as number)}` } },
        },
      },
    })
  }, [])

  const loadChart = useCallback(async (p: string) => {
    const key = `${coin.id}_${p}`
    if (cache.current[key]) { renderChart(cache.current[key].labels, cache.current[key].prices); return }
    setLoading(true)
    try {
      const days = PERIODS.find(x => x.label === p)?.days ?? 1
      const data = await fetchCoinChart(coin.id, days)
      const prices: number[] = data.prices.map(([,v]: [number,number]) => v)
      const labels: string[] = data.prices.map(([ts]: [number,number]) => {
        const d = new Date(ts)
        return p === '1D' ? d.toLocaleTimeString('el-GR', { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString('el-GR', { month: 'short', day: 'numeric' })
      })
      cache.current[key] = { labels, prices }
      renderChart(labels, prices)
    } catch(e) { console.error(e) } finally { setLoading(false) }
  }, [coin.id, renderChart])

  useEffect(() => { loadChart(period); return () => { chartInst.current?.destroy(); chartInst.current = null } }, [period, loadChart])
  useEffect(() => { const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }; window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h) }, [onClose])

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-coin-info">
            <Image src={coin.image} alt={coin.name} width={44} height={44} style={{ borderRadius: '50%' }} unoptimized />
            <div><h2>{coin.name}</h2><div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{coin.symbol.toUpperCase()} · Rank #{coin.market_cap_rank}</div></div>
          </div>
          <div style={{ textAlign: 'right', marginLeft: 'auto', marginRight: '1rem' }}>
            <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>€{fmt(coin.current_price)}</div>
            <span className={`coin-change ${positive ? 'positive' : 'negative'}`}>{positive?'+':''}{(coin.price_change_percentage_24h??0).toFixed(2)}%</span>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="period-btns">{PERIODS.map(({label}) => <button key={label} className={`period-btn${period===label?' active':''}`} onClick={() => setPeriod(label)}>{label}</button>)}</div>
        <div className="chart-wrap" style={{ position: 'relative' }}>
          {loading && <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div className="spinner" /></div>}
          <canvas ref={chartRef} style={{ width: '100%', height: '100%' }} />
        </div>
        <div className="modal-stats">
          {[
            { label: 'Market Cap', value: fmtMktCap(coin.market_cap) },
            { label: 'Volume 24h', value: fmtMktCap(coin.total_volume) },
            { label: 'High 24h', value: `€${fmt(coin.high_24h)}`, color: 'var(--green)' },
            { label: 'Low 24h', value: `€${fmt(coin.low_24h)}`, color: 'var(--red)' },
            { label: 'Circulating', value: coin.circulating_supply ? (coin.circulating_supply/1e6).toFixed(2)+'M' : '—' },
            { label: 'Max Supply', value: coin.max_supply ? (coin.max_supply/1e6).toFixed(2)+'M' : '∞' },
            { label: 'ATH', value: `€${fmt(coin.ath)}` },
            { label: 'ATH Change', value: `${(coin.ath_change_percentage??0).toFixed(1)}%`, color: (coin.ath_change_percentage??0)>=0?'var(--green)':'var(--red)' },
          ].map(({label,value,color}) => (
            <div key={label} className="stat-item">
              <div className="stat-label">{label}</div>
              <div className="stat-value" style={color?{color}:{}}>{value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
