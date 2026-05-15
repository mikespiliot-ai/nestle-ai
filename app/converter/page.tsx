'use client'
import { useEffect, useState, useCallback } from 'react'
import { fmt } from '@/lib/format'

interface Coin {
  id: string
  name: string
  symbol: string
  current_price: number
}

interface Rate {
  name: string
  unit: string
  value: number
  type: string
}

const FIAT_CURRENCIES = [
  { id: 'eur', symbol: '€', name: 'Euro' },
  { id: 'usd', symbol: '$', name: 'US Dollar' },
  { id: 'gbp', symbol: '£', name: 'British Pound' },
  { id: 'jpy', symbol: '¥', name: 'Japanese Yen' },
  { id: 'chf', symbol: 'Fr', name: 'Swiss Franc' },
  { id: 'btc', symbol: '₿', name: 'Bitcoin' },
  { id: 'eth', symbol: 'Ξ', name: 'Ethereum' },
]

export default function ConverterPage() {
  const [coins, setCoins] = useState<Coin[]>([])
  const [rates, setRates] = useState<Record<string, Rate>>({})
  const [fromCoin, setFromCoin] = useState('bitcoin')
  const [toCurrency, setToCurrency] = useState('eur')
  const [fromAmount, setFromAmount] = useState('1')
  const [result, setResult] = useState<number | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/coins').then((r) => r.json()),
      fetch('/api/rates').then((r) => r.json()),
    ]).then(([coinsData, ratesData]) => {
      setCoins(coinsData)
      setRates(ratesData?.rates || {})
    }).catch(() => {})
  }, [])

  const calculate = useCallback(() => {
    const coin = coins.find((c) => c.id === fromCoin)
    if (!coin) return
    const amount = parseFloat(fromAmount) || 0
    // coin.current_price is in EUR
    const eurValue = amount * coin.current_price

    if (toCurrency === 'eur') {
      setResult(eurValue)
    } else {
      // Convert from EUR using CoinGecko rates (rates are in BTC, we need EUR-based)
      const eurRate = rates['eur']
      const toRate = rates[toCurrency]
      if (eurRate && toRate) {
        // eurRate.value = EUR per BTC, toRate.value = target per BTC
        const inTarget = eurValue * (toRate.value / eurRate.value)
        setResult(inTarget)
      }
    }
  }, [coins, fromCoin, fromAmount, toCurrency, rates])

  useEffect(() => {
    calculate()
  }, [calculate])

  const selectedCoin = coins.find((c) => c.id === fromCoin)
  const toCurrencyInfo = FIAT_CURRENCIES.find((f) => f.id === toCurrency) ||
    { symbol: toCurrency.toUpperCase(), name: toCurrency }

  const formatResult = (val: number): string => {
    if (toCurrency === 'jpy') return '¥' + Math.round(val).toLocaleString()
    if (['usd', 'gbp', 'chf'].includes(toCurrency)) {
      return toCurrencyInfo.symbol + val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
    if (toCurrency === 'btc') return val.toFixed(8) + ' BTC'
    if (toCurrency === 'eth') return val.toFixed(6) + ' ETH'
    return fmt(val)
  }

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Μετατροπέας</div>
        <h1 className="page-section-title">Μετατροπέας Κρυπτονομισμάτων</h1>
        <p className="page-section-subtitle">
          Μετατρέψτε κρυπτονομίσματα σε fiat και άλλα κρυπτονομίσματα.
        </p>
      </div>

      <div className="converter-wrap">
        <div className="converter-card">
          <h2>Μετατροπή</h2>

          <div className="converter-row">
            <div className="converter-field">
              <label className="converter-label">Ποσό</label>
              <input
                type="number"
                step="any"
                min="0"
                className="converter-input"
                value={fromAmount}
                onChange={(e) => setFromAmount(e.target.value)}
              />
            </div>
            <div className="converter-field">
              <label className="converter-label">Κρυπτονόμισμα</label>
              <select
                className="converter-select"
                value={fromCoin}
                onChange={(e) => setFromCoin(e.target.value)}
              >
                {coins.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.symbol.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ textAlign: 'center', margin: '4px 0', color: 'var(--muted)', fontSize: 24 }}>
            ↓
          </div>

          <div className="converter-row" style={{ marginTop: 4 }}>
            <div className="converter-field">
              <label className="converter-label">Νόμισμα</label>
              <select
                className="converter-select"
                value={toCurrency}
                onChange={(e) => setToCurrency(e.target.value)}
              >
                {FIAT_CURRENCIES.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.symbol})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {result !== null && (
            <div className="converter-result" style={{ marginTop: 20 }}>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 8 }}>
                {fromAmount} {selectedCoin?.name} =
              </div>
              <div className="converter-result-value">{formatResult(result)}</div>
              <div className="converter-result-label">
                1 {selectedCoin?.symbol.toUpperCase()} = {fmt(selectedCoin?.current_price || 0)}
              </div>
            </div>
          )}

          {selectedCoin && (
            <div style={{ marginTop: 20, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div style={{ background: 'var(--surface2)', borderRadius: 10, padding: 14, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Τιμή</div>
                <div style={{ fontWeight: 700 }}>{fmt(selectedCoin.current_price)}</div>
              </div>
              <div style={{ background: 'var(--surface2)', borderRadius: 10, padding: 14, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>Σύμβολο</div>
                <div style={{ fontWeight: 700 }}>{selectedCoin.symbol.toUpperCase()}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
