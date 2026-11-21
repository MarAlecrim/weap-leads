import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"

import { type Dia, type Painel as PainelDados, PainelService } from "@/client"
import { dias, quando, reais } from "@/components/Funil/util"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/")({
  component: Painel,
  head: () => ({ meta: [{ title: "Painel - Weap" }] }),
})

const numero = new Intl.NumberFormat("pt-BR")
const pct = (a: number, b: number) =>
  b ? `${Math.round((a / b) * 100)}%` : "—"

function Painel() {
  const { data: p, isLoading } = useQuery({
    queryKey: ["painel"],
    queryFn: () => PainelService.painel(),
    refetchInterval: 60_000,
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Painel</h1>
        <p className="text-muted-foreground">
          Como está o disparo e o funil. Atualiza sozinho a cada minuto.
        </p>
      </div>

      {isLoading || !p ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <>
          <Numeros p={p} />
          <div className="grid gap-6 lg:grid-cols-2">
            <Bloco titulo="Funil por etapa" link="/funil">
              <Etapas p={p} />
            </Bloco>
            <Bloco titulo="Disparo nos últimos 14 dias">
              {p.por_dia ? (
                <PorDia dias={p.por_dia} />
              ) : (
                <p className="text-muted-foreground text-sm">
                  O banco do agente não respondeu agora.
                </p>
              )}
            </Bloco>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Bloco titulo="Por número">
              <PorNumero p={p} />
            </Bloco>
            <Bloco
              titulo={`Precisa de atenção (${p.atencao_total})`}
              link="/funil"
            >
              <Atencao p={p} />
            </Bloco>
          </div>
        </>
      )}
    </div>
  )
}

function Bloco({
  titulo,
  link,
  children,
}: {
  titulo: string
  link?: "/funil"
  children: React.ReactNode
}) {
  return (
    <section className="rounded-lg border p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-semibold">{titulo}</h2>
        {link && (
          <Link to={link} className="text-primary text-sm hover:underline">
            Abrir o funil
          </Link>
        )}
      </div>
      {children}
    </section>
  )
}

function Numero({
  rotulo,
  valor,
  extra,
}: {
  rotulo: string
  valor: string
  extra?: string
}) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-muted-foreground text-sm">{rotulo}</div>
      <div className="mt-1 font-semibold text-2xl tabular-nums">{valor}</div>
      {extra && (
        <div className="mt-0.5 text-muted-foreground text-xs">{extra}</div>
      )}
    </div>
  )
}

function Numeros({ p }: { p: PainelDados }) {
  const n = (v: number | null | undefined) =>
    v == null ? "—" : numero.format(v)
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Numero
        rotulo="Na fila do disparo"
        valor={n(p.na_fila)}
        extra={
          p.enviados_hoje != null
            ? `${n(p.enviados_hoje)} receberam a 1ª mensagem hoje`
            : undefined
        }
      />
      <Numero rotulo="Contatados" valor={n(p.contatados)} extra="no total" />
      <Numero
        rotulo="Responderam"
        valor={n(p.responderam)}
        extra={`${pct(p.responderam, p.contatados)} dos contatados`}
      />
      <Numero
        rotulo="Interessados e reuniões"
        valor={n(p.interessados + p.reunioes)}
        extra={`${n(p.reunioes)} com reunião marcada`}
      />
      <Numero
        rotulo="Propostas em aberto"
        valor={n(p.abertos)}
        extra={p.abertos_valor_cents ? reais(p.abertos_valor_cents) : undefined}
      />
      <Numero
        rotulo="Ganhos"
        valor={n(p.ganhos)}
        extra={p.ganhos_valor_cents ? reais(p.ganhos_valor_cents) : undefined}
      />
      <Numero rotulo="Clientes atuais" valor={n(p.clientes_atuais)} />
      <Numero
        rotulo="Precisam de atenção"
        valor={n(p.atencao_total)}
        extra="sem resposta, ação vencida ou com pessoa"
      />
    </div>
  )
}

function Etapas({ p }: { p: PainelDados }) {
  const max = Math.max(1, ...p.etapas.map((e) => e.total))
  return (
    <ul className="grid gap-1.5">
      {p.etapas.map((e) => (
        <li
          key={e.etapa}
          className="grid grid-cols-[8.5rem_1fr_3.5rem] items-center gap-2 text-sm"
          title={`${e.nome}: ${numero.format(e.total)}${e.valor_cents ? ` · ${reais(e.valor_cents)}` : ""}`}
        >
          <span className="truncate">{e.nome}</span>
          <span className="h-4 rounded-r-sm bg-muted">
            <span
              className="block h-full rounded-r-[4px] bg-primary"
              style={{ width: `${(e.total / max) * 100}%` }}
            />
          </span>
          <span className="text-right tabular-nums">
            {numero.format(e.total)}
          </span>
        </li>
      ))}
    </ul>
  )
}

const diaCurto = (iso: string) => {
  const [, m, d] = iso.split("-")
  return `${d}/${m}`
}

