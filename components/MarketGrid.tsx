'use client'
import { useState, useMemo, useCallback } from 'react'
import Image from 'next/image'
import { fmt, fmtMktCap, fmtPct } from '@/lib/format'
import SparklineChart from './SparklineChart'
import CoinModal from './CoinModal'

interface Coin {
  id: string
  name: string
  symbol: string
  image: string
  current_price: number
  price_change_percentage_24h: number
  market_cap: number
  total_volume: number
  circulating_supply: number
  sparkline_in_7d?: { price: number[] }
  market_cap_rank: number
}

type SortKey = 'market_cap' | 'current_price' | 'price_change_percentage_24h' | 'total_volume'

interface MarketGridProps {
  coins: Coin[]
}

export default function MarketGrid({ coins: initialCoins }: MarketGridProps) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('market_cap')
  const [sortDesc, setSortDesc] = useState(true)
  const [selectedCoin, setSelectedCoin] = useState<Coin | null>(null)

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortDesc((d) => !d)
    } else {
      setSortKey(key)
      setSortDesc(true)
    }
  }, [sortKey])

  const filtered = useMemo(() => {
    let coins = [...initialCoins]
    if (search.trim()) {
      const q = search.toLowerCase()
      coins = coins.filter(
        (c) => c.name.toLowerCase().includes(q) || c.symbol.toLowerCase().includes(q)
      )
    }
    coins.sort((a, b) => {
      const av = a[sortKey] ?? 0
      const bv = b[sortKey] ?? 0
      return sortDesc ? bv - av : av - bv
    })
    return coins
  }, [initialCoins, search, sortKey, sortDesc])

  return (
    <>
      <div className="market-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Αναζήτηση κρυπτονομίσματος..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="sort-btns">
          <button
            className={`sort-btn${sortKey === 'market_cap' ? ' active' : ''}`}
            onClick={() => handleSort('market_cap')}
          >
            Market Cap {sortKey === 'market_cap' ? (sortDesc ? '↓' : '↑') : ''}
          </button>
          <button
            className={`sort-btn${sortKey === 'price_change_percentage_24h' ? ' active' : ''}`}
            onClick={() => handleSort('price_change_percentage_24h')}
          >
            24h {sortKey === 'price_change_percentage_24h' ? (sortDesc ? '↓' : '↑') : ''}
          </button>
          <button
            className={`sort-btn${sortKey === 'total_volume' ? ' active' : ''}`}
            onClick={() => handleSort('total_volume')}
          >
            Volume {sortKey === 'total_volume' ? (sortDesc ? '↓' : '↑') : ''}
          </button>
        </div>
      </div>

      <div className="market-grid">
        {filtered.map((coin) => {
          const positive = coin.price_change_percentage_24h >= 0
          return (
            <div
              key={coin.id}
              className="coin-card"
              onClick={() => setSelectedCoin(coin)}
            >
              <div className="card-header">
                <Image
                  src={coin.image}
                  alt={coin.name}
                  width={36}
                  height={36}
                  className="card-img"
                  unoptimized
                />
                <div className="card-name-group">
                  <div className="card-name">{coin.name}</div>
                  <div className="card-symbol">{coin.symbol.toUpperCase()}</div>
                </div>
                <div className="card-rank">#{coin.market_cap_rank}</div>
              </div>
              <div className="card-price">{fmt(coin.current_price)}</div>
              <div className={`card-change ${positive ? 'pos' : 'neg'}`}>
                {positive ? '▲' : '▼'} {fmtPct(coin.price_change_percentage_24h)}
              </div>
              {coin.sparkline_in_7d?.price && (
                <SparklineChart data={coin.sparkline_in_7d.price} positive={positive} />
              )}
              <div className="card-meta">
                <span>MCap: {fmtMktCap(coin.market_cap)}</span>
                <span>Vol: {fmtMktCap(coin.total_volume)}</span>
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--muted)' }}>
          Δεν βρέθηκαν αποτελέσματα για &ldquo;{search}&rdquo;
        </div>
      )}

      {selectedCoin && (
        <CoinModal coin={selectedCoin} onClose={() => setSelectedCoin(null)} />
      )}
    </>
  )
}
