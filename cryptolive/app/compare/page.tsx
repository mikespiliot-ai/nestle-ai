'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import Image from 'next/image'
import { fetchMarketData, fetchCoinChart, fmt, fmtMktCap, COINS } from '@/lib/api'

interface Coin {
  id: string; name: string; symbol: string; image: string
  current_price: number; price_change_percentage_24h: number
  market_cap: number; total_volume: number
  high_24h: number; low_24h: number
  ath: number; ath_change_percentage: number; market_cap_rank: number
}

const PERIODS = [{ label: '7D', days: 7 }, { label: '1M', days: 30 }, { label: '6M', days: 180 }, { label: '1Y', days: 365 }]

export default function ComparePage() {
  const [coins, setCoins] = useState<Coin[]>([])
  const [coinA, setCoinA] = useState('bitcoin')
  const [coinB, setCoinB] = useState('ethereum')
  const [period, setPeriod] = useState('7D')
  const [loading, setLoading] = useState(true)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInst = useRef<{ destroy: () => void } | null>(null)

  useEffect(() => { fetchMarketData().then(setCoins).catch(console.error).finally(() => setLoading(false)) }, [])

  const buildChart = useCallback(async () => {
    if (!coins.length || !window.Chart || !chartRef.current) return
    const days = PERIODS.find(p=>p.label===period)?.days ?? 7
    try {
      const [dataA, dataB] = await Promise.all([fetchCoinChart(coinA, days), fetchCoinChart(coinB, days)])
      const pricesA: number[] = dataA.prices.map((pt:[number,number]) => pt[1])
      const pricesB: number[] = dataB.prices.map((pt:[number,number]) => pt[1])
      const labels: string[] = dataA.prices.map((pt:[number,number]) => new Date(pt[0]).toLocaleDateString('el-GR', { month: 'short', day: 'numeric' }))
      const normA = pricesA.map(p => (p/pricesA[0])*100)
      const normB = pricesB.map(p => (p/pricesB[0])*100)
      const step = Math.ceil(labels.length/10)
      const dispLabels = labels.map((l,i) => i%step===0?l:'')
      chartInst.current?.destroy()
      const ctx = chartRef.current.getContext('2d'); if (!ctx) return
      chartInst.current = new window.Chart(ctx, {
        type: 'line',
        data: { labels: dispLabels, datasets: [
          { label: coins.find(c=>c.id===coinA)?.name??coinA, data: normA, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false },
          { label: coins.find(c=>c.id===coinB)?.name??coinB, data: normB, borderColor: '#a371f7', backgroundColor: 'rgba(163,113,247,0.1)', borderWidth: 2, pointRadius: 0, tension: 0.3, fill: false },
        ]},
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#8b949e', font: { size: 11 } } }, tooltip: { mode: 'index', intersect: false, callbacks: { label: (c:{dataset:{label:string};parsed:{y:number}}) => `${c.dataset.label}: ${c.parsed.y.toFixed(2)}%` } } },
          scales: { x: { grid: { color: 'rgba(48,54,61,0.5)' }, ticks: { color: '#8b949e', font: { size: 10 }, maxRotation: 0 } }, y: { position: 'right', grid: { color: 'rgba(48,54,61,0.5)' }, ticks: { color: '#8b949e', font: { size: 10 }, callback: (v:unknown) => `${Number(v).toFixed(0)}%` } } },
        },
      })
    } catch(e) { console.error(e) }
  }, [coins, coinA, coinB, period])

  useEffect(() => { buildChart() }, [buildChart])

  const cA = coins.find(c=>c.id===coinA), cB = coins.find(c=>c.id===coinB)

  return (
    <main>
      <div className="page-header"><h1>Σύγκριση</h1><p>Σύγκριση δύο κρυπτονομισμάτων side-by-side</p></div>
      <div className="section">
        <div className="compare-selectors">
          <select className="compare-select" value={coinA} onChange={e=>setCoinA(e.target.value)}>{COINS.map(id=><option key={id} value={id}>{coins.find(c=>c.id===id)?.name??id}</option>)}</select>
          <select className="compare-select" value={coinB} onChange={e=>setCoinB(e.target.value)}>{COINS.map(id=><option key={id} value={id}>{coins.find(c=>c.id===id)?.name??id}</option>)}</select>
        </div>
        {loading ? <div className="loading"><div className="spinner" /></div> : cA && cB ? (
          <>
            <div className="compare-stats">
              {[cA,cB].map(coin=>(
                <div key={coin.id} className="compare-coin-stats">
                  <div className="compare-coin-header">
                    <Image src={coin.image} alt={coin.name} width={40} height={40} unoptimized />
                    <div><div style={{ fontWeight:700 }}>{coin.name}</div><div style={{ color:'var(--muted)',fontSize:'0.8rem' }}>Rank #{coin.market_cap_rank}</div></div>
                    <span className={`coin-change ${(coin.price_change_percentage_24h??0)>=0?'positive':'negative'}`} style={{ marginLeft:'auto' }}>{(coin.price_change_percentage_24h??0)>=0?'+':''}{(coin.price_change_percentage_24h??0).toFixed(2)}%</span>
                  </div>
                  {[['Τιμή',`€${fmt(coin.current_price)}`],['Market Cap',fmtMktCap(coin.market_cap)],['Volume 24h',fmtMktCap(coin.total_volume)],['High 24h',`€${fmt(coin.high_24h)}`],['Low 24h',`€${fmt(coin.low_24h)}`],['ATH',`€${fmt(coin.ath)}`]].map(([l,v])=>(
                    <div key={l} className="compare-stat-row"><span className="compare-stat-label">{l}</span><span>{v}</span></div>
                  ))}
                </div>
              ))}
            </div>
            <div className="period-btns">{PERIODS.map(p=><button key={p.label} className={`period-btn${period===p.label?' active':''}`} onClick={()=>setPeriod(p.label)}>{p.label}</button>)}</div>
            <div className="compare-chart-wrap"><canvas ref={chartRef} style={{ width:'100%',height:'100%' }} /></div>
            <p style={{ color:'var(--muted)',fontSize:'0.75rem',textAlign:'center' }}>Κανονικοποιημένη τιμή (αρχή περιόδου = 100%)</p>
          </>
        ) : null}
      </div>
    </main>
  )
}
