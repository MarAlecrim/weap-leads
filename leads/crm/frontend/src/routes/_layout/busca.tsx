import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Columns3, Download } from "lucide-react"
import { useEffect, useState } from "react"

import { type Lead, LeadsService } from "@/client"
import {
  baixarPlanilha,
  corDaNota,
  type FiltrosBusca,
  filtrosPadrao,
  paraApi,
} from "@/components/Leads/api"
import { Ficha } from "@/components/Leads/Ficha"
import { Filtros } from "@/components/Leads/Filtros"
import { MandarDisparo } from "@/components/Leads/MandarDisparo"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/busca")({
  component: Busca,
  head: () => ({ meta: [{ title: "Busca de leads - Weap" }] }),
})

const numero = new Intl.NumberFormat("pt-BR")
const moeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
})

const COLUNAS = {
  decisor: "Decisor",
  bairro: "Bairro e cidade",
  whatsapp: "WhatsApp",
  porte: "Porte",
  capital: "Capital social",
  anos: "Anos de empresa",
} as const
type Coluna = keyof typeof COLUNAS
const COLUNAS_PADRAO: Coluna[] = ["decisor", "bairro", "whatsapp"]
const CHAVE_COLUNAS = "weap-leads:colunas"

function lerColunas(): Coluna[] {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE_COLUNAS) ?? "null")
    if (Array.isArray(salvo)) {
      return salvo.filter((c): c is Coluna => c in COLUNAS)
    }
  } catch {
    // sem localStorage: usa o padrão
  }
  return COLUNAS_PADRAO
}

function useColunas() {
  const [colunas, setColunas] = useState<Coluna[]>(lerColunas)
  useEffect(() => {
    try {
      localStorage.setItem(CHAVE_COLUNAS, JSON.stringify(colunas))
    } catch {
      // ignora
    }
  }, [colunas])
  const alternar = (c: Coluna, v: boolean) =>
    setColunas((atual) =>
      v
        ? (Object.keys(COLUNAS) as Coluna[]).filter(
            (k) => k === c || atual.includes(k),
          )
        : atual.filter((k) => k !== c),
    )
  return { colunas, alternar }
}

