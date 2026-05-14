'use client'
import { useEffect, useState, useCallback } from 'react'
import Image from 'next/image'
import PriceModal from '@/components/PriceModal'
import { fetchMarketData, fmt } from '@/lib/api'
import type { CoinData } from '@/components/CoinCard'

export default function MoversPage() {
  const [coins, setCoins] = useState<CoinData[]>([])
  const [selected, setSelected] = useState<CoinData | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    try { const market = await fetchMarketData(); setCoins(market) }
    catch(e) { console.error(e) } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadData(); const t = setInterval(loadData, 5*60*1000); return () => clearInterval(t) }, [loadData])

  const sorted = [...coins].sort((a,b) => (b.price_change_percentage_24h??0) - (a.price_change_percentage_24h??0))
  const gainers = sorted.slice(0, 10)
  const losers = [...sorted].reverse().slice(0, 10)

  return (
    <main>
      <div className="page-header"><h1>Top Movers</h1><p>Μεγαλύτερες κινήσεις τελευταίων 24 ωρών</p></div>
      {loading ? <div className="loading"><div className="spinner" /></div> : (
        <div className="section">
          <div className="movers-grid">
            <div>
              <div className="section-title">🚀 Top Gainers</div>
              <div className="movers-list">
                {gainers.map((coin,i) => (
                  <div key={coin.id} className="mover-item" onClick={() => setSelected(coin)}>
                    <div className="mover-left">
                      <span className="mover-rank">#{i+1}</span>
                      <Image src={coin.image} alt={coin.name} width={32} height={32} unoptimized />
                      <div><div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{coin.name}</div><div style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>€{fmt(coin.current_price)}</div></div>
                    </div>
                    <span className="coin-change positive">+{(coin.price_change_percentage_24h??0).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="section-title">📉 Top Losers</div>
              <div className="movers-list">
                {losers.map((coin,i) => (
                  <div key={coin.id} className="mover-item" onClick={() => setSelected(coin)}>
                    <div className="mover-left">
                      <span className="mover-rank">#{i+1}</span>
                      <Image src={coin.image} alt={coin.name} width={32} height={32} unoptimized />
                      <div><div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{coin.name}</div><div style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>€{fmt(coin.current_price)}</div></div>
                    </div>
                    <span className="coin-change negative">{(coin.price_change_percentage_24h??0).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {selected && <PriceModal coin={selected} onClose={() => setSelected(null)} />}
    </main>
  )
}
