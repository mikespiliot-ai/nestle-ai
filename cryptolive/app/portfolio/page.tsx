'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import Image from 'next/image'
import { fetchMarketData, fmt, COINS } from '@/lib/api'

interface Coin { id: string; name: string; symbol: string; image: string; current_price: number }
interface Entry { id?: string; coin_id: string; amount: number; buy_price: number }

const LS_KEY = 'cryptolive_portfolio'
function lsLoad(): Entry[] { if (typeof window==='undefined') return []; try { return JSON.parse(localStorage.getItem(LS_KEY)??'[]') } catch { return [] } }
function lsSave(e: Entry[]) { try { localStorage.setItem(LS_KEY, JSON.stringify(e)) } catch {} }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let sb: any = null
async function getSupabase() {
  if (sb) return sb
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !key || url.includes('placeholder')) return null
  const { createClient } = await import('@supabase/supabase-js')
  sb = createClient(url, key); return sb
}

function getUserId() {
  if (typeof window==='undefined') return 'user'
  let id = localStorage.getItem('cryptolive_uid')
  if (!id) { id = 'u_'+Math.random().toString(36).slice(2,10); localStorage.setItem('cryptolive_uid', id) }
  return id
}

export default function PortfolioPage() {
  const [coins, setCoins] = useState<Coin[]>([])
  const [entries, setEntries] = useState<Entry[]>([])
  const [coinSel, setCoinSel] = useState('bitcoin')
  const [amount, setAmount] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [useLs, setUseLs] = useState(false)
  const uid = useRef('user')

  const loadCoins = useCallback(async () => { try { setCoins(await fetchMarketData()) } catch(e) { console.error(e) } }, [])
  const loadEntries = useCallback(async () => {
    uid.current = getUserId()
    const client = await getSupabase()
    if (!client) { setUseLs(true); setEntries(lsLoad()); setLoading(false); return }
    try {
      const { data, error } = await client.from('portfolios').select('*').eq('user_id', uid.current)
      if (error) throw error; setEntries(data??[])
    } catch { setUseLs(true); setEntries(lsLoad()) } finally { setLoading(false) }
  }, [])

  useEffect(() => { loadCoins(); loadEntries() }, [loadCoins, loadEntries])

  const addEntry = async () => {
    if (!amount || parseFloat(amount)<=0) return
    setSaving(true)
    const coin = coins.find(c => c.id===coinSel)
    const entry: Entry = { coin_id: coinSel, amount: parseFloat(amount), buy_price: buyPrice ? parseFloat(buyPrice) : (coin?.current_price??0) }
    try {
      if (useLs) { const u=[...entries,{...entry,id:'l_'+Date.now()}]; setEntries(u); lsSave(u) }
      else {
        const client = await getSupabase(); if (!client) return
        const { data, error } = await client.from('portfolios').insert([{...entry,user_id:uid.current}]).select()
        if (!error && data) setEntries(p=>[...p,data[0]])
      }
      setAmount(''); setBuyPrice('')
    } catch(e) { console.error(e) } finally { setSaving(false) }
  }

  const removeEntry = async (id?: string) => {
    if (!id) return
    if (useLs) { const u=entries.filter(e=>e.id!==id); setEntries(u); lsSave(u) }
    else { const client=await getSupabase(); if (client) await client.from('portfolios').delete().eq('id',id); setEntries(p=>p.filter(e=>e.id!==id)) }
  }

  const totalValue = entries.reduce((s,e) => s+(coins.find(c=>c.id===e.coin_id)?.current_price??0)*e.amount, 0)
  const totalCost = entries.reduce((s,e) => s+e.buy_price*e.amount, 0)
  const pnl = totalValue-totalCost
  const pnlPct = totalCost>0 ? (pnl/totalCost)*100 : 0

  return (
    <main>
      <div className="page-header"><h1>Χαρτοφυλάκιο</h1><p>Παρακολούθηση επενδύσεών σας{useLs ? ' (localStorage)' : ' (Supabase)'}</p></div>
      <div className="section">
        <div className="portfolio-summary">
          {[['Συνολική Αξία',`€${fmt(totalValue)}`,''],['Κόστος',`€${fmt(totalCost)}`,''],['P&L',`${pnl>=0?'+':''}€${fmt(Math.abs(pnl))}`,pnl>=0?'var(--green)':'var(--red)'],['P&L %',`${pnlPct>=0?'+':''}${pnlPct.toFixed(2)}%`,pnlPct>=0?'var(--green)':'var(--red)']].map(([label,value,color])=>(
            <div key={label as string} className="summary-card">
              <div className="summary-label">{label}</div>
              <div className="summary-value" style={color?{color:color as string}:{}}>{value}</div>
            </div>
          ))}
        </div>
        <div className="portfolio-controls">
          <select className="input-field compare-select" value={coinSel} onChange={e=>setCoinSel(e.target.value)}>
            {COINS.map(id=><option key={id} value={id}>{coins.find(c=>c.id===id)?.name??id}</option>)}
          </select>
          <input className="input-field" placeholder="Ποσότητα" type="number" min="0" step="any" value={amount} onChange={e=>setAmount(e.target.value)} />
          <input className="input-field" placeholder="Τιμή αγοράς (€)" type="number" min="0" step="any" value={buyPrice} onChange={e=>setBuyPrice(e.target.value)} />
          <button className="btn btn-primary" onClick={addEntry} disabled={saving}>{saving?'...':'+ Προσθήκη'}</button>
        </div>
        {loading ? <div className="loading"><div className="spinner" /></div> : entries.length===0 ? (
          <div style={{ color: 'var(--muted)', padding: '2rem', textAlign: 'center' }}>Δεν έχετε προσθέσει ακόμα νομίσματα.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="portfolio-table">
              <thead><tr><th>Νόμισμα</th><th>Ποσότητα</th><th>Αγορά</th><th>Τρέχουσα</th><th>Αξία</th><th>P&L</th><th></th></tr></thead>
              <tbody>{entries.map(entry => {
                const coin=coins.find(c=>c.id===entry.coin_id)
                const value=(coin?.current_price??0)*entry.amount, cost=entry.buy_price*entry.amount, p=value-cost
                return (
                  <tr key={entry.id}>
                    <td><div style={{ display:'flex',alignItems:'center',gap:'0.5rem' }}>{coin&&<Image src={coin.image} alt={coin.name} width={24} height={24} unoptimized />}<span>{coin?.name??entry.coin_id}</span></div></td>
                    <td>{entry.amount}</td><td>€{fmt(entry.buy_price)}</td><td>€{fmt(coin?.current_price??0)}</td><td>€{fmt(value)}</td>
                    <td style={{ color:p>=0?'var(--green)':'var(--red)',fontWeight:600 }}>{p>=0?'+':''}€{fmt(Math.abs(p))}</td>
                    <td><button className="btn btn-danger" style={{ padding:'0.3rem 0.6rem',fontSize:'0.75rem' }} onClick={()=>removeEntry(entry.id)}>✕</button></td>
                  </tr>
                )
              })}</tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
