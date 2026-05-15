'use client'
import { useRef, useState, useCallback, useEffect } from 'react'
import { fmt } from '@/lib/format'

type TabId = 'compound' | 'dca' | 'roi' | 'position'

const T = {
  el: {
    tools: 'Εργαλεία',
    title: 'Χρηματοοικονομικά Εργαλεία',
    subtitle: 'Επαγγελματικοί υπολογιστές για αποτελεσματικό trading και επένδυση.',
    tabs: ['📈 Σύνθετος Τόκος', '💰 DCA Calculator', '📊 ROI Calculator', '⚖️ Position Size'],
    compound: {
      title: 'Σύνθετος Τόκος',
      desc: 'Υπολογίστε την ανάπτυξη της επένδυσής σας με σύνθετο τόκο.',
      principal: 'Αρχικό Κεφάλαιο (€)',
      rate: 'Ετήσια Απόδοση (%)',
      years: 'Χρόνια',
      freq: 'Ανατοκισμός/Έτος',
      annual: 'Ετήσιος', quarterly: 'Τριμηνιαίος', monthly: 'Μηνιαίος', daily: 'Ημερήσιος',
      final: 'Τελική Αξία', profit: 'Κέρδος', multiplier: 'Πολλαπλασιαστής',
      yearLabel: (y: number) => `Έτος ${y}`, valueLabel: 'Αξία',
    },
    dca: {
      title: 'DCA Calculator',
      desc: 'Υπολογίστε την απόδοση της στρατηγικής Dollar Cost Averaging.',
      monthly: 'Μηνιαία Επένδυση (€)', months: 'Μήνες',
      avgPrice: 'Μέση Τιμή Αγοράς (€)', currentPrice: 'Τρέχουσα Τιμή (€)',
      invested: 'Επένδυση', coins: 'Νομίσματα', currentValue: 'Τρέχουσα Αξία', roi: 'ROI',
      investedLabel: 'Επένδυση', valueLabel: 'Αξία',
      monthLabel: (i: number) => `Μ${i}`,
    },
    roi: {
      title: 'ROI Calculator',
      desc: 'Υπολογίστε το ROI και το κέρδος της συναλλαγής σας.',
      buyPrice: 'Τιμή Αγοράς (€)', sellPrice: 'Τιμή Πώλησης (€)',
      amount: 'Ποσότητα', fees: 'Προμήθεια (%)',
      roi: 'ROI', netProfit: 'Καθαρό Κέρδος', multiplier: 'Πολλαπλασιαστής', feesTotal: 'Προμήθειες',
    },
    position: {
      title: 'Position Size Calculator',
      desc: 'Υπολογίστε το σωστό μέγεθος θέσης για διαχείριση ρίσκου.',
      capital: 'Κεφάλαιο (€)', risk: 'Ρίσκο (%)', entry: 'Τιμή Εισόδου (€)',
      stopLoss: 'Stop Loss (€)', takeProfit: 'Take Profit (€)',
      posSize: 'Μέγεθος Θέσης', coinAmt: 'Ποσοτ. Νομίσματος',
      riskAmt: 'Risk Amount', rr: 'Risk/Reward',
      potProfit: 'Δυνητικό Κέρδος', potLoss: 'Δυνητική Ζημία',
    },
  },
  en: {
    tools: 'Tools',
    title: 'Financial Tools',
    subtitle: 'Professional calculators for effective trading and investing.',
    tabs: ['📈 Compound Interest', '💰 DCA Calculator', '📊 ROI Calculator', '⚖️ Position Size'],
    compound: {
      title: 'Compound Interest',
      desc: 'Calculate the growth of your investment with compound interest.',
      principal: 'Initial Capital (€)',
      rate: 'Annual Return (%)',
      years: 'Years',
      freq: 'Compounding/Year',
      annual: 'Annual', quarterly: 'Quarterly', monthly: 'Monthly', daily: 'Daily',
      final: 'Final Value', profit: 'Profit', multiplier: 'Multiplier',
      yearLabel: (y: number) => `Year ${y}`, valueLabel: 'Value',
    },
    dca: {
      title: 'DCA Calculator',
      desc: 'Calculate the performance of your Dollar Cost Averaging strategy.',
      monthly: 'Monthly Investment (€)', months: 'Months',
      avgPrice: 'Average Buy Price (€)', currentPrice: 'Current Price (€)',
      invested: 'Invested', coins: 'Coins', currentValue: 'Current Value', roi: 'ROI',
      investedLabel: 'Invested', valueLabel: 'Value',
      monthLabel: (i: number) => `M${i}`,
    },
    roi: {
      title: 'ROI Calculator',
      desc: 'Calculate the ROI and profit of your trade.',
      buyPrice: 'Buy Price (€)', sellPrice: 'Sell Price (€)',
      amount: 'Amount', fees: 'Fee (%)',
      roi: 'ROI', netProfit: 'Net Profit', multiplier: 'Multiplier', feesTotal: 'Fees',
    },
    position: {
      title: 'Position Size Calculator',
      desc: 'Calculate the correct position size for risk management.',
      capital: 'Capital (€)', risk: 'Risk (%)', entry: 'Entry Price (€)',
      stopLoss: 'Stop Loss (€)', takeProfit: 'Take Profit (€)',
      posSize: 'Position Size', coinAmt: 'Coin Amount',
      riskAmt: 'Risk Amount', rr: 'Risk/Reward',
      potProfit: 'Potential Profit', potLoss: 'Potential Loss',
    },
  },
}

