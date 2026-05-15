import { getTrending } from '@/lib/api'

export async function GET() {
  const data = await getTrending()
  return Response.json(data)
}
