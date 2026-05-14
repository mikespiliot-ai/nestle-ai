'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import Splash from '@/components/Splash'
import CoinCard, { type CoinData } from '@/components/CoinCard'
import PriceModal from '@/components/PriceModal'
import { fetchMarketData, fetchExchangeRates } from '@/lib/api'
import { useRealtimePrices, BINANCE_PAIRS } from '@/hooks/useRealtimePrices'

const HERO_COINS = ['bitcoin', 'ethereum', 'solana', 'binancecoin']

function useParticleCanvas(ref: React.RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const pts = Array.from({ length: 55 }, () => ({ x: Math.random()*canvas.width, y: Math.random()*canvas.height, vx: (Math.random()-0.5)*0.35, vy: (Math.random()-0.5)*0.35, r: Math.random()*1.8+0.8 }))
    let raf: number
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      for (const p of pts) {
        p.x = (p.x+p.vx+canvas.width) % canvas.width
        p.y = (p.y+p.vy+canvas.height) % canvas.height
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI*2)
        ctx.fillStyle = 'rgba(88,166,255,0.45)'; ctx.fill()
        for (const q of pts) {
          const d = Math.hypot(p.x-q.x, p.y-q.y)
          if (d < 90) { ctx.beginPath(); ctx.moveTo(p.x,p.y); ctx.lineTo(q.x,q.y); ctx.strokeStyle=`rgba(88,166,255,${0.1*(1-d/90)})`; ctx.lineWidth=0.5; ctx.stroke() }
        }
      }
      raf = requestAnimationFrame(draw)
    }
    draw()
    const onResize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight }
    window.addEventListener('resize', onResize)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', onResize) }
  }, [ref])
}

export default function HomePage() {
  const [coins, setCoins] = useState<CoinData[]>([])
  const [eurRate, setEurRate] = useState(0.92)
  const [selected, setSelected] = useState<CoinData | null>(null)
  const [loading, setLoading] = useState(true)
  const particleRef = useRef<HTMLCanvasElement>(null)
  useParticleCanvas(particleRef)

  const loadData = useCallback(async () => {
    try {
      const [market, rates] = await Promise.all([fetchMarketData(), fetchExchangeRates()])
      setCoins(market)
      const usd = rates?.rates?.usd?.value ?? 1; const eur = rates?.rates?.eur?.value ?? 0.92
      setEurRate(eur / usd)
    } catch(e) { console.error(e) } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadData(); const t = setInterval(loadData, 5*60*1000); return () => clearInterval(t) }, [loadData])

  const handlePriceUpdate = useCallback((coinId: string, priceUsd: number) => {
    if (!BINANCE_PAIRS[coinId]) return
    const eur = priceUsd * eurRate
    setCoins(prev => prev.map(c => c.id === coinId ? { ...c, current_price: eur } : c))
    setSelected(prev => prev?.id === coinId ? { ...prev, current_price: eur } : prev)
  }, [eurRate])

  useRealtimePrices(handlePriceUpdate)

  const heroCoins = HERO_COINS.map(id => coins.find(c => c.id === id)).filter(Boolean) as CoinData[]

  if (loading) return <div className="loading"><div className="spinner" /> Loading prices...</div>

  return (
    <main>
      <Splash />
      <section className="hero" style={{ position: 'relative' }}>
        <canvas ref={particleRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }} />
        <div className="hero-blobs"><div className="blob blob-1" /><div className="blob blob-2" /><div className="blob blob-3" /></div>
        <div className="hero-content">
          <div className="live-badge"><span className="live-dot" />LIVE</div>
          <h1>Crypto Live Prices</h1>
          <p>Real-time cryptocurrency prices powered by Binance WebSocket</p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px,1fr))', gap: '1rem', maxWidth: '1000px', margin: '2rem auto 0', padding: '0 1.5rem', position: 'relative', zIndex: 1 }}>
          {heroCoins.map((coin, i) => <CoinCard key={coin.id} coin={coin} onClick={setSelected} delay={i*80} />)}
        </div>
      </section>
      <section className="section">
        <h2 className="section-title">All Cryptocurrencies</h2>
        <div className="grid">{coins.map((coin, i) => <CoinCard key={coin.id} coin={coin} onClick={setSelected} delay={i*35} />)}</div>
      </section>
      {selected && <PriceModal coin={selected} onClose={() => setSelected(null)} />}
    </main>
  )
}
