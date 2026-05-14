'use client'

import { useEffect, useRef, useCallback } from 'react'

export const BINANCE_PAIRS: Record<string, string> = {
  bitcoin:      'btcusdt',
  ethereum:     'ethusdt',
  binancecoin:  'bnbusdt',
  solana:       'solusdt',
  ripple:       'xrpusdt',
  dogecoin:     'dogeusdt',
  cardano:      'adausdt',
  'avalanche-2': 'avaxusdt',
  chainlink:    'linkusdt',
  tron:         'trxusdt',
  polkadot:     'dotusdt',
  'shiba-inu':  'shibusdt',
  'matic-network': 'maticusdt',
  litecoin:     'ltcusdt',
  'bitcoin-cash': 'bchusdt',
  near:         'nearusdt',
  uniswap:      'uniusdt',
}

type PriceUpdateCallback = (coinId: string, priceUsd: number) => void

export function useRealtimePrices(onUpdate: PriceUpdateCallback) {
  const wsRef = useRef<WebSocket | null>(null)
  const cbRef = useRef<PriceUpdateCallback>(onUpdate)

  useEffect(() => { cbRef.current = onUpdate }, [onUpdate])

  const connect = useCallback(() => {
    const streams = Object.values(BINANCE_PAIRS).map(p => `${p}@miniTicker`).join('/')
    const ws = new WebSocket(`wss://stream.binance.com:9443/stream?streams=${streams}`)
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const { data } = JSON.parse(e.data)
        if (!data?.s || !data?.c) return
        const coinId = Object.entries(BINANCE_PAIRS).find(([, v]) => v === data.s.toLowerCase())?.[0]
        if (coinId) cbRef.current(coinId, parseFloat(data.c))
      } catch { /* ignore */ }
    }
    ws.onclose = () => setTimeout(connect, 3000)
    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => { wsRef.current?.close(); wsRef.current = null }
  }, [connect])
}
