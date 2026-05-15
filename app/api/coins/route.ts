import { getCoins } from '@/lib/api'

export async function GET() {
  const data = await getCoins()
  return Response.json(data)
}
