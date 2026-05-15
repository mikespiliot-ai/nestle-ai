'use client'
import { useEffect, useRef, useState } from 'react'

interface TickerItem {
  symbol: string
  price: string
  change: number
}

const INITIAL_TICKERS: TickerItem[] = [
  { symbol: 'BTC', price: '—', change: 0 },
  { symbol: 'ETH', price: '—', change: 0 },
  { symbol: 'SOL', price: '—', change: 0 },
  { symbol: 'BNB', price: '—', change: 0 },
  { symbol: 'XRP', price: '—', change: 0 },
  { symbol: 'ADA', price: '—', change: 0 },
  { symbol: 'AVAX', price: '—', change: 0 },
  { symbol: 'DOT', price: '—', change: 0 },
  { symbol: 'LINK', price: '—', change: 0 },
  { symbol: 'DOGE', price: '—', change: 0 },
  { symbol: 'MATIC', price: '—', change: 0 },
  { symbol: 'UNI', price: '—', change: 0 },
]

const STREAMS = [
  'btcusdt', 'ethusdt', 'solusdt', 'bnbusdt',
  'xrpusdt', 'adausdt', 'avaxusdt', 'dotusdt',
  'linkusdt', 'dogeusdt', 'maticusdt', 'uniusdt',
]

const SYMBOL_MAP: Record<string, string> = {
  btcusdt: 'BTC', ethusdt: 'ETH', solusdt: 'SOL', bnbusdt: 'BNB',
  xrpusdt: 'XRP', adausdt: 'ADA', avaxusdt: 'AVAX', dotusdt: 'DOT',
  linkusdt: 'LINK', dogeusdt: 'DOGE', maticusdt: 'MATIC', uniusdt: 'UNI',
}

function formatPrice(price: number): string {
  if (price >= 1000) return '$' + price.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  if (price >= 1) return '$' + price.toFixed(2)
  return '$' + price.toFixed(4)
}

export default function TickerTape() {
  const [tickers, setTickers] = useState<TickerItem[]>(INITIAL_TICKERS)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const streamStr = STREAMS.map((s) => `${s}@ticker`).join('/')
    const url = `wss://stream.binance.com:9443/stream?streams=${streamStr}`

    function connect() {
      try {
        const ws = new WebSocket(url)
        wsRef.current = ws

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            const data = msg.data
            if (!data) return
            const sym = SYMBOL_MAP[data.s?.toLowerCase()]
            if (!sym) return
            const price = parseFloat(data.c)
            const change = parseFloat(data.P)
            setTickers((prev) =>
              prev.map((t) =>
                t.symbol === sym
                  ? { ...t, price: formatPrice(price), change }
                  : t
              )
            )
          } catch {
            // ignore parse errors
          }
        }

        ws.onerror = () => {
          ws.close()
        }

        ws.onclose = () => {
          // reconnect after 5s
          setTimeout(connect, 5000)
        }
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

  const doubled = [...tickers, ...tickers]

  return (
    <div className="ticker-wrap">
      <div className="ticker-track">
        {doubled.map((item, idx) => (
          <div key={idx} className="ticker-item">
            <span className="t-symbol">{item.symbol}</span>
            <span className="t-price">{item.price}</span>
            <span className={`t-change ${item.change >= 0 ? 'pos' : 'neg'}`}>
              {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
