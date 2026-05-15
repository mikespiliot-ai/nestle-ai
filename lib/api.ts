const COINGECKO_BASE = 'https://api.coingecko.com/api/v3'
const COINS = [
  'bitcoin', 'ethereum', 'tether', 'binancecoin', 'solana', 'ripple',
  'usd-coin', 'staked-ether', 'dogecoin', 'cardano', 'avalanche-2',
  'chainlink', 'tron', 'polkadot', 'shiba-inu', 'matic-network',
  'litecoin', 'bitcoin-cash', 'near', 'uniswap'
]

export async function getCoins() {
  const url = `${COINGECKO_BASE}/coins/markets?vs_currency=eur&ids=${COINS.join(',')}&order=market_cap_desc&per_page=20&page=1&sparkline=true&price_change_percentage=24h`
  try {
    const res = await fetch(url, { next: { revalidate: 30 } })
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

export async function getTrending() {
  try {
    const res = await fetch(`${COINGECKO_BASE}/search/trending`, { next: { revalidate: 60 } })
    if (!res.ok) return { coins: [] }
    return res.json()
  } catch {
    return { coins: [] }
  }
}

export async function getGlobal() {
  try {
    const res = await fetch(`${COINGECKO_BASE}/global`, { next: { revalidate: 60 } })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function getFNG() {
  try {
    const res = await fetch('https://api.alternative.me/fng/', { next: { revalidate: 3600 } })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export async function getRates() {
  try {
    const res = await fetch(`${COINGECKO_BASE}/exchange_rates`, { next: { revalidate: 60 } })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}
