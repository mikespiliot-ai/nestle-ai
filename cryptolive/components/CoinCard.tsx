'use client'
import Image from 'next/image'
import { useEffect, useRef, useState, useCallback } from 'react'
import { fmt, fmtMktCap } from '@/lib/api'

export interface CoinData {
  id: string; name: string; symbol: string; image: string
  current_price: number; price_change_percentage_24h: number
  market_cap: number; total_volume: number
  high_24h: number; low_24h: number
  circulating_supply: number; max_supply: number | null
  ath: number; ath_change_percentage: number; market_cap_rank: number
  sparkline_in_7d?: { price: number[] }
}

function drawSparkline(canvas: HTMLCanvasElement, prices: number[], positive: boolean) {
  const ctx = canvas.getContext('2d')
  if (!ctx || prices.length < 2) return
  const w = canvas.width, h = canvas.height
  ctx.clearRect(0, 0, w, h)
  const min = Math.min(...prices), max = Math.max(...prices), range = max - min || 1
  const pts = prices.map((p, i) => ({ x: (i / (prices.length - 1)) * w, y: h - ((p - min) / range) * (h - 4) - 2 }))
  const color = positive ? '#3fb950' : '#f85149'
  const grad = ctx.createLinearGradient(0, 0, 0, h)
  grad.addColorStop(0, positive ? 'rgba(63,185,80,0.2)' : 'rgba(248,81,73,0.2)')
  grad.addColorStop(1, 'transparent')
  ctx.beginPath(); ctx.moveTo(pts[0].x, pts[0].y)
  for (let i = 1; i < pts.length; i++) {
    const mx = (pts[i-1].x + pts[i].x) / 2, my = (pts[i-1].y + pts[i].y) / 2
    ctx.quadraticCurveTo(pts[i-1].x, pts[i-1].y, mx, my)
  }
  ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath()
  ctx.fillStyle = grad; ctx.fill()
  ctx.beginPath(); ctx.moveTo(pts[0].x, pts[0].y)
  for (let i = 1; i < pts.length; i++) {
    const mx = (pts[i-1].x + pts[i].x) / 2, my = (pts[i-1].y + pts[i].y) / 2
    ctx.quadraticCurveTo(pts[i-1].x, pts[i-1].y, mx, my)
  }
  ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke()
}

export default function CoinCard({ coin, onClick, delay = 0 }: { coin: CoinData; onClick: (c: CoinData) => void; delay?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [flash, setFlash] = useState('')
  const prevPrice = useRef(coin.current_price)
  const positive = (coin.price_change_percentage_24h ?? 0) >= 0

  useEffect(() => {
    const c = canvasRef.current
    if (!c || !coin.sparkline_in_7d?.price?.length) return
    c.width = c.offsetWidth || 240; c.height = 48
    drawSparkline(c, coin.sparkline_in_7d.price, positive)
  }, [coin.sparkline_in_7d, positive])

  useEffect(() => {
    if (prevPrice.current === coin.current_price) return
    const dir = coin.current_price > prevPrice.current ? 'flash-up' : 'flash-down'
    prevPrice.current = coin.current_price
    setFlash(dir)
    const t = setTimeout(() => setFlash(''), 700)
    return () => clearTimeout(t)
  }, [coin.current_price])

  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget, rect = card.getBoundingClientRect()
    const ripple = document.createElement('span'), size = Math.max(rect.width, rect.height)
    Object.assign(ripple.style, { position: 'absolute', width: size+'px', height: size+'px', left: e.clientX-rect.left-size/2+'px', top: e.clientY-rect.top-size/2+'px', borderRadius: '50%', background: 'rgba(88,166,255,0.2)', animation: 'rippleEffect 0.6s ease-out forwards', pointerEvents: 'none' })
    card.appendChild(ripple)
    setTimeout(() => ripple.remove(), 700)
    onClick(coin)
  }, [coin, onClick])

  return (
    <div className={`coin-card${flash ? ' '+flash : ''}`} style={{ animationDelay: `${delay}ms` }} onClick={handleClick}>
      <div className="coin-header">
        <Image src={coin.image} alt={coin.name} width={36} height={36} style={{ borderRadius: '50%' }} unoptimized />
        <div><div className="coin-name">{coin.name}</div><div className="coin-symbol">{coin.symbol}</div></div>
      </div>
      <div className="coin-price">€{fmt(coin.current_price)}</div>
      <span className={`coin-change ${positive ? 'positive' : 'negative'}`}>
        {positive ? '+' : ''}{(coin.price_change_percentage_24h ?? 0).toFixed(2)}%
      </span>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.74rem', color: 'var(--muted)' }}>
        <span>MCap {fmtMktCap(coin.market_cap)}</span><span>Vol {fmtMktCap(coin.total_volume)}</span>
      </div>
      <div className="sparkline-wrap"><canvas ref={canvasRef} style={{ width: '100%', height: '48px' }} /></div>
    </div>
  )
}
