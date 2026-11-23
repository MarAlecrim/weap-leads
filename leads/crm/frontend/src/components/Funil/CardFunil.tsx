import type { Card } from "@/client"
import { cn } from "@/lib/utils"
import { DIAS_ALERTA, dias, ORIGENS, quando, reais } from "./util"

type Props = {
  card: Card
  onAbrir: (c: Card) => void
}

/** Um card do kanban. Arrasta para mudar de etapa, clica para editar. */
export function CardFunil({ card, onAbrir }: Props) {
  const semResposta = card.dias_sem_resposta ?? 0
  const vencida =
    card.proxima_acao_em && new Date(card.proxima_acao_em) < new Date()
  return (
    <button
      type="button"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", String(card.id))
        e.dataTransfer.effectAllowed = "move"
      }}
      onClick={() => onAbrir(card)}
      className={cn(
        "w-full cursor-grab rounded-lg border bg-card p-3 text-left text-sm shadow-xs transition hover:border-primary/60 active:cursor-grabbing",
        card.ia_pausada && "border-amber-500/60",
      )}
    >
      <div className="truncate font-semibold" title={card.nome}>
        {card.nome}
      </div>
      <div className="mt-0.5 flex flex-wrap gap-x-1.5 text-xs">
        {card.valor_cents ? (
          <span className="font-medium">{reais(card.valor_cents)}</span>
        ) : (
          <span className="text-muted-foreground">sem valor</span>
        )}
        {card.nota != null && (
          <span className="text-muted-foreground">· nota {card.nota}</span>
        )}
      </div>
      <div className="mt-1 truncate text-muted-foreground text-xs">
        {[card.responsavel ?? "sem responsável", card.numero]
          .filter(Boolean)
          .join(" · ")}
      </div>
      <div className="truncate text-muted-foreground text-xs">
        {dias(card.dias_na_etapa)} na etapa ·{" "}
        {[ORIGENS[card.origem] ?? card.origem, card.cidade]
          .filter(Boolean)
          .join(" · ")}
      </div>
      {semResposta >= DIAS_ALERTA && (
        <div className="mt-1 font-semibold text-destructive text-xs">
          Sem resposta: {dias(semResposta)}
        </div>
      )}
      {card.ia_pausada && (
        <div className="mt-1 font-semibold text-amber-600 text-xs dark:text-amber-400">
          Com pessoa, IA pausada
        </div>
      )}
      {card.proxima_acao && (
        <div
          className={cn(
            "mt-1 truncate font-semibold text-xs",
            vencida && "text-destructive",
          )}
          title={card.proxima_acao}
        >
          {card.proxima_acao}
          {card.proxima_acao_em ? ` · ${quando(card.proxima_acao_em)}` : ""}
        </div>
      )}
      {card.etapa === "perdido" && card.perdido_motivo && (
        <div className="mt-1 text-muted-foreground text-xs">
          {card.perdido_motivo}
        </div>
      )}
    </button>
  )
}
