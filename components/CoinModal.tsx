'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import Image from 'next/image'
import { fmt, fmtMktCap, fmtPct } from '@/lib/format'

interface CoinData {
  id: string
  name: string
  symbol: string
  image: string
  current_price: number
  price_change_percentage_24h: number
  market_cap: number
  total_volume: number
  circulating_supply: number
}

interface CoinModalProps {
  coin: CoinData | null
  onClose: () => void
}

const PERIODS = [
  { label: '1D', days: 1 },
  { label: '5D', days: 5 },
  { label: '7D', days: 7 },
  { label: '1M', days: 30 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'Max', days: 'max' as const },
]

export default function CoinModal({ coin, onClose }: CoinModalProps) {
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstanceRef = useRef<unknown>(null)
  const [activePeriod, setActivePeriod] = useState(7)
  const [chartData, setChartData] = useState<number[]>([])
  const [chartLabels, setChartLabels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const fetchChart = useCallback(
    async (days: number | 'max') => {
      if (!coin) return
      setLoading(true)
      try {
        const res = await fetch(
          `https://api.coingecko.com/api/v3/coins/${coin.id}/market_chart?vs_currency=eur&days=${days}`
        )
        if (!res.ok) return
        const json = await res.json()
        const prices: [number, number][] = json.prices || []
        setChartData(prices.map((p) => p[1]))
        setChartLabels(
          prices.map((p) => {
            const d = new Date(p[0])
            return days === 1
              ? d.toLocaleTimeString('el-GR', { hour: '2-digit', minute: '2-digit' })
              : d.toLocaleDateString('el-GR', { month: 'short', day: 'numeric' })
          })
        )
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    },
    [coin]
  )

  useEffect(() => {
    if (coin) {
      fetchChart(7)
      setActivePeriod(7)
    }
  }, [coin, fetchChart])

  useEffect(() => {
    if (!chartRef.current || chartData.length < 2) return

    const buildChart = async () => {
      const { Chart, registerables } = await import('chart.js')
      Chart.register(...registerables)

      if (chartInstanceRef.current) {
        ;(chartInstanceRef.current as { destroy(): void }).destroy()
      }

      const ctx = chartRef.current!.getContext('2d')!
      const positive = chartData[chartData.length - 1] >= chartData[0]
      const color = positive ? '#00e676' : '#ff3d57'

      const gradient = ctx.createLinearGradient(0, 0, 0, 250)
      gradient.addColorStop(0, positive ? 'rgba(0,230,118,0.25)' : 'rgba(255,61,87,0.25)')
      gradient.addColorStop(1, 'rgba(0,0,0,0)')

      chartInstanceRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: chartLabels,
          datasets: [
            {
              data: chartData,
              borderColor: color,
              backgroundColor: gradient,
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.4,
              fill: true,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: 'rgba(7,13,26,0.95)',
              borderColor: 'rgba(255,255,255,0.1)',
              borderWidth: 1,
              titleColor: '#8899bb',
              bodyColor: '#f0f4ff',
              callbacks: {
                label: (ctx) => ` ${fmt(ctx.parsed.y ?? 0)}`,
              },
            },
          },
          scales: {
            x: {
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: {
                color: '#6b7a99',
                maxTicksLimit: 6,
                font: { size: 11 },
              },
            },
            y: {
              grid: { color: 'rgba(255,255,255,0.04)' },
              ticks: {
                color: '#6b7a99',
                font: { size: 11 },
                callback: (val) => fmt(Number(val)),
              },
              position: 'right',
            },
          },
          interaction: { mode: 'index', intersect: false },
        },
      })
    }

    buildChart()
  }, [chartData, chartLabels])

  // Destroy chart on unmount
  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        ;(chartInstanceRef.current as { destroy(): void }).destroy()
      }
    }
  }, [])

  if (!coin) return null

  const positive = coin.price_change_percentage_24h >= 0

  return (
    <div className={`modal-overlay open`} onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal-card">
        <div className="modal-header">
          <Image
            src={coin.image}
            alt={coin.name}
            width={48}
            height={48}
            style={{ borderRadius: '50%' }}
            unoptimized
          />
          <div>
            <div className="modal-name">{coin.name}</div>
            <div className="modal-symbol">{coin.symbol.toUpperCase()}</div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-price">{fmt(coin.current_price)}</div>
        <div style={{ marginBottom: 16 }}>
          <span className={`card-change ${positive ? 'pos' : 'neg'}`}>
            {positive ? '▲' : '▼'} {fmtPct(coin.price_change_percentage_24h)}
          </span>
        </div>

        <div className="modal-stats">
          <div className="modal-stat">
            <div className="modal-stat-label">Market Cap</div>
            <div className="modal-stat-value">{fmtMktCap(coin.market_cap)}</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-label">Volume 24h</div>
            <div className="modal-stat-value">{fmtMktCap(coin.total_volume)}</div>
          </div>
          <div className="modal-stat">
            <div className="modal-stat-label">Κυκλοφορία</div>
            <div className="modal-stat-value">
              {coin.circulating_supply
                ? (coin.circulating_supply / 1e6).toFixed(2) + 'M'
                : '—'}
            </div>
          </div>
        </div>

        <div className="period-btns">
          {PERIODS.map((p) => (
            <button
              key={p.label}
              className={`period-btn${activePeriod === p.days ? ' active' : ''}`}
              onClick={() => {
                setActivePeriod(p.days as number)
                fetchChart(p.days)
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="modal-chart-wrap">
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)' }}>
              Φόρτωση...
            </div>
          ) : (
            <canvas ref={chartRef} />
          )}
        </div>
      </div>
    </div>
  )
}
