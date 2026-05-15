import { getCoins, getFNG, getTrending, getGlobal } from '@/lib/api'
import HeroGrid from '@/components/HeroGrid'
import StatsBar from '@/components/StatsBar'
import FNGGauge from '@/components/FNGGauge'
import TrendingMini from '@/components/TrendingMini'

export default async function Home() {
  const [coins, fng, trending, globalData] = await Promise.all([
    getCoins(),
    getFNG(),
    getTrending(),
    getGlobal(),
  ])

  const fngValue = fng?.data?.[0]?.value ? parseInt(fng.data[0].value) : 50
  const fngClass = fng?.data?.[0]?.value_classification || 'Neutral'
  const trendingCoins = trending?.coins || []

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Ζωντανές Τιμές</div>
        <h1 className="hero-title">
          Αγορά <span className="gradient-text">Κρυπτονομισμάτων</span>
        </h1>
        <p className="hero-subtitle">
          Παρακολουθήστε τις κορυφαίες κρυπτοαγορές σε πραγματικό χρόνο με δεδομένα από CoinGecko και Binance.
        </p>
      </div>

      <StatsBar global={globalData} />

      <HeroGrid coins={coins} />

      <div className="bottom-grid">
        <FNGGauge value={fngValue} classification={fngClass} />
        <TrendingMini coins={trendingCoins} />
      </div>
    </div>
  )
}
