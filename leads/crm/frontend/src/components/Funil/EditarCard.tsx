import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import {
  type Card,
  type FunilOpcoes,
  FunilService,
  type NegocioAtualiza,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { cnpjFmt, deInput, paraInput, selectCls } from "./util"

type Props = {
  card: Card | null
  /** etapa pedida ao arrastar para "Perdido": abre direto pedindo o motivo */
  etapaPedida?: string
  opcoes: FunilOpcoes | undefined
  onFechar: () => void
}

const erro = (e: unknown) =>
  (e as { body?: { detail?: string } })?.body?.detail ||
  "Não foi possível salvar."

/** Edita o card: etapa, serviço e valor, responsável, próxima ação e motivo da perda. */
export function EditarCard({ card, etapaPedida, opcoes, onFechar }: Props) {
  const [f, setF] = useState<NegocioAtualiza>({})
  const [valor, setValor] = useState("")
  const qc = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

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
  }, [card, etapaPedida])

  const salvar = useMutation({
    mutationFn: () => {
      if (!card) throw new Error()
      const cents = valor.trim()
        ? Math.round(Number(valor.replace(/\./g, "").replace(",", ".")) * 100)
        : null
      return FunilService.atualizar({
        negocioId: card.id,
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
      onFechar()
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
    <Dialog open={!!card} onOpenChange={(v) => !v && onFechar()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{card?.nome}</DialogTitle>
          <DialogDescription>
            {[
              card?.cnpj && `CNPJ ${cnpjFmt(card.cnpj)}`,
              card?.cidade,
              card?.numero,
            ]
              .filter(Boolean)
              .join(" · ")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="etapa">Etapa</Label>
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
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="resp">Responsável</Label>
            <select
              id="resp"
              className={selectCls}
              value={f.responsavel_id ?? ""}
              onChange={(e) => set("responsavel_id", e.target.value || null)}
            >
              <option value="">Ninguém</option>
              {opcoes?.responsaveis.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.nome}
                </option>
              ))}
            </select>
          </div>
          {f.etapa === "perdido" && (
            <div className="grid gap-1.5 sm:col-span-2">
              <Label htmlFor="motivo">Motivo da perda</Label>
              <select
                id="motivo"
                className={selectCls}
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
            </div>
          )}
          <div className="grid gap-1.5">
            <Label htmlFor="servico">Serviço</Label>
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
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="valor">Valor (R$)</Label>
            <Input
              id="valor"
              inputMode="decimal"
              placeholder="ex.: 1.700"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="acao">Próxima ação</Label>
            <Input
              id="acao"
              placeholder="ex.: Ligar para a sócia"
              value={f.proxima_acao ?? ""}
              onChange={(e) => set("proxima_acao", e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="acao-em">Quando</Label>
            <Input
              id="acao-em"
              type="datetime-local"
              value={paraInput(f.proxima_acao_em)}
              onChange={(e) => set("proxima_acao_em", deInput(e.target.value))}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onFechar}>
            Cancelar
          </Button>
          <Button
            disabled={
              salvar.isPending || (f.etapa === "perdido" && !f.perdido_motivo)
            }
            onClick={() => salvar.mutate()}
          >
            {salvar.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
