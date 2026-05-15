'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import Image from 'next/image'
import { fmt, fmtPct } from '@/lib/format'
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

interface HeroGridProps {
  coins: Coin[]
}

const HERO_IDS = ['bitcoin', 'ethereum', 'solana', 'binancecoin']
const WS_PAIRS: Record<string, string> = {
  bitcoin: 'btcusdt',
  ethereum: 'ethusdt',
  solana: 'solusdt',
  binancecoin: 'bnbusdt',
}

// EUR/USD rough rate (we'll use BTC price ratio)
const EUR_USD_RATE = 0.925

export default function HeroGrid({ coins: initialCoins }: HeroGridProps) {
  const [coins, setCoins] = useState<Coin[]>(
    initialCoins.filter((c) => HERO_IDS.includes(c.id))
  )
  const [selectedCoin, setSelectedCoin] = useState<Coin | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const tiltRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const pairs = HERO_IDS.map((id) => `${WS_PAIRS[id]}@ticker`).join('/')
    const url = `wss://stream.binance.com:9443/stream?streams=${pairs}`

    function connect() {
      try {
        const ws = new WebSocket(url)
        wsRef.current = ws

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            const data = msg.data
            if (!data) return
            const pairId = Object.entries(WS_PAIRS).find(
              ([, v]) => v === data.s?.toLowerCase()
            )?.[0]
            if (!pairId) return
            const priceUsd = parseFloat(data.c)
            const priceEur = priceUsd * EUR_USD_RATE
            setCoins((prev) =>
              prev.map((c) =>
                c.id === pairId ? { ...c, current_price: priceEur } : c
              )
            )
          } catch {
            // ignore
          }
        }

        ws.onerror = () => ws.close()
        ws.onclose = () => setTimeout(connect, 5000)
      } catch {
        setTimeout(connect, 5000)
      }
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>, idx: number) => {
    const card = tiltRefs.current[idx]
    if (!card) return
    const rect = card.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    card.style.transform = `translateY(-4px) rotateX(${-y * 8}deg) rotateY(${x * 8}deg) scale(1.02)`
  }, [])

  const handleMouseLeave = useCallback((idx: number) => {
    const card = tiltRefs.current[idx]
    if (!card) return
    card.style.transform = ''
  }, [])

  return (
    <>
      <div className="hero-grid">
        {coins.map((coin, idx) => {
          const positive = coin.price_change_percentage_24h >= 0
          return (
            <div
              key={coin.id}
              ref={(el) => { tiltRefs.current[idx] = el }}
              className="coin-card"
              style={{ transition: 'transform 0.1s ease, border-color 0.2s, background 0.2s, box-shadow 0.2s' }}
              onClick={() => setSelectedCoin(coin)}
              onMouseMove={(e) => handleMouseMove(e, idx)}
              onMouseLeave={() => handleMouseLeave(idx)}
            >
              <div className="card-header">
                <Image
                  src={coin.image}
                  alt={coin.name}
                  width={40}
                  height={40}
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
            </div>
          )
        })}
      </div>

      {selectedCoin && (
        <CoinModal coin={selectedCoin} onClose={() => setSelectedCoin(null)} />
      )}
    </>
  )
}
