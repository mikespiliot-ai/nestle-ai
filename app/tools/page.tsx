'use client'
import { useRef, useState, useCallback, useEffect } from 'react'
import { fmt } from '@/lib/format'

type TabId = 'compound' | 'dca' | 'roi' | 'position'

interface Tab {
  id: TabId
  label: string
}

const TABS: Tab[] = [
  { id: 'compound', label: '📈 Σύνθετος Τόκος' },
  { id: 'dca', label: '💰 DCA Calculator' },
  { id: 'roi', label: '📊 ROI Calculator' },
  { id: 'position', label: '⚖️ Position Size' },
]

// Compound Interest
function CompoundTab() {
  const [principal, setPrincipal] = useState('10000')
  const [rate, setRate] = useState('15')
  const [years, setYears] = useState('5')
  const [compound, setCompound] = useState('12')
  const [results, setResults] = useState<{ finalAmount: number; totalInterest: number; multiplier: number } | null>(null)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstRef = useRef<unknown>(null)

  const calculate = useCallback(() => {
    const P = parseFloat(principal) || 0
    const r = parseFloat(rate) / 100
    const n = parseFloat(compound) || 1
    const t = parseFloat(years) || 1
    const A = P * Math.pow(1 + r / n, n * t)
    setResults({
      finalAmount: A,
      totalInterest: A - P,
      multiplier: A / P,
    })

    // Build chart data
    const labels: string[] = []
    const data: number[] = []
    for (let y = 0; y <= t; y++) {
      labels.push(`Έτος ${y}`)
      data.push(P * Math.pow(1 + r / n, n * y))
    }

    const buildChart = async () => {
      const { Chart, registerables } = await import('chart.js')
      Chart.register(...registerables)
      if (chartInstRef.current) (chartInstRef.current as { destroy(): void }).destroy()
      const ctx = chartRef.current?.getContext('2d')
      if (!ctx) return
      const grad = ctx.createLinearGradient(0, 0, 0, 300)
      grad.addColorStop(0, 'rgba(0,212,255,0.4)')
      grad.addColorStop(1, 'rgba(0,212,255,0)')
      chartInstRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: 'Αξία',
            data,
            borderColor: '#00d4ff',
            backgroundColor: grad,
            fill: true,
            borderWidth: 2,
            pointRadius: 4,
            tension: 0.4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (c) => ` ${fmt(c.parsed.y ?? 0)}` } },
          },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 } } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 }, callback: (v) => fmt(Number(v)) }, position: 'right' },
          },
        },
      })
    }
    buildChart()
  }, [principal, rate, years, compound])

  useEffect(() => () => { if (chartInstRef.current) (chartInstRef.current as { destroy(): void }).destroy() }, [])

  return (
    <div className="tool-panel">
      <h2>Σύνθετος Τόκος</h2>
      <p className="tool-panel-desc">Υπολογίστε την ανάπτυξη της επένδυσής σας με σύνθετο τόκο.</p>
      <div className="tool-inputs">
        <div className="tool-field">
          <label className="tool-label">Αρχικό Κεφάλαιο (€)</label>
          <input className="tool-input" type="number" value={principal} onChange={(e) => setPrincipal(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Ετήσια Απόδοση (%)</label>
          <input className="tool-input" type="number" value={rate} onChange={(e) => setRate(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Χρόνια</label>
          <input className="tool-input" type="number" value={years} onChange={(e) => setYears(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Ανατοκισμός/Έτος</label>
          <select className="tool-select" value={compound} onChange={(e) => setCompound(e.target.value)}>
            <option value="1">Ετήσιος</option>
            <option value="4">Τριμηνιαίος</option>
            <option value="12">Μηνιαίος</option>
            <option value="365">Ημερήσιος</option>
          </select>
        </div>
      </div>
      <button className="tool-calc-btn" onClick={calculate}>Υπολόγισε</button>
      {results && (
        <>
          <div className="tool-result-grid">
            <div className="tool-result-card">
              <div className="tool-result-label">Τελική Αξία</div>
              <div className="tool-result-value">{fmt(results.finalAmount)}</div>
            </div>
            <div className="tool-result-card">
              <div className="tool-result-label">Κέρδος</div>
              <div className="tool-result-value" style={{ color: 'var(--green)' }}>{fmt(results.totalInterest)}</div>
            </div>
            <div className="tool-result-card">
              <div className="tool-result-label">Πολλαπλασιαστής</div>
              <div className="tool-result-value">{results.multiplier.toFixed(2)}x</div>
            </div>
          </div>
          <div className="tool-chart-wrap">
            <canvas ref={chartRef} />
          </div>
        </>
      )}
    </div>
  )
}

// DCA Calculator
function DCATab() {
  const [monthly, setMonthly] = useState('200')
  const [months, setMonths] = useState('24')
  const [avgPrice, setAvgPrice] = useState('40000')
  const [currentPrice, setCurrentPrice] = useState('65000')
  const [results, setResults] = useState<{ totalInvested: number; coins: number; currentValue: number; roi: number } | null>(null)
  const chartRef = useRef<HTMLCanvasElement>(null)
  const chartInstRef = useRef<unknown>(null)

  const calculate = useCallback(() => {
    const m = parseFloat(monthly) || 0
    const n = parseFloat(months) || 1
    const ap = parseFloat(avgPrice) || 1
    const cp = parseFloat(currentPrice) || 1
    const totalInvested = m * n
    const coins = totalInvested / ap
    const currentValue = coins * cp
    const roi = ((currentValue - totalInvested) / totalInvested) * 100
    setResults({ totalInvested, coins, currentValue, roi })

    const labels: string[] = []
    const invested: number[] = []
    const value: number[] = []
    for (let i = 1; i <= n; i++) {
      labels.push(`Μ${i}`)
      invested.push(m * i)
      value.push((m * i / ap) * cp)
    }

    const buildChart = async () => {
      const { Chart, registerables } = await import('chart.js')
      Chart.register(...registerables)
      if (chartInstRef.current) (chartInstRef.current as { destroy(): void }).destroy()
      const ctx = chartRef.current?.getContext('2d')
      if (!ctx) return
      chartInstRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            { label: 'Επένδυση', data: invested, borderColor: '#6b7a99', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, borderDash: [5, 5] },
            { label: 'Αξία', data: value, borderColor: '#00d4ff', backgroundColor: 'rgba(0,212,255,0.1)', fill: true, borderWidth: 2, pointRadius: 0, tension: 0.4 },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#8899bb', font: { size: 12 } } },
            tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.parsed.y ?? 0)}` } },
          },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', maxTicksLimit: 8, font: { size: 11 } } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#6b7a99', font: { size: 11 }, callback: (v) => fmt(Number(v)) }, position: 'right' },
          },
        },
      })
    }
    buildChart()
  }, [monthly, months, avgPrice, currentPrice])

  useEffect(() => () => { if (chartInstRef.current) (chartInstRef.current as { destroy(): void }).destroy() }, [])

  return (
    <div className="tool-panel">
      <h2>DCA Calculator</h2>
      <p className="tool-panel-desc">Υπολογίστε την απόδοση της στρατηγικής Dollar Cost Averaging.</p>
      <div className="tool-inputs">
        <div className="tool-field">
          <label className="tool-label">Μηνιαία Επένδυση (€)</label>
          <input className="tool-input" type="number" value={monthly} onChange={(e) => setMonthly(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Μήνες</label>
          <input className="tool-input" type="number" value={months} onChange={(e) => setMonths(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Μέση Τιμή Αγοράς (€)</label>
          <input className="tool-input" type="number" value={avgPrice} onChange={(e) => setAvgPrice(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Τρέχουσα Τιμή (€)</label>
          <input className="tool-input" type="number" value={currentPrice} onChange={(e) => setCurrentPrice(e.target.value)} />
        </div>
      </div>
      <button className="tool-calc-btn" onClick={calculate}>Υπολόγισε</button>
      {results && (
        <>
          <div className="tool-result-grid">
            <div className="tool-result-card">
              <div className="tool-result-label">Επένδυση</div>
              <div className="tool-result-value">{fmt(results.totalInvested)}</div>
            </div>
            <div className="tool-result-card">
              <div className="tool-result-label">Νομίσματα</div>
              <div className="tool-result-value">{results.coins.toFixed(4)}</div>
            </div>
            <div className="tool-result-card">
              <div className="tool-result-label">Τρέχουσα Αξία</div>
              <div className="tool-result-value">{fmt(results.currentValue)}</div>
            </div>
            <div className="tool-result-card">
              <div className="tool-result-label">ROI</div>
              <div className="tool-result-value" style={{ color: results.roi >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {results.roi >= 0 ? '+' : ''}{results.roi.toFixed(2)}%
              </div>
            </div>
          </div>
          <div className="tool-chart-wrap">
            <canvas ref={chartRef} />
          </div>
        </>
      )}
    </div>
  )
}

// ROI Calculator
function ROITab() {
  const [buyPrice, setBuyPrice] = useState('30000')
  const [sellPrice, setSellPrice] = useState('65000')
  const [amount, setAmount] = useState('0.1')
  const [fees, setFees] = useState('0.1')
  const [results, setResults] = useState<{ roi: number; profit: number; netProfit: number; feesTotal: number; multiple: number } | null>(null)

  const calculate = useCallback(() => {
    const bp = parseFloat(buyPrice) || 0
    const sp = parseFloat(sellPrice) || 0
    const amt = parseFloat(amount) || 0
    const fee = parseFloat(fees) / 100

    const invested = bp * amt
    const proceeds = sp * amt
    const feesTotal = (invested + proceeds) * fee
    const profit = proceeds - invested
    const netProfit = profit - feesTotal
    const roi = invested > 0 ? (netProfit / invested) * 100 : 0
    const multiple = invested > 0 ? proceeds / invested : 1

    setResults({ roi, profit: netProfit, netProfit, feesTotal, multiple })
  }, [buyPrice, sellPrice, amount, fees])

  return (
    <div className="tool-panel">
      <h2>ROI Calculator</h2>
      <p className="tool-panel-desc">Υπολογίστε το ROI και το κέρδος της συναλλαγής σας.</p>
      <div className="tool-inputs">
        <div className="tool-field">
          <label className="tool-label">Τιμή Αγοράς (€)</label>
          <input className="tool-input" type="number" value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Τιμή Πώλησης (€)</label>
          <input className="tool-input" type="number" value={sellPrice} onChange={(e) => setSellPrice(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Ποσότητα</label>
          <input className="tool-input" type="number" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Προμήθεια (%)</label>
          <input className="tool-input" type="number" step="0.01" value={fees} onChange={(e) => setFees(e.target.value)} />
        </div>
      </div>
      <button className="tool-calc-btn" onClick={calculate}>Υπολόγισε</button>
      {results && (
        <div className="tool-result-grid">
          <div className="tool-result-card">
            <div className="tool-result-label">ROI</div>
            <div className="tool-result-value" style={{ color: results.roi >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {results.roi >= 0 ? '+' : ''}{results.roi.toFixed(2)}%
            </div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Καθαρό Κέρδος</div>
            <div className="tool-result-value" style={{ color: results.netProfit >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {results.netProfit >= 0 ? '+' : ''}{fmt(results.netProfit)}
            </div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Πολλαπλασιαστής</div>
            <div className="tool-result-value">{results.multiple.toFixed(2)}x</div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Προμήθειες</div>
            <div className="tool-result-value" style={{ color: 'var(--red)' }}>-{fmt(results.feesTotal)}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// Position Size Calculator
function PositionTab() {
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

    const riskAmount = cap * r
    const riskPerCoin = Math.abs(ep - sl)
    const coins = riskPerCoin > 0 ? riskAmount / riskPerCoin : 0
    const positionSize = coins * ep
    const potentialLoss = coins * riskPerCoin
    const potentialProfit = coins * Math.abs(tp - ep)
    const riskReward = potentialLoss > 0 ? potentialProfit / potentialLoss : 0

    setResults({ riskAmount, positionSize, coins, riskReward, potentialProfit, potentialLoss })
  }, [capital, risk, entry, stopLoss, takeProfit])

  return (
    <div className="tool-panel">
      <h2>Position Size Calculator</h2>
      <p className="tool-panel-desc">Υπολογίστε το σωστό μέγεθος θέσης για διαχείριση ρίσκου.</p>
      <div className="tool-inputs">
        <div className="tool-field">
          <label className="tool-label">Κεφάλαιο (€)</label>
          <input className="tool-input" type="number" value={capital} onChange={(e) => setCapital(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Ρίσκο (%)</label>
          <input className="tool-input" type="number" step="0.1" value={risk} onChange={(e) => setRisk(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Τιμή Εισόδου (€)</label>
          <input className="tool-input" type="number" value={entry} onChange={(e) => setEntry(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Stop Loss (€)</label>
          <input className="tool-input" type="number" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} />
        </div>
        <div className="tool-field">
          <label className="tool-label">Take Profit (€)</label>
          <input className="tool-input" type="number" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} />
        </div>
      </div>
      <button className="tool-calc-btn" onClick={calculate}>Υπολόγισε</button>
      {results && (
        <div className="tool-result-grid">
          <div className="tool-result-card">
            <div className="tool-result-label">Μέγεθος Θέσης</div>
            <div className="tool-result-value">{fmt(results.positionSize)}</div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Ποσοτ. Νομίσματος</div>
            <div className="tool-result-value">{results.coins.toFixed(4)}</div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Risk Amount</div>
            <div className="tool-result-value" style={{ color: 'var(--red)' }}>{fmt(results.riskAmount)}</div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Risk/Reward</div>
            <div className="tool-result-value" style={{ color: results.riskReward >= 2 ? 'var(--green)' : 'var(--gold)' }}>
              1:{results.riskReward.toFixed(2)}
            </div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Δυνητικό Κέρδος</div>
            <div className="tool-result-value" style={{ color: 'var(--green)' }}>+{fmt(results.potentialProfit)}</div>
          </div>
          <div className="tool-result-card">
            <div className="tool-result-label">Δυνητική Ζημία</div>
            <div className="tool-result-value" style={{ color: 'var(--red)' }}>-{fmt(results.potentialLoss)}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('compound')

  return (
    <div className="page-content page-enter">
      <div className="hero-section">
        <div className="section-label">Εργαλεία</div>
        <h1 className="page-section-title">Χρηματοοικονομικά Εργαλεία</h1>
        <p className="page-section-subtitle">
          Επαγγελματικοί υπολογιστές για αποτελεσματικό trading και επένδυση.
        </p>
      </div>

      <div className="tools-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tool-tab${activeTab === tab.id ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'compound' && <CompoundTab />}
      {activeTab === 'dca' && <DCATab />}
      {activeTab === 'roi' && <ROITab />}
      {activeTab === 'position' && <PositionTab />}
    </div>
  )
}
