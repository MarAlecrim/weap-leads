import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"

import { type Conversa, ConversasService } from "@/client"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

export const AUTOR: Record<string, string> = {
  disparo: "Disparo",
  ia: "IA",
  lead: "Lead",
  humano: "Pessoa",
}

export const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  })

const erro = (e: unknown, padrao: string) =>
  (e as { body?: { detail?: string } })?.body?.detail || padrao

/** Atualiza a conversa aberta a cada 5 s (quase tempo real). */
const A_CADA_MS = 5000

/** Conversa do WhatsApp com um lead: mensagens, resposta pelo mesmo número e pausa/retomada da IA. */
export function ConversaPainel({
  chave,
  altura = "h-[420px]",
  mostrarResumo = true,
}: {
  chave: string | null
  altura?: string
  mostrarResumo?: boolean
}) {
  const [texto, setTexto] = useState("")
  const qc = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const chaveQ = ["conversa", chave]

  const { data, isLoading, isError } = useQuery({
    queryKey: chaveQ,
    queryFn: () => ConversasService.abrir({ chave: chave! }),
    enabled: !!chave,
    refetchInterval: A_CADA_MS,
    retry: false,
  })

  const atualizou = (c: Conversa) => {
    qc.setQueryData(chaveQ, c)
    qc.invalidateQueries({ queryKey: ["conversas"] })
    qc.invalidateQueries({ queryKey: ["funil"] })
  }

  const responder = useMutation({
    mutationFn: () =>
      ConversasService.responder({
        chave: chave!,
        requestBody: { texto: texto.trim() },
      }),
    onSuccess: (c) => {
      setTexto("")
      atualizou(c)
    },
    onError: (e) => showErrorToast(erro(e, "Não foi possível enviar.")),
  })

  const retomar = useMutation({
    mutationFn: () => ConversasService.retomar({ chave: chave! }),
    onSuccess: atualizou,
    onError: (e) => showErrorToast(erro(e, "Não foi possível retomar a IA.")),
  })

  const fim = useRef<HTMLDivElement>(null)
  const ultima = data?.mensagens[data.mensagens.length - 1]?.id ?? 0
  // rola para a mensagem mais nova quando chega uma nova
  useEffect(() => {
    if (ultima) fim.current?.scrollIntoView({ block: "end" })
  }, [ultima])

  if (!chave)
    return (
      <p className="rounded-lg border p-4 text-muted-foreground text-sm">
        Ainda não há conversa com este lead.
      </p>
    )
  if (isLoading) return <Skeleton className={cn(altura, "w-full rounded-lg")} />
  if (isError || !data)
    return (
      <p className="rounded-lg border p-4 text-muted-foreground text-sm">
        Não consegui ler a conversa agora (banco do agente fora do ar, ou este
        lead ainda não recebeu mensagem).
      </p>
    )

  const enviar = () => {
    if (texto.trim() && !responder.isPending) responder.mutate()
  }

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-xs",
            data.ia_pausada
              ? "border-amber-500/50 bg-amber-500/10"
              : "border-emerald-500/50 bg-emerald-500/10",
          )}
        >
          {data.ia_pausada
            ? "IA pausada: uma pessoa está conversando"
            : "IA respondendo"}
        </span>
        {data.ia_pausada && !data.opt_out && (
          <Button
            size="sm"
            variant="outline"
            disabled={retomar.isPending}
            onClick={() => retomar.mutate()}
          >
            Devolver para a IA
          </Button>
        )}
      </div>

      <div
        className={cn(
          altura,
          "grid content-start gap-2 overflow-y-auto rounded-lg border bg-muted/30 p-3",
        )}
      >
        {data.mensagens.length === 0 && (
          <p className="text-muted-foreground text-sm">
            Ainda não há mensagens com este lead.
          </p>
        )}
        {data.mensagens.map((m) => {
          const nosso = m.direcao === "out"
          return (
            <div
              key={m.id}
              className={cn(
                "max-w-[80%] rounded-lg border px-3 py-2 text-sm",
                nosso
                  ? "justify-self-end border-primary/40 bg-primary/10"
                  : "justify-self-start bg-background",
                m.autor === "humano" && "border-primary bg-primary/20",
              )}
            >
              <div className="text-muted-foreground text-xs">
                {AUTOR[m.autor] ?? m.autor} · {dataHora(m.criado_em)}
              </div>
              <p className="whitespace-pre-line break-words">
                {m.texto || "[mensagem sem texto]"}
              </p>
            </div>
          )
        })}
        <div ref={fim} />
      </div>

      {data.opt_out ? (
        <p className="text-muted-foreground text-sm">
          Este lead pediu para não receber mensagens. A resposta fica fechada.
        </p>
      ) : data.pode_responder ? (
        <form
          className="grid gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            enviar()
          }}
        >
          <textarea
            aria-label="Resposta"
            className="min-h-16 rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-input/30"
            placeholder={`Responder pelo número ${data.numero ?? ""} (Enter envia, Shift+Enter pula linha)`}
            value={texto}
            maxLength={4000}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                enviar()
              }
            }}
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-muted-foreground text-xs">
              Ao responder, a IA para de falar com este lead até você devolver.
            </span>
            <Button
              type="submit"
              size="sm"
              disabled={!texto.trim() || responder.isPending}
            >
              {responder.isPending ? "Enviando..." : "Enviar"}
            </Button>
          </div>
        </form>
      ) : (
        <p className="text-muted-foreground text-sm">
          Responder pelo CRM ainda não está ligado neste servidor.
        </p>
      )}

      {mostrarResumo && data.resumo && (
        <div className="rounded-lg border bg-muted/50 p-3 text-sm">
          <div className="mb-1 font-semibold">Resumo da IA</div>
          <p className="whitespace-pre-line">{data.resumo}</p>
        </div>
      )}
    </div>
  )
}
