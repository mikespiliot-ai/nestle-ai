import { NextRequest } from 'next/server'
import { Resend } from 'resend'
import { createClient } from '@supabase/supabase-js'

export const dynamic = 'force-dynamic'

const supabaseAdmin = createClient(
  'https://nuvemdfqriecjsemepaf.supabase.co',
  process.env.SUPABASE_SERVICE_ROLE_KEY || ''
)

const resend = new Resend(process.env.RESEND_API_KEY)

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Get all users with notifications enabled
  const { data: notifUsers, error: notifError } = await supabaseAdmin
    .from('notifications')
    .select('user_id, email')
    .eq('enabled', true)

  if (notifError || !notifUsers || notifUsers.length === 0) {
    return Response.json({ sent: 0 })
  }

  // Fetch current coin prices
  let prices: Record<string, number> = {}
  try {
    const res = await fetch(
      'https://api.coingecko.com/api/v3/coins/markets?vs_currency=eur&order=market_cap_desc&per_page=100&page=1'
    )
    if (res.ok) {
      const coins = await res.json()
      for (const c of coins) prices[c.id] = c.current_price
    }
  } catch {}

  let sent = 0

  for (const { user_id, email } of notifUsers) {
    const { data: holdings } = await supabaseAdmin
      .from('portfolios')
      .select('*')
      .eq('user_id', user_id)

    if (!holdings || holdings.length === 0) continue

    let totalValue = 0
    let totalCost = 0
    const rows = holdings.map((h: { coin_id: string; amount: number; buy_price: number }) => {
      const price = prices[h.coin_id] ?? 0
      const value = h.amount * price
      const cost = h.amount * h.buy_price
      const pnl = value - cost
      const pnlPct = cost > 0 ? ((pnl / cost) * 100).toFixed(2) : '0'
      totalValue += value
      totalCost += cost
      return `
        <tr style="border-bottom:1px solid #1a2340">
          <td style="padding:10px 8px;color:#f0f4ff">${h.coin_id.charAt(0).toUpperCase() + h.coin_id.slice(1)}</td>
          <td style="padding:10px 8px;color:#8899bb;text-align:right">${h.amount}</td>
          <td style="padding:10px 8px;text-align:right;color:#f0f4ff">€${value.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          <td style="padding:10px 8px;text-align:right;color:${pnl >= 0 ? '#00e676' : '#ff3d57'}">${pnl >= 0 ? '+' : ''}€${pnl.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${pnl >= 0 ? '+' : ''}${pnlPct}%)</td>
        </tr>`
    }).join('')

    const totalPnl = totalValue - totalCost
    const totalPnlPct = totalCost > 0 ? ((totalPnl / totalCost) * 100).toFixed(2) : '0'

    const html = `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="background:#04070f;font-family:Inter,sans-serif;margin:0;padding:0">
  <div style="max-width:600px;margin:0 auto;padding:32px 16px">
    <div style="text-align:center;margin-bottom:32px">
      <div style="font-size:28px;font-weight:800;color:#00d4ff">₿ CryptoLive</div>
      <div style="color:#6b7a99;font-size:13px;margin-top:6px">Ημερήσια Ενημέρωση Χαρτοφυλακίου</div>
    </div>

    <div style="background:#070d1a;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:24px;margin-bottom:20px;text-align:center">
      <div style="color:#6b7a99;font-size:12px;margin-bottom:8px">ΣΥΝΟΛΙΚΗ ΑΞΙΑ</div>
      <div style="font-size:36px;font-weight:800;color:#f0f4ff">€${totalValue.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
      <div style="margin-top:8px;font-size:18px;font-weight:700;color:${totalPnl >= 0 ? '#00e676' : '#ff3d57'}">
        ${totalPnl >= 0 ? '▲' : '▼'} €${Math.abs(totalPnl).toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${totalPnl >= 0 ? '+' : ''}${totalPnlPct}%)
      </div>
      <div style="color:#6b7a99;font-size:12px;margin-top:4px">Κόστος: €${totalCost.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
    </div>

    <div style="background:#070d1a;border:1px solid rgba(255,255,255,0.08);border-radius:16px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="background:rgba(255,255,255,0.04)">
            <th style="padding:10px 8px;text-align:left;color:#6b7a99;font-size:12px;font-weight:600">ΝΟΜΙΣΜΑ</th>
            <th style="padding:10px 8px;text-align:right;color:#6b7a99;font-size:12px;font-weight:600">ΠΟΣΟΤΗΤΑ</th>
            <th style="padding:10px 8px;text-align:right;color:#6b7a99;font-size:12px;font-weight:600">ΑΞΙΑ</th>
            <th style="padding:10px 8px;text-align:right;color:#6b7a99;font-size:12px;font-weight:600">P&L</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>

    <div style="text-align:center;margin-top:24px">
      <a href="https://nestle-ai.vercel.app/portfolio" style="display:inline-block;background:#00d4ff;color:#04070f;font-weight:700;padding:12px 28px;border-radius:10px;text-decoration:none;font-size:14px">
        Δες το Χαρτοφυλάκιό σου →
      </a>
    </div>

    <div style="text-align:center;margin-top:24px;color:#6b7a99;font-size:11px">
      © 2025 CryptoLive · <a href="https://nestle-ai.vercel.app/portfolio" style="color:#6b7a99">Απενεργοποίηση ειδοποιήσεων</a>
    </div>
  </div>
</body>
</html>`

    try {
      await resend.emails.send({
        from: 'CryptoLive <notifications@byluma.co>',
        to: email,
        subject: `Χαρτοφυλάκιο: €${totalValue.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${totalPnl >= 0 ? '▲' : '▼'} ${totalPnl >= 0 ? '+' : ''}${totalPnlPct}%`,
        html,
      })
      sent++
    } catch {}
  }

  return Response.json({ sent })
}
