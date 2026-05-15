import { NextRequest } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const id = searchParams.get('id')
  const days = searchParams.get('days') || '7'

  if (!id) return Response.json({ error: 'Missing id' }, { status: 400 })

  const res = await fetch(
    `https://api.coingecko.com/api/v3/coins/${id}/market_chart?vs_currency=eur&days=${days}`,
    { next: { revalidate: 60 } }
  )

  if (!res.ok) return Response.json({ error: 'Failed to fetch' }, { status: res.status })

  const data = await res.json()
  return Response.json(data)
}
