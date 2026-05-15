export const SYMBOL = '€'

export function fmt(price: number): string {
  if (!price && price !== 0) return '—'
  if (price < 0.001) return SYMBOL + price.toFixed(6)
  if (price < 1) return SYMBOL + price.toFixed(4)
  return SYMBOL + price.toLocaleString('el-GR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function fmtMktCap(val: number): string {
  if (!val || isNaN(val)) return '—'
  if (val >= 1e12) return SYMBOL + (val / 1e12).toFixed(2) + 'T'
  if (val >= 1e9) return SYMBOL + (val / 1e9).toFixed(2) + 'B'
  if (val >= 1e6) return SYMBOL + (val / 1e6).toFixed(2) + 'M'
  return SYMBOL + val.toLocaleString('el-GR')
}

export function fmtPct(val: number): string {
  if (val === null || val === undefined || isNaN(val)) return '—'
  const sign = val >= 0 ? '+' : ''
  return sign + val.toFixed(2) + '%'
}
