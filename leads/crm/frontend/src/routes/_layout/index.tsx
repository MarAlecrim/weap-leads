import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Download } from "lucide-react"
import { useState } from "react"

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
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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

export const Route = createFileRoute("/_layout/")({
  component: Busca,
  head: () => ({ meta: [{ title: "Busca de leads - Weap" }] }),
})

const numero = new Intl.NumberFormat("pt-BR")

function Busca() {
  const [rascunho, setRascunho] = useState<FiltrosBusca>(filtrosPadrao)
  const [filtros, setFiltros] = useState<FiltrosBusca>(filtrosPadrao)
  const [pagina, setPagina] = useState(1)
  const [marcados, setMarcados] = useState<string[]>([])
  const [aberto, setAberto] = useState<string | null>(null)
  const [pularDisparo, setPularDisparo] = useState(true)
  const [baixando, setBaixando] = useState(false)
  const { showErrorToast } = useCustomToast()

  const { data: opcoes } = useQuery({
    queryKey: ["opcoes"],
    queryFn: () => LeadsService.opcoes(),
    staleTime: Number.POSITIVE_INFINITY,
  })

  const { data, isFetching, isLoading } = useQuery({
    queryKey: ["leads", filtros, pagina],
    queryFn: () => LeadsService.buscar({ ...paraApi(filtros), pagina }),
    placeholderData: keepPreviousData,
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
          {isLoading ? "Buscando…" : `${numero.format(total)} empresas`}
        </strong>
        {isFetching && !isLoading && (
          <span className="text-sm text-muted-foreground">atualizando…</span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-3">
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
          <Button disabled={!total || baixando} onClick={() => baixar(false)}>
            <Download /> Planilha de todos (até 3.000)
          </Button>
        </div>
      </div>

      <div className="rounded-lg border">
        <Table>
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
              <TableHead className="w-16">Nota</TableHead>
              <TableHead>Empresa</TableHead>
              <TableHead className="hidden md:table-cell">Decisor</TableHead>
              <TableHead className="hidden lg:table-cell">Bairro</TableHead>
              <TableHead className="hidden sm:table-cell">WhatsApp</TableHead>
              <TableHead className="hidden lg:table-cell">Porte</TableHead>
              <TableHead className="hidden lg:table-cell">Anos</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={8}>
                    <Skeleton className="h-6 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {!isLoading && linhas.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="py-10 text-center text-muted-foreground"
                >
                  Nenhuma empresa com esses filtros.
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
                <TableCell>
                  <button
                    type="button"
                    className="text-left font-medium hover:text-primary hover:underline"
                    onClick={() => setAberto(l.cnpj)}
                  >
                    {l.nome}
                  </button>
                  <div className="text-xs text-muted-foreground">
                    {l.atividade}
                  </div>
                  {l.no_disparo && (
                    <Badge variant="secondary" className="mt-1">
                      no disparo
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {l.decisor || (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {l.bairro}
                  <div className="text-xs text-muted-foreground">
                    {l.cidade}
                  </div>
                </TableCell>
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
                <TableCell className="hidden lg:table-cell">
                  {l.porte}
                </TableCell>
                <TableCell className="hidden lg:table-cell tabular-nums">
                  {l.anos ?? ""}
                </TableCell>
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
        oferta={filtros.oferta}
        onClose={() => setAberto(null)}
      />
    </div>
  )
}
