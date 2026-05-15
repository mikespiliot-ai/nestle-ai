import Image from 'next/image'
import { fmtPct } from '@/lib/format'

interface TrendingCoin {
  item: {
    id: string
    name: string
    symbol: string
    thumb: string
    market_cap_rank: number
    data?: {
      price_change_percentage_24h?: { usd: number }
    }
  }
}

interface TrendingMiniProps {
  coins: TrendingCoin[]
}

export default function TrendingMini({ coins }: TrendingMiniProps) {
  const top7 = coins.slice(0, 7)

  return (
    <div className="trending-panel">
      <div className="panel-title">
        🔥 Trending
      </div>
      <div className="trending-list">
        {top7.map((c, i) => {
          const change = c.item.data?.price_change_percentage_24h?.usd ?? 0
          const positive = change >= 0
          return (
            <div key={c.item.id} className="trending-item">
              <span className="trend-rank">#{i + 1}</span>
              <Image
                src={c.item.thumb}
                alt={c.item.name}
                width={28}
                height={28}
                className="trend-img"
                unoptimized
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="trend-name">{c.item.name}</div>
                <div className="trend-symbol">{c.item.symbol}</div>
              </div>
              <span className={`trend-change ${positive ? 'pos' : 'neg'}`}>
                {fmtPct(change)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
