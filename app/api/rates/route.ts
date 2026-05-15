import { getRates } from '@/lib/api'

export async function GET() {
  const data = await getRates()
  return Response.json(data)
}
