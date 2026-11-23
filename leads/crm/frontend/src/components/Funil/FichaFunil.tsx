import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useRef, useState } from "react"

import {
  type Card,
  type CardFicha,
  type FunilOpcoes,
  FunilService,
  LeadsService,
  type NegocioAtualiza,
} from "@/client"
import { Ficha } from "@/components/Leads/Ficha"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"
import { cnpjFmt, deInput, foneFmt, paraInput, reais, selectCls } from "./util"

type Props = {
  card: Card | null
  /** etapa pedida ao arrastar para "Perdido": abre já pedindo o motivo */
  etapaPedida?: string
  opcoes: FunilOpcoes | undefined
  onFechar: () => void
}

const erro = (e: unknown) =>
  (e as { body?: { detail?: string } })?.body?.detail ||
  "Não foi possível salvar."

const AUTOR: Record<string, string> = {
  disparo: "Disparo",
  ia: "IA",
  lead: "Lead",
  humano: "Pessoa",
}

const NOME_ETAPA = (opcoes: FunilOpcoes | undefined, id: string | null) =>
  opcoes?.etapas.find((e) => e.id === id)?.nome ?? id ?? ""

const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  })

/** Ficha do card: o que muda à mão, os dados da Receita, a conversa do WhatsApp, notas e histórico. */
export function FichaFunil({ card, etapaPedida, opcoes, onFechar }: Props) {
  const [f, setF] = useState<NegocioAtualiza>({})
  const [valor, setValor] = useState("")
  const [nota, setNota] = useState("")
  const [receitaAberta, setReceitaAberta] = useState(false)
  const qc = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: ficha, isLoading } = useQuery({
    queryKey: ["funil-ficha", card?.id],
    queryFn: () => FunilService.ficha({ negocioId: card!.id }),
    enabled: !!card,
  })
  const { data: empresa } = useQuery({
    queryKey: ["lead", card?.cnpj, "geral"],
    queryFn: () => LeadsService.ficha({ cnpj: card!.cnpj!, oferta: "geral" }),
    enabled: !!card?.cnpj,
  })

  useEffect(() => {
    if (!card) return
    setF({
      etapa: etapaPedida ?? card.etapa,
      servico: card.servico ?? "",
      responsavel_id: card.responsavel_id ?? null,
      perdido_motivo: card.perdido_motivo ?? "",
      proxima_acao: card.proxima_acao ?? "",
      proxima_acao_em: card.proxima_acao_em ?? null,
    })
    setValor(card.valor_cents ? String(card.valor_cents / 100) : "")
    setNota("")
  }, [card, etapaPedida])

  const salvar = useMutation({
    mutationFn: () => {
      const cents = valor.trim()
        ? Math.round(Number(valor.replace(/\./g, "").replace(",", ".")) * 100)
        : null
      return FunilService.atualizar({
        negocioId: card!.id,
        requestBody: {
          ...f,
          servico: f.servico || null,
          perdido_motivo: f.perdido_motivo || null,
          proxima_acao: f.proxima_acao || null,
          valor_cents: Number.isFinite(cents) ? cents : null,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast("Card atualizado.")
      qc.invalidateQueries({ queryKey: ["funil"] })
      qc.invalidateQueries({ queryKey: ["funil-ficha", card?.id] })
      onFechar()
    },
    onError: (e) => showErrorToast(erro(e)),
  })

  const anotar = useMutation({
    mutationFn: () =>
      FunilService.novaNota({
        negocioId: card!.id,
        requestBody: { texto: nota },
      }),
    onSuccess: (r) => {
      qc.setQueryData(["funil-ficha", card?.id], r)
      setNota("")
    },
    onError: (e) => showErrorToast(erro(e)),
  })

  const set = <K extends keyof NegocioAtualiza>(k: K, v: NegocioAtualiza[K]) =>
    setF((x) => ({ ...x, [k]: v }))

  const escolherServico = (id: string) => {
    set("servico", id)
    const s = opcoes?.servicos.find((x) => x.id === id)
    if (s?.valor_cents && !valor.trim()) setValor(String(s.valor_cents / 100))
  }

  return (
    <>
      <Dialog open={!!card} onOpenChange={(v) => !v && onFechar()}>
        <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-6xl">
          <DialogHeader>
            <DialogTitle>{card?.nome}</DialogTitle>
            <DialogDescription>
              {[
                card?.cnpj && `CNPJ ${cnpjFmt(card.cnpj)}`,
                card?.cidade,
                card?.numero && `número ${card.numero}`,
                foneFmt(ficha?.telefone),
              ]
                .filter(Boolean)
                .join(" · ")}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
            {/* Esquerda: o que muda à mão + empresa */}
            <div className="grid content-start gap-3">
              <div className="grid grid-cols-2 gap-3">
                <Campo id="etapa" label="Etapa">
                  <select
                    id="etapa"
                    className={selectCls}
                    value={f.etapa ?? ""}
                    onChange={(e) => set("etapa", e.target.value)}
                  >
                    {opcoes?.etapas.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.nome}
                      </option>
                    ))}
                  </select>
                </Campo>
                <Campo id="resp" label="Responsável">
                  <select
                    id="resp"
                    className={selectCls}
                    value={f.responsavel_id ?? ""}
                    onChange={(e) =>
                      set("responsavel_id", e.target.value || null)
                    }
                  >
                    <option value="">Ninguém</option>
                    {opcoes?.responsaveis.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.nome}
                      </option>
                    ))}
                  </select>
                </Campo>
              </div>
              {f.etapa === "perdido" && (
                <Campo id="motivo" label="Motivo da perda">
                  <select
                    id="motivo"
                    className={cn(
                      selectCls,
                      !f.perdido_motivo && "border-destructive",
                    )}
                    value={f.perdido_motivo ?? ""}
                    onChange={(e) => set("perdido_motivo", e.target.value)}
                  >
                    <option value="">Escolha…</option>
                    {opcoes?.motivos.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </Campo>
              )}
              <div className="grid grid-cols-2 gap-3">
                <Campo id="servico" label="Serviço">
                  <select
                    id="servico"
                    className={selectCls}
                    value={f.servico ?? ""}
                    onChange={(e) => escolherServico(e.target.value)}
                  >
                    <option value="">Não definido</option>
                    {opcoes?.servicos.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.nome}
                      </option>
                    ))}
                  </select>
                </Campo>
                <Campo id="valor" label="Valor (R$)">
                  <Input
                    id="valor"
                    inputMode="decimal"
                    placeholder="ex.: 1.700"
                    value={valor}
                    onChange={(e) => setValor(e.target.value)}
                  />
                </Campo>
              </div>
              <Campo id="acao" label="Próxima ação">
                <Input
                  id="acao"
                  placeholder="ex.: Ligar para a sócia"
                  value={f.proxima_acao ?? ""}
                  onChange={(e) => set("proxima_acao", e.target.value)}
                />
              </Campo>
              <Campo id="acao-em" label="Quando">
                <Input
                  id="acao-em"
                  type="datetime-local"
                  value={paraInput(f.proxima_acao_em)}
                  onChange={(e) =>
                    set("proxima_acao_em", deInput(e.target.value))
                  }
                />
              </Campo>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={onFechar}>
                  Fechar
                </Button>
                <Button
                  disabled={
                    salvar.isPending ||
                    (f.etapa === "perdido" && !f.perdido_motivo)
                  }
                  onClick={() => salvar.mutate()}
                >
                  {salvar.isPending ? "Salvando…" : "Salvar"}
                </Button>
              </div>

              {card?.cnpj && (
                <div className="mt-2 grid gap-1 rounded-lg border p-3 text-sm">
                  <div className="font-semibold">Empresa (Receita)</div>
                  {empresa ? (
                    <>
                      <Linha rotulo="Decisor" valor={empresa.decisor} />
                      <Linha
                        rotulo="Porte"
                        valor={[
                          empresa.porte,
                          empresa.anos != null && `${empresa.anos} anos`,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      />
                      <Linha
                        rotulo="Capital"
                        valor={reais(Math.round(empresa.capital_social * 100))}
                      />
                      <Linha rotulo="Atividade" valor={empresa.atividade} />
                      {!!empresa.motivos.length && (
                        <Linha
                          rotulo={`Nota ${empresa.nota}`}
                          valor={empresa.motivos.join(", ")}
                        />
                      )}
                      <Button
                        variant="link"
                        className="h-auto justify-start p-0"
                        onClick={() => setReceitaAberta(true)}
                      >
                        Ver ficha completa e sócios
                      </Button>
                    </>
                  ) : (
                    <Skeleton className="h-16 w-full" />
                  )}
                </div>
              )}
            </div>

            {/* Direita: conversa */}
            <div className="grid content-start gap-3">
              <div className="flex items-baseline justify-between">
                <h3 className="font-semibold">
                  Conversa{card?.numero ? ` · número ${card.numero}` : ""}
                </h3>
                <span className="text-muted-foreground text-xs">
                  só leitura por enquanto
                </span>
              </div>
              <Conversa ficha={ficha} carregando={isLoading} />
              {ficha?.resumo && (
                <div className="rounded-lg border bg-muted/50 p-3 text-sm">
                  <div className="mb-1 font-semibold">Resumo da IA</div>
                  <p className="whitespace-pre-line">{ficha.resumo}</p>
                </div>
              )}
            </div>
          </div>

          {/* Embaixo: notas e histórico */}
          <div className="grid gap-6 border-t pt-4 md:grid-cols-2">
            <div className="grid content-start gap-2">
              <h3 className="font-semibold">Notas</h3>
              <form
                className="grid gap-2"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (nota.trim()) anotar.mutate()
                }}
              >
                <textarea
                  className="min-h-16 rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-input/30"
                  placeholder="Escreva uma nota sobre o lead"
                  value={nota}
                  onChange={(e) => setNota(e.target.value)}
                />
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  className="justify-self-end"
                  disabled={!nota.trim() || anotar.isPending}
                >
                  Adicionar nota
                </Button>
              </form>
              {ficha?.notas.map((n) => (
                <div key={n.id} className="rounded-md border p-2 text-sm">
                  <div className="text-muted-foreground text-xs">
                    {n.autor} · {dataHora(n.criado_em)}
                  </div>
                  <p className="whitespace-pre-line">{n.texto}</p>
                </div>
              ))}
            </div>
            <div className="grid content-start gap-2">
              <h3 className="font-semibold">Histórico</h3>
              {ficha?.historico.length ? (
                <ul className="grid gap-1 text-sm">
                  {[...ficha.historico].reverse().map((h) => (
                    <li key={h.criado_em + h.para}>
                      <span className="text-muted-foreground tabular-nums">
                        {dataHora(h.criado_em)}
                      </span>{" "}
                      ·{" "}
                      {h.de
                        ? `${NOME_ETAPA(opcoes, h.de)} → ${NOME_ETAPA(opcoes, h.para)}`
                        : `Entrou em ${NOME_ETAPA(opcoes, h.para)}`}{" "}
                      <span className="text-muted-foreground">({h.autor})</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm">
                  Sem mudanças de etapa ainda.
                </p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
      <Ficha
        cnpj={receitaAberta ? (card?.cnpj ?? null) : null}
        oferta="geral"
        onClose={() => setReceitaAberta(false)}
      />
    </>
  )
}

function Campo({
  id,
  label,
  children,
}: {
  id: string
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  )
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  if (!valor) return null
  return (
    <div>
      <span className="text-muted-foreground">{rotulo}: </span>
      {valor}
    </div>
  )
}

function Conversa({
  ficha,
  carregando,
}: {
  ficha: CardFicha | undefined
  carregando: boolean
}) {
  const fim = useRef<HTMLDivElement>(null)
  // rola para a mensagem mais nova quando a conversa chega
  const total = ficha?.mensagens.length ?? 0
  useEffect(() => {
    if (total) fim.current?.scrollIntoView({ block: "end" })
  }, [total])

  if (carregando) return <Skeleton className="h-[420px] w-full rounded-lg" />
  if (!ficha?.conversa_disponivel)
    return (
      <p className="rounded-lg border p-4 text-muted-foreground text-sm">
        Não consegui ler a conversa agora (banco do agente fora do ar ou não
        ligado).
      </p>
    )
  if (!ficha.mensagens.length)
    return (
      <p className="rounded-lg border p-4 text-muted-foreground text-sm">
        Ainda não há mensagens com este lead.
      </p>
    )
  return (
    <div className="grid max-h-[420px] content-start gap-2 overflow-y-auto rounded-lg border bg-muted/30 p-3">
      {ficha.mensagens.map((m) => {
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
  )
}
