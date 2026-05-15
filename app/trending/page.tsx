import { getTrending } from '@/lib/api'
import Image from 'next/image'
import { fmtPct } from '@/lib/format'

export const metadata = {
  title: 'Trending — CryptoLive',
  description: 'Trending κρυπτονομίσματα στο CoinGecko',
}

export default async function TrendingPage() {
  const trending = await getTrending()
  const coins = trending?.coins || []
  const nfts = trending?.nfts || []

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Trending</div>
        <h1 className="page-section-title">🔥 Trending Κρυπτονομίσματα</h1>
        <p className="page-section-subtitle">
          Τα πιο δημοφιλή κρυπτονομίσματα στο CoinGecko τις τελευταίες 24 ώρες.
        </p>
      </div>

      <div className="trending-grid">
        {coins.map((c: { item: { id: string; name: string; symbol: string; large: string; thumb: string; market_cap_rank: number; score: number; data?: { price_change_percentage_24h?: { usd: number }; price?: string } } }, idx: number) => {
          const change = c.item.data?.price_change_percentage_24h?.usd ?? 0
          const positive = change >= 0
          return (
            <div key={c.item.id} className="coin-card">
              <div className="card-header">
                <Image
                  src={c.item.large || c.item.thumb}
                  alt={c.item.name}
                  width={40}
                  height={40}
                  className="card-img"
                  unoptimized
                />
                <div className="card-name-group">
                  <div className="card-name">{c.item.name}</div>
                  <div className="card-symbol">{c.item.symbol.toUpperCase()}</div>
                </div>
                <div className="card-rank">#{idx + 1}</div>
              </div>
              {c.item.data?.price && (
                <div className="card-price" style={{ fontSize: 16, marginBottom: 8 }}>
                  {c.item.data.price}
                </div>
              )}
              <div className={`card-change ${positive ? 'pos' : 'neg'}`}>
                {positive ? '▲' : '▼'} {fmtPct(change)}
              </div>
              <div className="card-meta" style={{ marginTop: 8 }}>
                {c.item.market_cap_rank && (
                  <span>Rank #{c.item.market_cap_rank}</span>
                )}
                <span>Score #{c.item.score + 1}</span>
              </div>
            </div>
          )
        })}
      </div>

      {nfts && nfts.length > 0 && (
        <>
          <div style={{ marginTop: 48, marginBottom: 24 }}>
            <h2 className="page-section-title">Trending NFTs</h2>
          </div>
          <div className="trending-grid">
            {nfts.slice(0, 6).map((n: { id: string; name: string; symbol: string; thumb: string; floor_price_in_native_currency?: number; floor_price_24h_percentage_change?: number }) => (
              <div key={n.id} className="coin-card">
                <div className="card-header">
                  <Image
                    src={n.thumb}
                    alt={n.name}
                    width={40}
                    height={40}
                    className="card-img"
                    unoptimized
                  />
                  <div className="card-name-group">
                    <div className="card-name">{n.name}</div>
                    <div className="card-symbol">{n.symbol}</div>
                  </div>
                </div>
                {n.floor_price_in_native_currency && (
                  <div className="card-price" style={{ fontSize: 16 }}>
                    {n.floor_price_in_native_currency} ETH
                  </div>
                )}
                {n.floor_price_24h_percentage_change !== undefined && (
                  <div className={`card-change ${n.floor_price_24h_percentage_change >= 0 ? 'pos' : 'neg'}`}>
                    {n.floor_price_24h_percentage_change >= 0 ? '▲' : '▼'} {fmtPct(n.floor_price_24h_percentage_change)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
