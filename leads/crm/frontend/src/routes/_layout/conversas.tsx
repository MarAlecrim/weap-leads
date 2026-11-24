import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { type ConversaItem, ConversasService, FunilService } from "@/client"
import {
  AUTOR,
  ConversaPainel,
  dataHora,
} from "@/components/Conversas/ConversaPainel"
import { selectCls } from "@/components/Funil/util"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/_layout/conversas")({
  component: Conversas,
  head: () => ({ meta: [{ title: "Conversas - Weap" }] }),
})

/** A lista se atualiza a cada 10 s. */
const A_CADA_MS = 10000

function Conversas() {
  const [instancia, setInstancia] = useState("")
  const [naoLidas, setNaoLidas] = useState(false)
  const [digitado, setDigitado] = useState("")
  const [busca, setBusca] = useState("")
  const [aberta, setAberta] = useState<ConversaItem | null>(null)
  const { user: eu } = useAuth()
  const vendedor =
    !!eu && !eu.is_superuser && (eu.perfil ?? "vendedor") === "vendedor"

  const { data: opcoes } = useQuery({
    queryKey: ["funil-opcoes"],
    queryFn: () => FunilService.opcoes(),
  })
  const numeros = (opcoes?.numeros ?? []).filter(
    (n) => !vendedor || (eu?.numeros ?? []).includes(n.id),
  )

  const lista = useInfiniteQuery({
    queryKey: ["conversas", instancia, naoLidas, busca],
    queryFn: ({ pageParam }) =>
      ConversasService.lista({
        instancia: instancia || null,
        naoLidas,
        busca,
        antes: pageParam,
      }),
    initialPageParam: null as number | null,
    getNextPageParam: (ultima) =>
      ultima.tem_mais
        ? (ultima.conversas[ultima.conversas.length - 1]?.ultima_id ?? null)
        : null,
    refetchInterval: A_CADA_MS,
    placeholderData: keepPreviousData,
  })
  const paginas = lista.data?.pages ?? []
  const itens = paginas.flatMap((p) => p.conversas)
  const totalNaoLidas = paginas[0]?.nao_lidas ?? 0
  const ligado = paginas[0]?.ligado_ao_agente ?? true

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-bold text-2xl tracking-tight">Conversas</h1>
          <p className="text-muted-foreground text-sm">
            WhatsApp de {vendedor ? "os seus números" : "todos os números"}, da
            mais recente para a mais antiga.
            {totalNaoLidas > 0 && ` ${totalNaoLidas} com mensagem nova.`}
          </p>
        </div>
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            setBusca(digitado.trim())
          }}
        >
          <Input
            aria-label="Buscar conversa"
            className="h-9 w-48"
            placeholder="Nome ou telefone"
            value={digitado}
            onChange={(e) => setDigitado(e.target.value)}
            onBlur={() => setBusca(digitado.trim())}
          />
          {numeros.length > 1 && (
            <select
              aria-label="Número"
              className={cn(selectCls, "w-auto max-w-56")}
              value={instancia}
              onChange={(e) => setInstancia(e.target.value)}
            >
              <option value="">Todos os números</option>
              {numeros.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.nome}
                </option>
              ))}
            </select>
          )}
          <Button
            type="button"
            size="sm"
            variant={naoLidas ? "default" : "outline"}
            onClick={() => setNaoLidas((v) => !v)}
          >
            Só não lidas
          </Button>
        </form>
      </div>

      {!ligado ? (
        <p className="rounded-lg border p-4 text-muted-foreground text-sm">
          O CRM não está ligado ao banco do agente, então não há conversas para
          mostrar.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-[minmax(260px,360px)_1fr]">
          <div
            className={cn(
              "grid grid-cols-1 content-start gap-1 overflow-y-auto rounded-lg border p-1 md:h-[calc(100vh-220px)]",
              aberta && "hidden md:grid",
            )}
          >
            {lista.isLoading &&
              [1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            {lista.isError && (
              <p className="p-3 text-muted-foreground text-sm">
                Não consegui ler as conversas agora.
              </p>
            )}
            {!lista.isLoading && !lista.isError && itens.length === 0 && (
              <p className="p-3 text-muted-foreground text-sm">
                {naoLidas || busca || instancia
                  ? "Nenhuma conversa com esses filtros."
                  : "Nenhum lead respondeu ainda."}
              </p>
            )}
            {itens.map((c) => (
              <button
                type="button"
                key={c.chave}
                onClick={() => setAberta(c)}
                className={cn(
                  "grid w-full min-w-0 gap-0.5 rounded-md px-3 py-2 text-left text-sm hover:bg-muted",
                  aberta?.chave === c.chave && "bg-muted",
                )}
              >
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span
                    className={cn(
                      "truncate",
                      c.nao_lidas > 0 && "font-semibold",
                    )}
                  >
                    {c.nome}
                  </span>
                  <span className="shrink-0 text-muted-foreground text-xs tabular-nums">
                    {dataHora(c.ultima_em)}
                  </span>
                </div>
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <span className="truncate text-muted-foreground">
                    {c.ultima_autor !== "lead" &&
                      `${AUTOR[c.ultima_autor] ?? c.ultima_autor}: `}
                    {c.ultima_texto || "[mensagem sem texto]"}
                  </span>
                  {c.nao_lidas > 0 && (
                    <span className="shrink-0 rounded-full bg-primary px-1.5 text-primary-foreground text-xs tabular-nums">
                      {c.nao_lidas}
                    </span>
                  )}
                </div>
                <div className="text-muted-foreground text-xs">
                  {c.numero ? `número ${c.numero}` : ""}
                  {c.ia_pausada ? " · IA pausada" : ""}
                </div>
              </button>
            ))}
            {lista.hasNextPage && (
              <Button
                variant="ghost"
                size="sm"
                disabled={lista.isFetchingNextPage}
                onClick={() => lista.fetchNextPage()}
              >
                Carregar mais
              </Button>
            )}
          </div>

          <div
            className={cn(
              "grid content-start gap-2",
              !aberta && "hidden md:grid",
            )}
          >
            {aberta ? (
              <>
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div>
                    <h2 className="font-semibold">{aberta.nome}</h2>
                    <p className="text-muted-foreground text-xs">
                      {aberta.numero ? `Número ${aberta.numero}` : ""}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="md:hidden"
                    onClick={() => setAberta(null)}
                  >
                    Voltar
                  </Button>
                </div>
                <ConversaPainel
                  chave={aberta.chave}
                  altura="h-[calc(100vh-420px)] min-h-[260px]"
                />
              </>
            ) : (
              <p className="rounded-lg border p-6 text-muted-foreground text-sm">
                Escolha uma conversa na lista.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
