const moeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
})

export const reais = (cents: number | null | undefined) =>
  cents == null ? "" : moeda.format(cents / 100)

export const dias = (n: number) => (n === 1 ? "1 dia" : `${n} dias`)

export const ORIGENS: Record<string, string> = {
  receita: "Receita",
  google_maps: "Google Maps",
  trafego: "Tráfego pago",
}

export const DIAS_ALERTA = 3

export const selectCls =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-input/30"

/** "2026-11-27T13:00:00Z" -> "sex 27/11 10h" (horário de Brasília) */
export function quando(iso: string | null | undefined) {
  if (!iso) return ""
  const d = new Date(iso)
  const dia = d.toLocaleDateString("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    timeZone: "America/Sao_Paulo",
  })
  const hora = d.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  })
  return `${dia.replace(".", "").replace(",", "")} ${hora.replace(":00", "h")}`
}

/** ISO -> valor de <input type="datetime-local"> no horário de Brasília */
export function paraInput(iso: string | null | undefined) {
  if (!iso) return ""
  const d = new Date(iso)
  const p = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d)
  return p.replace(" ", "T")
}

/** valor de <input type="datetime-local"> (Brasília, UTC-3) -> ISO */
export function deInput(v: string) {
  return v ? new Date(`${v}:00-03:00`).toISOString() : null
}

export const cnpjFmt = (c: string | null | undefined) =>
  c?.length === 14
    ? c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5")
    : (c ?? "")

/** "5543999998888@s.whatsapp.net" -> "(43) 99999-8888" */
export function foneFmt(t: string | null | undefined) {
  const d = (t ?? "")
    .split("@")[0]
    .replace(/\D/g, "")
    .replace(/^55(?=\d{10,11}$)/, "")
  if (d.length === 11)
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
  if (d.length === 10)
    return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return d
}