function Busca() {
  const [rascunho, setRascunho] = useState<FiltrosBusca>(filtrosPadrao)
  // a busca só roda depois do primeiro clique em Buscar
  const [filtros, setFiltros] = useState<FiltrosBusca | null>(null)
  const [pagina, setPagina] = useState(1)
  const [marcados, setMarcados] = useState<string[]>([])
  const [aberto, setAberto] = useState<string | null>(null)
  const [pularDisparo, setPularDisparo] = useState(true)
  const [baixando, setBaixando] = useState(false)
  const { showErrorToast } = useCustomToast()
  const { colunas, alternar } = useColunas()
  const ver = (c: Coluna) => colunas.includes(c)
  const nColunas = 3 + colunas.length

  const { data: opcoes } = useQuery({
    queryKey: ["opcoes"],
    queryFn: () => LeadsService.opcoes(),
    staleTime: Number.POSITIVE_INFINITY,
  })

  const { data, isFetching, isLoading } = useQuery({
    queryKey: ["leads", filtros, pagina],
    queryFn: () =>
      LeadsService.buscar({ ...paraApi(filtros ?? filtrosPadrao), pagina }),
    enabled: filtros !== null,
    placeholderData: keepPreviousData,
  })

  const { data: fila } = useQuery({
    queryKey: ["fila"],
    queryFn: () => LeadsService.fila(),
    refetchInterval: 60_000,
  })

  const total = data?.count ?? 0
  const paginas = Math.max(1, Math.ceil(total / (data?.por_pagina ?? 50)))
  const linhas = data?.data ?? []
  const todosMarcados =
    linhas.length > 0 && linhas.every((l) => marcados.includes(l.cnpj))

  const buscar = () => {
    setFiltros(rascunho)
    setPagina(1)
    setMarcados([])
  }

  const marcar = (cnpj: string, v: boolean) =>
    setMarcados((m) => (v ? [...m, cnpj] : m.filter((x) => x !== cnpj)))

  const baixar = async (so_marcados: boolean) => {
    if (!filtros) return
    setBaixando(true)
    try {
      await baixarPlanilha(filtros, so_marcados ? marcados : [], pularDisparo)
    } catch (e) {
      showErrorToast((e as Error).message)
    } finally {
      setBaixando(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Busca de leads</h1>
        <p className="text-muted-foreground">
          Empresas ativas da Receita, da nota mais alta para a mais baixa. A
          nota mostra o quanto a empresa se parece com quem já é cliente da
          Weap.
        </p>
      </div>

      <Filtros
        opcoes={opcoes}
        valor={rascunho}
        onChange={setRascunho}
        onBuscar={buscar}
      />

      <div className="flex flex-wrap items-center gap-3">
        <strong>
          {!filtros
            ? "Escolha os filtros e clique em Buscar"
            : isLoading
              ? "Buscando…"
              : `${numero.format(total)} empresas`}
        </strong>
        {isFetching && !isLoading && (
          <span className="text-sm text-muted-foreground">atualizando…</span>
        )}
        {fila && (
          <span className="text-sm text-muted-foreground">
            Fila do disparo: {numero.format(fila.aguardando)} aguardando ·{" "}
            {numero.format(fila.enviados_hoje)} enviados hoje
          </span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Columns3 /> Colunas
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Mostrar na tabela</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {(Object.keys(COLUNAS) as Coluna[]).map((c) => (
                <DropdownMenuCheckboxItem
                  key={c}
                  checked={ver(c)}
                  onCheckedChange={(v) => alternar(c, v === true)}
                  onSelect={(e) => e.preventDefault()}
                >
                  {COLUNAS[c]}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <div className="flex items-center gap-2">
            <Checkbox
              id="pular"
              checked={pularDisparo}
              onCheckedChange={(v) => setPularDisparo(v === true)}
            />
            <Label htmlFor="pular" className="font-normal">
              Pular quem já está no disparo
            </Label>
          </div>
          <Button
            variant="outline"
            disabled={!marcados.length || baixando}
            onClick={() => baixar(true)}
          >
            <Download /> Planilha dos marcados ({marcados.length})
          </Button>
          <Button
            variant="outline"
            disabled={!total || baixando}
            onClick={() => baixar(false)}
          >
            <Download /> Planilha de todos (até 3.000)
          </Button>
          <MandarDisparo
            filtros={filtros ?? filtrosPadrao}
            marcados={marcados}
            total={total}
            onFeito={() => setMarcados([])}
          />
        </div>
      </div>

      <div className="rounded-lg border">
        <Table className="table-fixed">
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10">
                <Checkbox
                  aria-label="Marcar todos da página"
                  checked={todosMarcados}
                  onCheckedChange={(v) =>
                    setMarcados((m) =>
                      v === true
                        ? [...new Set([...m, ...linhas.map((l) => l.cnpj)])]
                        : m.filter((x) => !linhas.some((l) => l.cnpj === x)),
                    )
                  }
                />
              </TableHead>
              <TableHead className="w-20">Nota</TableHead>
              <TableHead>Empresa</TableHead>
              {ver("decisor") && (
                <TableHead className="hidden w-[18%] md:table-cell">
                  Decisor
                </TableHead>
              )}
              {ver("bairro") && (
                <TableHead className="hidden w-[18%] lg:table-cell">
                  Bairro
                </TableHead>
              )}
              {ver("whatsapp") && (
                <TableHead className="hidden w-40 sm:table-cell">
                  WhatsApp
                </TableHead>
              )}
              {ver("porte") && (
                <TableHead className="hidden w-36 lg:table-cell">
                  Porte
                </TableHead>
              )}
              {ver("capital") && (
                <TableHead className="hidden w-32 text-right lg:table-cell">
                  Capital
                </TableHead>
              )}
              {ver("anos") && (
                <TableHead className="hidden w-20 lg:table-cell">
                  Anos
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={nColunas}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {!isLoading && linhas.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={nColunas}
                  className="py-10 text-center text-muted-foreground"
                >
                  {filtros
                    ? "Nenhuma empresa com esses filtros."
                    : "Escolha os filtros acima e clique em Buscar."}
                </TableCell>
              </TableRow>
            )}
            {linhas.map((l: Lead) => (
              <TableRow key={l.cnpj}>
                <TableCell>
                  <Checkbox
                    aria-label={`Marcar ${l.nome}`}
                    checked={marcados.includes(l.cnpj)}
                    onCheckedChange={(v) => marcar(l.cnpj, v === true)}
                  />
                </TableCell>
                <TableCell>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        className={`inline-block min-w-9 rounded-md px-1.5 py-0.5 text-center text-sm font-semibold tabular-nums ${corDaNota(l.nota)}`}
                      >
                        {l.nota}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>
                      {l.motivos.length
                        ? l.motivos.join(" · ")
                        : "Não se parece com os clientes atuais"}
                    </TooltipContent>
                  </Tooltip>
                </TableCell>
                <TableCell className="max-w-0">
                  <button
                    type="button"
                    title={l.nome}
                    className="block max-w-full truncate text-left font-medium hover:text-primary hover:underline"
                    onClick={() => setAberto(l.cnpj)}
                  >
                    {l.nome}
                  </button>
                  <div
                    className="truncate text-xs text-muted-foreground"
                    title={l.atividade ?? ""}
                  >
                    {l.atividade}
                  </div>
                  {l.no_disparo && (
                    <Badge variant="secondary" className="mt-1">
                      no disparo
                    </Badge>
                  )}
                </TableCell>
                {ver("decisor") && (
                  <TableCell
                    className="hidden max-w-0 truncate md:table-cell"
                    title={l.decisor ?? ""}
                  >
                    {l.decisor || (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                )}
                {ver("bairro") && (
                  <TableCell className="hidden max-w-0 lg:table-cell">
                    <div className="truncate" title={l.bairro ?? ""}>
                      {l.bairro}
                    </div>
                    <div className="truncate text-xs text-muted-foreground">
                      {l.cidade}
                    </div>
                  </TableCell>
                )}
                {ver("whatsapp") && (
                  <TableCell className="hidden whitespace-nowrap sm:table-cell">
                    {l.whatsapp ? (
                      <a
                        className="hover:text-primary hover:underline"
                        href={`https://wa.me/55${l.whatsapp}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {l.telefone1 &&
                        l.telefone1.replace(/\D/g, "") === l.whatsapp
                          ? l.telefone1
                          : l.telefone2}
                      </a>
                    ) : (
                      <span className="text-muted-foreground">só fixo</span>
                    )}
                  </TableCell>
                )}
                {ver("porte") && (
                  <TableCell className="hidden truncate lg:table-cell">
                    {l.porte}
                  </TableCell>
                )}
                {ver("capital") && (
                  <TableCell className="hidden text-right tabular-nums lg:table-cell">
                    {moeda.format(l.capital_social)}
                  </TableCell>
                )}
                {ver("anos") && (
                  <TableCell className="hidden tabular-nums lg:table-cell">
                    {l.anos ?? ""}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-end gap-3">
        <span className="text-sm text-muted-foreground">
          Página {pagina} de {numero.format(paginas)}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={pagina <= 1}
          onClick={() => setPagina((p) => p - 1)}
        >
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={pagina >= paginas}
          onClick={() => setPagina((p) => p + 1)}
        >
          Próxima
        </Button>
      </div>

      <Ficha
        cnpj={aberto}
        oferta={(filtros ?? rascunho).oferta}
        onClose={() => setAberto(null)}
      />
    </div>
  )
}
