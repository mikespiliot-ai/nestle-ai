'use client'
import { useEffect, useState, useCallback } from 'react'
import { fetchMarketData, fetchExchangeRates, fmt, FIAT } from '@/lib/api'

interface Coin { id: string; name: string; symbol: string; current_price: number }

export default function ConverterPage() {
  const [coins, setCoins] = useState<Coin[]>([])
  const [rates, setRates] = useState<Record<string,number>>({})
  const [amount, setAmount] = useState('1')
  const [fromType, setFromType] = useState<'crypto'|'fiat'>('crypto')
  const [fromCoin, setFromCoin] = useState('bitcoin')
  const [fromFiat, setFromFiat] = useState('eur')
  const [toFiat, setToFiat] = useState('usd')
  const [toCoin, setToCoin] = useState('ethereum')
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(async () => {
    try {
      const [market, rd] = await Promise.all([fetchMarketData(), fetchExchangeRates()])
      setCoins(market)
      const r: Record<string,number> = {}
      for (const [k,v] of Object.entries(rd?.rates??{})) r[k] = (v as {value:number}).value
      setRates(r)
    } catch(e) { console.error(e) } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const compute = (): string => {
    const n = parseFloat(amount)
    if (!n || !rates.usd) return '—'
    if (fromType==='crypto') {
      const coin = coins.find(c=>c.id===fromCoin)
      if (!coin) return '—'
      const priceUsd = coin.current_price / (rates.eur/rates.usd)
      const toRate = rates[toFiat]
      if (!toRate) return '—'
      return `${fmt(n * priceUsd * (toRate/rates.usd))} ${FIAT.find(f=>f.id===toFiat)?.symbol??toFiat.toUpperCase()}`
    } else {
      const coin = coins.find(c=>c.id===toCoin)
      if (!coin) return '—'
      const fromRate = rates[fromFiat]
      if (!fromRate) return '—'
      const amtUsd = n * (rates.usd/fromRate)
      const priceUsd = coin.current_price / (rates.eur/rates.usd)
      return `${fmt(amtUsd/priceUsd)} ${coin.symbol.toUpperCase()}`
    }
  }

  const btnStyle = (active: boolean) => ({ flex: 1, background: active?'var(--accent)':'var(--surface)', color: active?'#000':'var(--muted)', border: '1px solid var(--border)', padding: '0.65rem', borderRadius: 'var(--radius)', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' })

  return (
    <main>
      <div className="page-header"><h1>Μετατροπέας</h1><p>Μετατρέψτε μεταξύ κρυπτονομισμάτων και fiat</p></div>
      <div className="section">
        <div className="converter-wrap">
          <div style={{ display:'flex',gap:'0.5rem',marginBottom:'1.5rem' }}>
            <button style={btnStyle(fromType==='crypto')} onClick={()=>setFromType('crypto')}>Crypto → Fiat</button>
            <button style={btnStyle(fromType==='fiat')} onClick={()=>setFromType('fiat')}>Fiat → Crypto</button>
          </div>
          <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:'var(--radius)',padding:'1.25rem',marginBottom:'1rem' }}>
            <div style={{ fontSize:'0.75rem',color:'var(--muted)',marginBottom:'0.5rem' }}>Από</div>
            <div className="converter-row">
              <input className="input-field" type="number" min="0" step="any" value={amount} onChange={e=>setAmount(e.target.value)} />
              {fromType==='crypto'
                ? <select className="input-field compare-select" value={fromCoin} onChange={e=>setFromCoin(e.target.value)}>{coins.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
                : <select className="input-field compare-select" value={fromFiat} onChange={e=>setFromFiat(e.target.value)}>{FIAT.map(f=><option key={f.id} value={f.id}>{f.symbol}</option>)}</select>
              }
            </div>
          </div>
          <div style={{ background:'var(--surface)',border:'1px solid var(--border)',borderRadius:'var(--radius)',padding:'1.25rem',marginBottom:'1.5rem' }}>
            <div style={{ fontSize:'0.75rem',color:'var(--muted)',marginBottom:'0.5rem' }}>Σε</div>
            {fromType==='crypto'
              ? <select className="input-field compare-select" value={toFiat} onChange={e=>setToFiat(e.target.value)}>{FIAT.map(f=><option key={f.id} value={f.id}>{f.symbol} — {f.sign}</option>)}</select>
              : <select className="input-field compare-select" value={toCoin} onChange={e=>setToCoin(e.target.value)}>{coins.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select>
            }
          </div>
          <div className="converter-result">
            {loading ? <div className="spinner" style={{ margin:'0 auto' }} /> : (
              <><div style={{ color:'var(--muted)',fontSize:'0.8rem',marginBottom:'0.5rem' }}>{amount} {fromType==='crypto'?coins.find(c=>c.id===fromCoin)?.symbol?.toUpperCase():FIAT.find(f=>f.id===fromFiat)?.symbol} =</div>
              <div className="converter-result-amount">{compute()}</div></>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
