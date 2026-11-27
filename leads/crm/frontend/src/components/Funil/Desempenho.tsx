import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useState } from "react"

import {
  type Contagem,
  type DiaDesempenho,
  FunilService,
  type NumeroDesempenho,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { quando, selectCls } from "./util"

const num = new Intl.NumberFormat("pt-BR")
const pct = (a: number, b: number) =>
  b ? `${Math.round((a / b) * 100)}%` : "–"

const PERIODOS = [7, 14, 30]

/** "2026-11-27" -> "sex 27/11" */
function diaFmt(iso: string) {
  const d = new Date(`${iso}T12:00:00-03:00`)
  return d
    .toLocaleDateString("pt-BR", {
      weekday: "short",
      day: "2-digit",
      month: "2-digit",
      timeZone: "America/Sao_Paulo",
    })
    .replace(".", "")
    .replace(",", "")
}

type Props = {
  instancia: string
  onEscolher: (instancia: string) => void
}

/** Quanto cada número de WhatsApp abordou, mandou e recebeu de resposta, por dia. */
export function Desempenho({ instancia, onEscolher }: Props) {
  const [aberto, setAberto] = useState(true)
  const [dias, setDias] = useState(14)
  const { data, isLoading } = useQuery({
    queryKey: ["funil-desempenho", instancia, dias],
    queryFn: () =>
      FunilService.desempenho({ instancia: instancia || undefined, dias }),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
    enabled: aberto,
  })

  return (
    <section className="rounded-lg border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">
          Desempenho {instancia ? "do número" : "por número"}
        </h2>
        <div className="flex items-center gap-2">
          {aberto && (
            <select
              aria-label="Período"
              className={cn(selectCls, "w-auto")}
              value={dias}
              onChange={(e) => setDias(Number(e.target.value))}
            >
              {PERIODOS.map((p) => (
                <option key={p} value={p}>
                  Últimos {p} dias
                </option>
              ))}
            </select>
          )}
          <Button variant="ghost" size="sm" onClick={() => setAberto(!aberto)}>
            {aberto ? "Esconder" : "Mostrar"}
          </Button>
        </div>
      </div>

      {aberto &&
        (isLoading || !data ? (
          <p className="mt-2 text-muted-foreground text-sm">Carregando…</p>
        ) : !data.disponivel ? (
          <p className="mt-2 text-muted-foreground text-sm">
            Sem ligação com o banco do agente agora: não dá para contar os
            envios.
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <Resumo titulo="Hoje" c={data.hoje} semTaxa />
              <Resumo titulo={`Últimos ${data.dias} dias`} c={data.total} />
            </div>
            <p className="text-muted-foreground text-xs">
              Empresas = empresas que receberam o disparo. Cada abordagem manda
              2 mensagens. Responderam = empresas que escreveram de volta no dia
              (ou no período).
            </p>
            {instancia ? (
              <PorDia linhas={data.por_dia} />
            ) : (
              <PorNumero linhas={data.numeros} onEscolher={onEscolher} />
            )}
          </div>
        ))}
    </section>
  )
}

function Resumo({
  titulo,
  c,
  semTaxa,
}: {
  titulo: string
  c: Contagem
  semTaxa?: boolean
}) {
  return (
    <div className="rounded-md bg-muted/40 px-3 py-2">
      <div className="text-muted-foreground text-xs">{titulo}</div>
      <div className="flex flex-wrap gap-x-4 text-sm">
        <span>
          <b className="tabular-nums">{num.format(c.empresas)}</b> empresas
        </span>
        <span>
          <b className="tabular-nums">{num.format(c.mensagens)}</b> mensagens
        </span>
        <span>
          <b className="tabular-nums">{num.format(c.respostas)}</b> responderam
          {!semTaxa && ` (${pct(c.respostas, c.empresas)})`}
        </span>
      </div>
    </div>
  )
}

function PorNumero({
  linhas,
  onEscolher,
}: {
  linhas: NumeroDesempenho[]
  onEscolher: (instancia: string) => void
}) {
  if (!linhas.length)
    return (
      <p className="text-muted-foreground text-sm">Nenhum envio no período.</p>
    )
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Número</TableHead>
            <TableHead className="text-right">Hoje</TableHead>
            <TableHead className="text-right">Empresas</TableHead>
            <TableHead className="text-right">Mensagens</TableHead>
            <TableHead className="text-right">Responderam</TableHead>
            <TableHead className="text-right">Taxa</TableHead>
            <TableHead>Último envio</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {linhas.map((x) => (
            <TableRow
              key={x.instancia}
              className={cn(x.instancia && "cursor-pointer")}
              title={
                x.instancia
                  ? `${x.instancia}: clique para ver só este número`
                  : "Envios sem número registrado"
              }
              onClick={() => x.instancia && onEscolher(x.instancia)}
            >
              <TableCell className="font-medium">{x.nome}</TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.hoje.empresas)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.empresas)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.mensagens)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.respostas)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {pct(x.respostas, x.empresas)}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {quando(x.ultimo_envio)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

function PorDia({ linhas }: { linhas: DiaDesempenho[] }) {
  return (
    <div className="max-h-80 overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Dia</TableHead>
            <TableHead className="text-right">Empresas</TableHead>
            <TableHead className="text-right">Mensagens</TableHead>
            <TableHead className="text-right">Responderam</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {linhas.map((x) => (
            <TableRow
              key={x.dia}
              className={cn(!x.empresas && !x.respostas && "opacity-50")}
            >
              <TableCell>{diaFmt(x.dia)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.empresas)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.mensagens)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {num.format(x.respostas)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