function useLang() {
  const [lang, setLang] = useState<'el' | 'en'>('el')
  useEffect(() => {
    const stored = localStorage.getItem('lang') as 'el' | 'en' | null
    if (stored === 'en') setLang('en')
    const handler = () => {
      const v = localStorage.getItem('lang') as 'el' | 'en' | null
      setLang(v === 'en' ? 'en' : 'el')
    }
    window.addEventListener('langchange', handler)
    return () => window.removeEventListener('langchange', handler)
  }, [])
  return lang
}

function destroyChart(ref: React.MutableRefObject<unknown>) {
  if (ref.current) {
    ;(ref.current as { destroy(): void }).destroy()
    ref.current = null
  }
}

function CompoundTab({ t }: { t: typeof T.el }) {
  const c = t.compound
  const [principal, setPrincipal] = useState('10000')
  const [rate, setRate] = useState('15')
  const [years, setYears] = useState('5')
  const [compound, setCompound] = useState('12')
  const [results, setResults] = useState<{ finalAmount: number; totalInterest: number; multiplier: number } | null>(null)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstRef = useRef<unknown>(null)

  const calculate = useCallback(async () => {
    const P = parseFloat(principal) || 0
    const r = parseFloat(rate) / 100
    const n = parseFloat(compound) || 1
    const tt = parseFloat(years) || 1
    if (P <= 0 || tt <= 0) return
    const A = P * Math.pow(1 + r / n, n * tt)
    setResults({ finalAmount: A, totalInterest: A - P, multiplier: A / P })

    const labels: string[] = []
    const data: number[] = []
    for (let y = 0; y <= tt; y++) {
      labels.push(c.yearLabel(y))
      data.push(P * Math.pow(1 + r / n, n * y))
    }

    const { Chart, registerables } = await import('chart.js')
    Chart.register(...registerables)
    destroyChart(chartInstRef)
    const ctx = chartRef.current?.getContext('2d')
    if (!ctx) return
    const grad = ctx.createLinearGradient(0, 0, 0, 300)
    grad.addColorStop(0, 'rgba(0,212,255,0.4)')
    grad.addColorStop(1, 'rgba(0,212,255,0)')
    chartInstRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{ label: c.valueLabel, data, borderColor: '#00d4ff', backgroundColor: grad, fill: true, borderWidth: 2, pointRadius: 4, tension: 0.4 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${fmt(ctx.parsed.y ?? 0)}` } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 } } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 }, callback: (v) => fmt(Number(v)) }, position: 'right' },
        },
      },
    })
  }, [principal, rate, years, compound, c])

  useEffect(() => { calculate() }, [calculate])
  useEffect(() => () => destroyChart(chartInstRef), [])

  return (
    <div className="tool-panel">
      <h2>{c.title}</h2>
      <p className="tool-panel-desc">{c.desc}</p>
      <div className="tool-inputs">
        <div className="tool-field"><label className="tool-label">{c.principal}</label>
          <input className="tool-input" type="number" value={principal} onChange={(e) => setPrincipal(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.rate}</label>
          <input className="tool-input" type="number" value={rate} onChange={(e) => setRate(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.years}</label>
          <input className="tool-input" type="number" value={years} onChange={(e) => setYears(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.freq}</label>
          <select className="tool-select" value={compound} onChange={(e) => setCompound(e.target.value)}>
            <option value="1">{c.annual}</option>
            <option value="4">{c.quarterly}</option>
            <option value="12">{c.monthly}</option>
            <option value="365">{c.daily}</option>
          </select></div>
      </div>
      {results && (
        <>
          <div className="tool-result-grid">
            <div className="tool-result-card"><div className="tool-result-label">{c.final}</div><div className="tool-result-value">{fmt(results.finalAmount)}</div></div>
            <div className="tool-result-card"><div className="tool-result-label">{c.profit}</div><div className="tool-result-value" style={{ color: 'var(--green)' }}>{fmt(results.totalInterest)}</div></div>
            <div className="tool-result-card"><div className="tool-result-label">{c.multiplier}</div><div className="tool-result-value">{results.multiplier.toFixed(2)}x</div></div>
          </div>
          <div className="tool-chart-wrap"><canvas ref={chartRef} /></div>
        </>
      )}
    </div>
  )
}

function DCATab({ t }: { t: typeof T.el }) {
  const c = t.dca
  const [monthly, setMonthly] = useState('200')
  const [months, setMonths] = useState('24')
  const [avgPrice, setAvgPrice] = useState('40000')
  const [currentPrice, setCurrentPrice] = useState('65000')
  const [results, setResults] = useState<{ totalInvested: number; coins: number; currentValue: number; roi: number } | null>(null)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstRef = useRef<unknown>(null)

  const calculate = useCallback(async () => {
    const m = parseFloat(monthly) || 0
    const n = parseFloat(months) || 1
    const ap = parseFloat(avgPrice) || 1
    const cp = parseFloat(currentPrice) || 1
    if (m <= 0 || n <= 0) return
    const totalInvested = m * n
    const coins = totalInvested / ap
    const currentValue = coins * cp
    const roi = ((currentValue - totalInvested) / totalInvested) * 100
    setResults({ totalInvested, coins, currentValue, roi })

    const labels: string[] = []
    const invested: number[] = []
    const value: number[] = []
    for (let i = 1; i <= n; i++) {
      labels.push(c.monthLabel(i))
      invested.push(m * i)
      value.push((m * i / ap) * cp)
    }

    const { Chart, registerables } = await import('chart.js')
    Chart.register(...registerables)
    destroyChart(chartInstRef)
    const ctx = chartRef.current?.getContext('2d')
    if (!ctx) return
    chartInstRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: c.investedLabel, data: invested, borderColor: '#6b7a99', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, borderDash: [5, 5] },
          { label: c.valueLabel, data: value, borderColor: '#00d4ff', backgroundColor: 'rgba(0,212,255,0.1)', fill: true, borderWidth: 2, pointRadius: 0, tension: 0.4 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#8899bb', font: { size: 12 } } },
          tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${fmt(ctx.parsed.y ?? 0)}` } },
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', maxTicksLimit: 8, font: { size: 11 } } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 }, callback: (v) => fmt(Number(v)) }, position: 'right' },
        },
      },
    })
  }, [monthly, months, avgPrice, currentPrice, c])

  useEffect(() => { calculate() }, [calculate])
  useEffect(() => () => destroyChart(chartInstRef), [])

  return (
    <div className="tool-panel">
      <h2>{c.title}</h2>
      <p className="tool-panel-desc">{c.desc}</p>
      <div className="tool-inputs">
        <div className="tool-field"><label className="tool-label">{c.monthly}</label>
          <input className="tool-input" type="number" value={monthly} onChange={(e) => setMonthly(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.months}</label>
          <input className="tool-input" type="number" value={months} onChange={(e) => setMonths(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.avgPrice}</label>
          <input className="tool-input" type="number" value={avgPrice} onChange={(e) => setAvgPrice(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.currentPrice}</label>
          <input className="tool-input" type="number" value={currentPrice} onChange={(e) => setCurrentPrice(e.target.value)} /></div>
      </div>
      {results && (
        <>
          <div className="tool-result-grid">
            <div className="tool-result-card"><div className="tool-result-label">{c.invested}</div><div className="tool-result-value">{fmt(results.totalInvested)}</div></div>
            <div className="tool-result-card"><div className="tool-result-label">{c.coins}</div><div className="tool-result-value">{results.coins.toFixed(4)}</div></div>
            <div className="tool-result-card"><div className="tool-result-label">{c.currentValue}</div><div className="tool-result-value">{fmt(results.currentValue)}</div></div>
            <div className="tool-result-card"><div className="tool-result-label">{c.roi}</div>
              <div className="tool-result-value" style={{ color: results.roi >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {results.roi >= 0 ? '+' : ''}{results.roi.toFixed(2)}%
              </div></div>
          </div>
          <div className="tool-chart-wrap"><canvas ref={chartRef} /></div>
        </>
      )}
    </div>
  )
}

function ROITab({ t }: { t: typeof T.el }) {
  const c = t.roi
  const [buyPrice, setBuyPrice] = useState('30000')
  const [sellPrice, setSellPrice] = useState('65000')
  const [amount, setAmount] = useState('0.1')
  const [fees, setFees] = useState('0.1')
  const [results, setResults] = useState<{ roi: number; netProfit: number; feesTotal: number; multiple: number } | null>(null)

  const calculate = useCallback(() => {
    const bp = parseFloat(buyPrice) || 0
    const sp = parseFloat(sellPrice) || 0
    const amt = parseFloat(amount) || 0
    const fee = parseFloat(fees) / 100
    if (bp <= 0 || amt <= 0) return
    const invested = bp * amt
    const proceeds = sp * amt
    const feesTotal = (invested + proceeds) * fee
    const profit = proceeds - invested
    const netProfit = profit - feesTotal
    const roi = invested > 0 ? (netProfit / invested) * 100 : 0
    const multiple = invested > 0 ? proceeds / invested : 1
    setResults({ roi, netProfit, feesTotal, multiple })
  }, [buyPrice, sellPrice, amount, fees])

  useEffect(() => { calculate() }, [calculate])

  return (
    <div className="tool-panel">
      <h2>{c.title}</h2>
      <p className="tool-panel-desc">{c.desc}</p>
      <div className="tool-inputs">
        <div className="tool-field"><label className="tool-label">{c.buyPrice}</label>
          <input className="tool-input" type="number" value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.sellPrice}</label>
          <input className="tool-input" type="number" value={sellPrice} onChange={(e) => setSellPrice(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.amount}</label>
          <input className="tool-input" type="number" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.fees}</label>
          <input className="tool-input" type="number" step="0.01" value={fees} onChange={(e) => setFees(e.target.value)} /></div>
      </div>
      {results && (
        <div className="tool-result-grid">
          <div className="tool-result-card"><div className="tool-result-label">{c.roi}</div>
            <div className="tool-result-value" style={{ color: results.roi >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {results.roi >= 0 ? '+' : ''}{results.roi.toFixed(2)}%
            </div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.netProfit}</div>
            <div className="tool-result-value" style={{ color: results.netProfit >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {results.netProfit >= 0 ? '+' : ''}{fmt(results.netProfit)}
            </div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.multiplier}</div><div className="tool-result-value">{results.multiple.toFixed(2)}x</div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.feesTotal}</div><div className="tool-result-value" style={{ color: 'var(--red)' }}>-{fmt(results.feesTotal)}</div></div>
        </div>
      )}
    </div>
  )
}

function PositionTab({ t }: { t: typeof T.el }) {
  const c = t.position
  const [capital, setCapital] = useState('10000')
  const [risk, setRisk] = useState('2')
  const [entry, setEntry] = useState('65000')
  const [stopLoss, setStopLoss] = useState('60000')
  const [takeProfit, setTakeProfit] = useState('75000')
  const [results, setResults] = useState<{
    riskAmount: number; positionSize: number; coins: number;
    riskReward: number; potentialProfit: number; potentialLoss: number
  } | null>(null)

  const calculate = useCallback(() => {
    const cap = parseFloat(capital) || 0
    const r = parseFloat(risk) / 100
    const ep = parseFloat(entry) || 1
    const sl = parseFloat(stopLoss) || 1
    const tp = parseFloat(takeProfit) || 1
    if (cap <= 0 || ep <= 0) return
    const riskAmount = cap * r
    const riskPerCoin = Math.abs(ep - sl)
    const coins = riskPerCoin > 0 ? riskAmount / riskPerCoin : 0
    const positionSize = coins * ep
    const potentialLoss = coins * riskPerCoin
    const potentialProfit = coins * Math.abs(tp - ep)
    const riskReward = potentialLoss > 0 ? potentialProfit / potentialLoss : 0
    setResults({ riskAmount, positionSize, coins, riskReward, potentialProfit, potentialLoss })
  }, [capital, risk, entry, stopLoss, takeProfit])

  useEffect(() => { calculate() }, [calculate])

  return (
    <div className="tool-panel">
      <h2>{c.title}</h2>
      <p className="tool-panel-desc">{c.desc}</p>
      <div className="tool-inputs">
        <div className="tool-field"><label className="tool-label">{c.capital}</label>
          <input className="tool-input" type="number" value={capital} onChange={(e) => setCapital(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.risk}</label>
          <input className="tool-input" type="number" step="0.1" value={risk} onChange={(e) => setRisk(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.entry}</label>
          <input className="tool-input" type="number" value={entry} onChange={(e) => setEntry(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.stopLoss}</label>
          <input className="tool-input" type="number" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} /></div>
        <div className="tool-field"><label className="tool-label">{c.takeProfit}</label>
          <input className="tool-input" type="number" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} /></div>
      </div>
      {results && (
        <div className="tool-result-grid">
          <div className="tool-result-card"><div className="tool-result-label">{c.posSize}</div><div className="tool-result-value">{fmt(results.positionSize)}</div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.coinAmt}</div><div className="tool-result-value">{results.coins.toFixed(4)}</div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.riskAmt}</div><div className="tool-result-value" style={{ color: 'var(--red)' }}>{fmt(results.riskAmount)}</div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.rr}</div>
            <div className="tool-result-value" style={{ color: results.riskReward >= 2 ? 'var(--green)' : 'var(--gold)' }}>
              1:{results.riskReward.toFixed(2)}
            </div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.potProfit}</div><div className="tool-result-value" style={{ color: 'var(--green)' }}>+{fmt(results.potentialProfit)}</div></div>
          <div className="tool-result-card"><div className="tool-result-label">{c.potLoss}</div><div className="tool-result-value" style={{ color: 'var(--red)' }}>-{fmt(results.potentialLoss)}</div></div>
        </div>
      )}
    </div>
  )
}

const TAB_IDS: TabId[] = ['compound', 'dca', 'roi', 'position']

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('compound')
  const lang = useLang()
  const t = T[lang]

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">{t.tools}</div>
        <h1 className="page-section-title">{t.title}</h1>
        <p className="page-section-subtitle">{t.subtitle}</p>
      </div>

      <div className="tools-tabs">
        {TAB_IDS.map((id, i) => (
          <button
            key={id}
            className={`tool-tab${activeTab === id ? ' active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            {t.tabs[i]}
          </button>
        ))}
      </div>

      {activeTab === 'compound' && <CompoundTab t={t} />}
      {activeTab === 'dca' && <DCATab t={t} />}
      {activeTab === 'roi' && <ROITab t={t} />}
      {activeTab === 'position' && <PositionTab t={t} />}
    </div>
  )
}
