import { getFNG } from '@/lib/api'

export async function GET() {
  const data = await getFNG()
  return Response.json(data)
}
