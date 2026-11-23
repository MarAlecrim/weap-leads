import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { type Card, type Coluna, FunilService } from "@/client"
import { CardFunil } from "@/components/Funil/CardFunil"
import { EditarCard } from "@/components/Funil/EditarCard"
import { ORIGENS, reais, selectCls } from "@/components/Funil/util"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/funil")({
  component: Funil,
  head: () => ({ meta: [{ title: "Funil - Weap" }] }),
})

// Etapas que ficam recolhidas nas pontas até a pessoa abrir
const RECOLHIDAS = ["fila", "ganho", "perdido"]

type Filtros = {
  responsavel_id: string
  instancia: string
  origem: string
  parados: boolean
  busca: string
}

const VAZIO: Filtros = {
  responsavel_id: "",
  instancia: "",
  origem: "",
  parados: false,
  busca: "",
}

function Funil() {
  const [f, setF] = useState<Filtros>(VAZIO)
  const [busca, setBusca] = useState("")
  const [abertas, setAbertas] = useState<string[]>([])
  const [editando, setEditando] = useState<{
    card: Card
    etapa?: string
  } | null>(null)
  const [sobre, setSobre] = useState<string | null>(null)
  const qc = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: opcoes } = useQuery({
    queryKey: ["funil-opcoes"],
    queryFn: () => FunilService.opcoes(),
    staleTime: 60_000,
  })
  const { data, isLoading } = useQuery({
    queryKey: ["funil", f],
    queryFn: () =>
      FunilService.funil({
        responsavelId: f.responsavel_id || undefined,
        instancia: f.instancia || undefined,
        origem: f.origem || undefined,
        parados: f.parados,
        busca: f.busca || undefined,
      }),
    refetchInterval: 60_000,
  })

  const mover = useMutation({
    mutationFn: ({ id, etapa }: { id: number; etapa: string }) =>
      FunilService.atualizar({ negocioId: id, requestBody: { etapa } }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["funil"] }),
    onError: (e: unknown) =>
      showErrorToast(
        (e as { body?: { detail?: string } })?.body?.detail ||
          "Não foi possível mover o card.",
      ),
  })

  const colunas = data?.colunas ?? []
  const todos = colunas.flatMap((c) => c.cards)
  const soltar = (etapa: string, idTexto: string) => {
    setSobre(null)
    const card = todos.find((c) => String(c.id) === idTexto)
    if (!card || card.etapa === etapa) return
    if (etapa === "perdido") setEditando({ card, etapa })
    else mover.mutate({ id: card.id, etapa })
  }

  const visiveis = colunas.filter(
    (c) => !RECOLHIDAS.includes(c.etapa) || abertas.includes(c.etapa),
  )
  const alternar = (etapa: string) =>
    setAbertas((a) =>
      a.includes(etapa) ? a.filter((x) => x !== etapa) : [...a, etapa],
    )
  const recolhida = (etapa: string) => colunas.find((c) => c.etapa === etapa)

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Funil</h1>
        <p className="text-muted-foreground">
          Cada lead do disparo é um card. O agente leva o card sozinho até
          "Reunião marcada"; daí em diante, arraste ou clique para mudar.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <select
          aria-label="Responsável"
          className={cn(selectCls, "w-auto")}
          value={f.responsavel_id}
          onChange={(e) => setF({ ...f, responsavel_id: e.target.value })}
        >
          <option value="">Responsável: todos</option>
          {opcoes?.responsaveis.map((r) => (
            <option key={r.id} value={r.id}>
              {r.nome}
            </option>
          ))}
        </select>
        <select
          aria-label="Número"
          className={cn(selectCls, "w-auto")}
          value={f.instancia}
          onChange={(e) => setF({ ...f, instancia: e.target.value })}
        >
          <option value="">Número: todos</option>
          {opcoes?.numeros.map((n) => (
            <option key={n.id} value={n.id}>
              {n.nome}
            </option>
          ))}
        </select>
        <select
          aria-label="Origem"
          className={cn(selectCls, "w-auto")}
          value={f.origem}
          onChange={(e) => setF({ ...f, origem: e.target.value })}
        >
          <option value="">Origem: todas</option>
          {Object.entries(ORIGENS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <Button
          variant={f.parados ? "default" : "outline"}
          onClick={() => setF({ ...f, parados: !f.parados })}
        >
          Parados há +3 dias
        </Button>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            setF({ ...f, busca })
          }}
        >
          <Input
            className="w-56"
            placeholder="Buscar empresa, CNPJ ou telefone"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </form>
        {(JSON.stringify(f) !== JSON.stringify(VAZIO) || busca) && (
          <Button
            variant="ghost"
            onClick={() => {
              setF(VAZIO)
              setBusca("")
            }}
          >
            Limpar
          </Button>
        )}
      </div>

      {data && !data.ligado_ao_agente && (
        <p className="rounded-md border border-amber-500/50 p-3 text-sm">
          O CRM não está ligado ao banco do agente. Os cards não vão andar
          sozinhos.
        </p>
      )}

      <div className="flex flex-wrap justify-between gap-2 text-sm">
        <Recolhida
          coluna={recolhida("fila")}
          aberta={abertas.includes("fila")}
          onClick={() => alternar("fila")}
          seta="esquerda"
        />
        <div className="flex gap-2">
          {["ganho", "perdido"].map((e) => (
            <Recolhida
              key={e}
              coluna={recolhida(e)}
              aberta={abertas.includes(e)}
              onClick={() => alternar(e)}
              seta="direita"
            />
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Carregando o funil…</p>
      ) : (
        <div
          className="grid gap-3 overflow-x-auto pb-2"
          style={{
            gridTemplateColumns: `repeat(${visiveis.length}, minmax(170px, 1fr))`,
          }}
        >
          {visiveis.map((c) => (
            <section
              key={c.etapa}
              aria-label={c.nome}
              onDragOver={(e) => {
                e.preventDefault()
                setSobre(c.etapa)
              }}
              onDragLeave={() => setSobre((s) => (s === c.etapa ? null : s))}
              onDrop={(e) => {
                e.preventDefault()
                soltar(c.etapa, e.dataTransfer.getData("text/plain"))
              }}
              className={cn(
                "flex min-h-64 flex-col gap-2 rounded-lg border bg-muted/40 p-2",
                sobre === c.etapa && "border-primary bg-primary/5",
              )}
            >
              <header className="border-b px-1 pb-2">
                <h2 className="font-semibold">{c.nome}</h2>
                <p className="text-muted-foreground text-xs">
                  {c.total === 1 ? "1 lead" : `${c.total} leads`}
                  {c.valor_cents ? ` · ${reais(c.valor_cents)}` : ""}
                </p>
              </header>
              {c.cards.map((card) => (
                <CardFunil
                  key={card.id}
                  card={card}
                  onAbrir={(x) => setEditando({ card: x })}
                />
              ))}
              {c.total > c.cards.length && (
                <p className="px-1 text-muted-foreground text-xs">
                  Mostrando {c.cards.length} de {c.total}. Use os filtros para
                  achar os outros.
                </p>
              )}
            </section>
          ))}
        </div>
      )}

      <EditarCard
        card={editando?.card ?? null}
        etapaPedida={editando?.etapa}
        opcoes={opcoes}
        onFechar={() => setEditando(null)}
      />
    </div>
  )
}

function Recolhida({
  coluna,
  aberta,
  onClick,
  seta,
}: {
  coluna: Coluna | undefined
  aberta: boolean
  onClick: () => void
  seta: "esquerda" | "direita"
}) {
  if (!coluna) return null
  const texto = `${coluna.nome} ${coluna.total}${coluna.valor_cents ? ` · ${reais(coluna.valor_cents)}` : ""}`
  return (
    <Button
      variant={aberta ? "secondary" : "ghost"}
      size="sm"
      onClick={onClick}
    >
      {seta === "esquerda" && "← "}
      {aberta ? `Esconder ${coluna.nome}` : texto}
      {seta === "direita" && " →"}
    </Button>
  )
}
