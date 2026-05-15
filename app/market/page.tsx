import { getCoins } from '@/lib/api'
import MarketGrid from '@/components/MarketGrid'

export const metadata = {
  title: 'Αγορά — CryptoLive',
  description: 'Πλήρης αγορά κρυπτονομισμάτων με αναζήτηση και ταξινόμηση',
}

export default async function MarketPage() {
  const coins = await getCoins()

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Αγορά</div>
        <h1 className="page-section-title">Κρυπτοαγορά</h1>
        <p className="page-section-subtitle">
          20 κορυφαία κρυπτονομίσματα με ζωντανά δεδομένα, αναζήτηση και ταξινόμηση.
        </p>
      </div>

      <MarketGrid coins={coins} />
    </div>
  )
}
