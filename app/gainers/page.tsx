import { getCoins } from '@/lib/api'
import Image from 'next/image'
import { fmt, fmtPct } from '@/lib/format'

export const metadata = {
  title: 'Κερδισμένοι & Χαμένοι — CryptoLive',
  description: 'Κορυφαίοι κερδισμένοι και χαμένοι της ημέρας',
}

export default async function GainersPage() {
  const coins = await getCoins()

  const sorted = [...coins].sort(
    (a: { price_change_percentage_24h: number }, b: { price_change_percentage_24h: number }) =>
      b.price_change_percentage_24h - a.price_change_percentage_24h
  )

  const gainers = sorted.slice(0, 8)
  const losers = [...sorted].reverse().slice(0, 8)

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Top Movers</div>
        <h1 className="page-section-title">Κερδισμένοι &amp; Χαμένοι</h1>
        <p className="page-section-subtitle">
          Κορυφαίοι κερδισμένοι και χαμένοι της τελευταίας 24ωρης περιόδου.
        </p>
      </div>

      <div className="gainers-grid">
        <div className="gainers-column">
          <h2>
            <span style={{ color: 'var(--green)' }}>▲</span> Κερδισμένοι
          </h2>
          <div className="gainers-list">
            {gainers.map((coin: { id: string; name: string; symbol: string; image: string; current_price: number; price_change_percentage_24h: number; market_cap_rank: number }, idx: number) => (
              <div key={coin.id} className="gainer-item">
                <span className="gainer-rank">#{idx + 1}</span>
                <Image
                  src={coin.image}
                  alt={coin.name}
                  width={32}
                  height={32}
                  style={{ borderRadius: '50%' }}
                  unoptimized
                />
                <div className="gainer-info">
                  <div className="gainer-name">{coin.name}</div>
                  <div className="gainer-symbol">{coin.symbol.toUpperCase()}</div>
                </div>
                <div className="gainer-price">{fmt(coin.current_price)}</div>
                <div className="gainer-change pos">
                  {fmtPct(coin.price_change_percentage_24h)}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="gainers-column">
          <h2>
            <span style={{ color: 'var(--red)' }}>▼</span> Χαμένοι
          </h2>
          <div className="gainers-list">
            {losers.map((coin: { id: string; name: string; symbol: string; image: string; current_price: number; price_change_percentage_24h: number; market_cap_rank: number }, idx: number) => (
              <div key={coin.id} className="gainer-item">
                <span className="gainer-rank">#{idx + 1}</span>
                <Image
                  src={coin.image}
                  alt={coin.name}
                  width={32}
                  height={32}
                  style={{ borderRadius: '50%' }}
                  unoptimized
                />
                <div className="gainer-info">
                  <div className="gainer-name">{coin.name}</div>
                  <div className="gainer-symbol">{coin.symbol.toUpperCase()}</div>
                </div>
                <div className="gainer-price">{fmt(coin.current_price)}</div>
                <div className="gainer-change neg">
                  {fmtPct(coin.price_change_percentage_24h)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
