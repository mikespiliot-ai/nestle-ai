import { fmtMktCap, fmtPct } from '@/lib/format'

interface GlobalData {
  data: {
    total_market_cap: Record<string, number>
    total_volume: Record<string, number>
    market_cap_percentage: Record<string, number>
    active_cryptocurrencies: number
    market_cap_change_percentage_24h_usd: number
  }
}

interface StatsBarProps {
  global: GlobalData | null
}

export default function StatsBar({ global: globalData }: StatsBarProps) {
  if (!globalData?.data) {
    return (
      <div className="stats-bar">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="stat-pill skeleton" style={{ width: 160, height: 36 }} />
        ))}
      </div>
    )
  }

  const d = globalData.data
  const totalMcap = d.total_market_cap?.eur || 0
  const totalVol = d.total_volume?.eur || 0
  const btcDom = d.market_cap_percentage?.btc || 0
  const numCoins = d.active_cryptocurrencies || 0
  const mcapChange = d.market_cap_change_percentage_24h_usd || 0

  return (
    <div className="stats-bar">
      <div className="stat-pill">
        <span className="sp-label">Market Cap</span>
        <span className="sp-value">{fmtMktCap(totalMcap)}</span>
        <span className={`sp-change ${mcapChange >= 0 ? 'pos' : 'neg'}`}>
          {fmtPct(mcapChange)}
        </span>
      </div>
      <div className="stat-pill">
        <span className="sp-label">Volume 24h</span>
        <span className="sp-value">{fmtMktCap(totalVol)}</span>
      </div>
      <div className="stat-pill">
        <span className="sp-label">BTC Dominance</span>
        <span className="sp-value">{btcDom.toFixed(1)}%</span>
      </div>
      <div className="stat-pill">
        <span className="sp-label">Coins</span>
        <span className="sp-value">{numCoins.toLocaleString()}</span>
      </div>
    </div>
  )
}
