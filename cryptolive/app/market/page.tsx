'use client'
import { useEffect, useState, useCallback } from 'react'
import CoinCard, { type CoinData } from '@/components/CoinCard'
import PriceModal from '@/components/PriceModal'
import { fetchMarketData, fetchExchangeRates } from '@/lib/api'
import { useRealtimePrices, BINANCE_PAIRS } from '@/hooks/useRealtimePrices'

export default function MarketPage() {
  const [coins, setCoins] = useState<CoinData[]>([])
  const [eurRate, setEurRate] = useState(0.92)
  const [selected, setSelected] = useState<CoinData | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

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
  const filtered = coins.filter(c => c.name.toLowerCase().includes(search.toLowerCase()) || c.symbol.toLowerCase().includes(search.toLowerCase()))

  return (
    <main>
      <div className="page-header"><h1>Αγορά</h1><p>Όλα τα κρυπτονομίσματα σε πραγματικό χρόνο</p></div>
      <div className="section" style={{ paddingTop: '1rem' }}>
        <input className="input-field" placeholder="Αναζήτηση νομίσματος..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 340, marginBottom: '1.5rem' }} />
        {loading ? <div className="loading"><div className="spinner" /> Φόρτωση...</div> : <div className="grid">{filtered.map((coin, i) => <CoinCard key={coin.id} coin={coin} onClick={setSelected} delay={i*30} />)}</div>}
      </div>
      {selected && <PriceModal coin={selected} onClose={() => setSelected(null)} />}
    </main>
  )
}
