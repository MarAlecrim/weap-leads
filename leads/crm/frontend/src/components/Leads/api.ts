import { OpenAPI } from "@/client"

export type FiltrosBusca = {
  oferta: string
  nicho: string
  secundario: boolean
  cidade: string
  bairro: string
  nome: string
  porte: string[]
  anos_min: string
  anos_max: string
  celular: boolean
  email: boolean
  socio: boolean
  nota_min: string
  esconder_disparo: boolean
}

export const filtrosPadrao: FiltrosBusca = {
  oferta: "geral",
  nicho: "",
  secundario: false,
  cidade: "",
  bairro: "",
  nome: "",
  porte: [],
  anos_min: "",
  anos_max: "",
  celular: true,
  email: false,
  socio: false,
  nota_min: "",
  esconder_disparo: false,
}

/** Converte os filtros da tela para os parâmetros da API (sem campos vazios). */
export function paraApi(f: FiltrosBusca) {
  return {
    oferta: f.oferta,
    nicho: f.nicho || undefined,
    secundario: f.secundario || undefined,
    cidade: f.cidade || undefined,
    bairro: f.bairro || undefined,
    nome: f.nome || undefined,
    porte: f.porte.length ? f.porte : undefined,
    anosMin: f.anos_min === "" ? undefined : Number(f.anos_min),
    anosMax: f.anos_max === "" ? undefined : Number(f.anos_max),
    celular: f.celular,
    email: f.email || undefined,
    socio: f.socio || undefined,
    notaMin: f.nota_min === "" ? undefined : Number(f.nota_min),
    esconderDisparo: f.esconder_disparo || undefined,
  }
}

/** Baixa o CSV no formato da planilha do disparo. */
export async function baixarPlanilha(
  f: FiltrosBusca,
  cnpjs: string[],
  pularDisparo: boolean,
) {
  const token = localStorage.getItem("access_token") || ""
  const filtros: Record<string, unknown> = {
    ...f,
    anos_min: f.anos_min === "" ? null : Number(f.anos_min),
    anos_max: f.anos_max === "" ? null : Number(f.anos_max),
    nota_min: f.nota_min === "" ? null : Number(f.nota_min),
  }
  const r = await fetch(`${OpenAPI.BASE}/api/v1/leads/planilha`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ filtros, cnpjs, pular_disparo: pularDisparo }),
  })
  if (!r.ok) throw new Error(`Erro ${r.status} ao gerar a planilha`)
  const nome =
    r.headers.get("Content-Disposition")?.match(/filename="(.+)"/)?.[1] ??
    "leads.csv"
  const blob = await r.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = nome
  a.click()
  URL.revokeObjectURL(url)
}

export function corDaNota(n: number) {
  if (n >= 75) return "bg-emerald-600 text-white"
  if (n >= 50) return "bg-amber-500 text-white"
  return "bg-muted text-muted-foreground"
}
