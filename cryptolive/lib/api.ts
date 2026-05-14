export const COINS = [
  'bitcoin','ethereum','tether','binancecoin','solana','ripple',
  'usd-coin','staked-ether','dogecoin','cardano','avalanche-2','chainlink',
  'tron','polkadot','shiba-inu','matic-network','litecoin','bitcoin-cash',
  'near','uniswap'
]

export const FIAT = [
  { id: 'eur', symbol: 'EUR', sign: '€' },
  { id: 'usd', symbol: 'USD', sign: '$' },
  { id: 'gbp', symbol: 'GBP', sign: '£' },
  { id: 'jpy', symbol: 'JPY', sign: '¥' },
  { id: 'chf', symbol: 'CHF', sign: 'Fr' },
]

const BASE = 'https://api.coingecko.com/api/v3'

export async function fetchMarketData(currency = 'eur') {
  const url = `${BASE}/coins/markets?vs_currency=${currency}&ids=${COINS.join(',')}&order=market_cap_desc&per_page=20&page=1&sparkline=true&price_change_percentage=24h`
  const res = await fetch(url, { next: { revalidate: 60 } })
  if (!res.ok) throw new Error('CoinGecko error')
  return res.json()
}

export async function fetchExchangeRates() {
  const res = await fetch(`${BASE}/exchange_rates`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error('Exchange rates error')
  return res.json()
}

export async function fetchCoinChart(coinId: string, days: number | string) {
  const url = `${BASE}/coins/${coinId}/market_chart?vs_currency=eur&days=${days}`
  const res = await fetch(url, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error(`Chart error ${res.status}`)
  return res.json()
}

export function fmt(n: number, decimals = 2): string {
  if (n === undefined || n === null) return '—'
  if (n >= 1000) return n.toLocaleString('el-GR', { maximumFractionDigits: 0 })
  if (n >= 1) return n.toLocaleString('el-GR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  if (n >= 0.01) return n.toLocaleString('el-GR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })
  return n.toLocaleString('el-GR', { minimumFractionDigits: 8, maximumFractionDigits: 8 })
}

export function fmtMktCap(n: number): string {
  if (!n) return '—'
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`
  return n.toLocaleString('el-GR')
}