function PorDia({ dias: serie }: { dias: Dia[] }) {
  const [foco, setFoco] = useState<number | null>(null)
  const max = Math.max(
    1,
    ...serie.map((d) => Math.max(d.enviados, d.respostas)),
  )
  const altura = 160
  const total = serie.reduce(
    (a, d) => ({ e: a.e + d.enviados, r: a.r + d.respostas }),
    { e: 0, r: 0 },
  )
  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap gap-4 text-sm">
        <Legenda cor="var(--serie-envio)" texto="1ª mensagem enviada" />
        <Legenda cor="var(--serie-resposta)" texto="Respostas" />
        <span className="ml-auto text-muted-foreground">
          {numero.format(total.e)} enviados · {numero.format(total.r)} respostas
        </span>
      </div>
      <div className="relative">
        <ul
          aria-label="Envios e respostas por dia"
          className="grid items-end gap-1 border-b"
          style={{
            gridTemplateColumns: `repeat(${serie.length}, 1fr)`,
            height: altura,
          }}
          onMouseLeave={() => setFoco(null)}
        >
          {serie.map((d, i) => (
            <li
              key={d.dia}
              aria-label={`${d.dia}: ${d.enviados} enviados, ${d.respostas} respostas`}
              className={cn(
                "flex h-full items-end justify-center gap-[2px] rounded-sm",
                foco === i && "bg-muted",
              )}
              onMouseEnter={() => setFoco(i)}
            >
              <span
                className="w-[38%] rounded-t-[4px]"
                style={{
                  height: `${(d.enviados / max) * 100}%`,
                  background: "var(--serie-envio)",
                  minHeight: d.enviados ? 2 : 0,
                }}
              />
              <span
                className="w-[38%] rounded-t-[4px]"
                style={{
                  height: `${(d.respostas / max) * 100}%`,
                  background: "var(--serie-resposta)",
                  minHeight: d.respostas ? 2 : 0,
                }}
              />
            </li>
          ))}
        </ul>
        {foco != null && (
          <div
            className="pointer-events-none absolute top-0 z-10 rounded-md border bg-popover px-3 py-2 text-popover-foreground text-xs shadow-md"
            style={{
              left: `${((foco + 0.5) / serie.length) * 100}%`,
              transform:
                foco > serie.length / 2
                  ? "translateX(calc(-100% - 8px))"
                  : "translateX(8px)",
            }}
          >
            <div className="font-semibold">{diaCurto(serie[foco].dia)}</div>
            <div>
              {numero.format(serie[foco].enviados)} receberam a 1ª mensagem
            </div>
            <div>{numero.format(serie[foco].respostas)} responderam</div>
          </div>
        )}
        <div
          className="mt-1 grid text-center text-muted-foreground text-xs"
          style={{ gridTemplateColumns: `repeat(${serie.length}, 1fr)` }}
        >
          {serie.map((d, i) => (
            <span key={d.dia}>
              {i % 2 === serie.length % 2 ? "" : diaCurto(d.dia)}
            </span>
          ))}
        </div>
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">
          Ver em tabela
        </summary>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Dia</TableHead>
              <TableHead className="text-right">1ª mensagem</TableHead>
              <TableHead className="text-right">Respostas</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[...serie].reverse().map((d) => (
              <TableRow key={d.dia}>
                <TableCell>{diaCurto(d.dia)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {numero.format(d.enviados)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {numero.format(d.respostas)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </details>
    </div>
  )
}

function Legenda({ cor, texto }: { cor: string; texto: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-3 rounded-sm" style={{ background: cor }} />
      {texto}
    </span>
  )
}

function PorNumero({ p }: { p: PainelDados }) {
  if (!p.por_numero.length)
    return <p className="text-muted-foreground text-sm">Sem contatos ainda.</p>
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Número</TableHead>
          <TableHead className="text-right">Contatos</TableHead>
          <TableHead className="text-right">Respostas</TableHead>
          <TableHead className="text-right">Taxa</TableHead>
          <TableHead className="text-right">Interesse</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {p.por_numero.map((x) => (
          <TableRow key={x.instancia}>
            <TableCell title={x.instancia}>{x.numero}</TableCell>
            <TableCell className="text-right tabular-nums">
              {numero.format(x.contatados)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {numero.format(x.responderam)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {pct(x.responderam, x.contatados)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {numero.format(x.interessados)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Atencao({ p }: { p: PainelDados }) {
  if (!p.atencao.length)
    return (
      <p className="text-muted-foreground text-sm">Nada parado. Tudo em dia.</p>
    )
  const agora = new Date()
  return (
    <ul className="grid gap-2">
      {p.atencao.map((c) => {
        const vencida = c.proxima_acao_em && new Date(c.proxima_acao_em) < agora
        const motivo = vencida
          ? `${c.proxima_acao || "Ação"} vencida (${quando(c.proxima_acao_em)})`
          : c.ia_pausada
            ? "Com pessoa, IA pausada"
            : `Sem resposta há ${dias(c.dias_sem_resposta ?? 0)}`
        return (
          <li
            key={c.id}
            className="flex items-baseline justify-between gap-3 rounded-md border px-3 py-2 text-sm"
          >
            <span className="min-w-0">
              <span className="block truncate font-medium">{c.nome}</span>
              <span className="text-muted-foreground text-xs">
                {[c.responsavel, c.numero].filter(Boolean).join(" · ")}
              </span>
            </span>
            <span
              className={cn(
                "shrink-0 text-xs font-semibold",
                vencida || !c.ia_pausada
                  ? "text-destructive"
                  : "text-amber-600 dark:text-amber-400",
              )}
            >
              {motivo}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
