import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Send } from "lucide-react"
import { useState } from "react"

import { LeadsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { type FiltrosBusca, filtrosDoPedido } from "./api"

const numero = new Intl.NumberFormat("pt-BR")

type Props = {
  filtros: FiltrosBusca
  marcados: string[]
  total: number
  onFeito: () => void
}

/** Botão e confirmação do "Mandar para o disparo": põe os leads na fila do n8n, sem planilha. */
export function MandarDisparo({ filtros, marcados, total, onFeito }: Props) {
  const [aberto, setAberto] = useState(false)
  const [quais, setQuais] = useState<"marcados" | "todos">("todos")
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const qc = useQueryClient()

  const mandar = useMutation({
    mutationFn: () =>
      LeadsService.mandarParaDisparo({
        requestBody: {
          filtros: filtrosDoPedido(filtros),
          cnpjs: quais === "marcados" ? marcados : [],
          pular_disparo: true,
        },
      }),
    onSuccess: (r) => {
      const partes = [`${numero.format(r.adicionados)} entraram na fila`]
      if (r.ja_no_disparo)
        partes.push(`${numero.format(r.ja_no_disparo)} já estavam no disparo`)
      if (r.sem_whatsapp)
        partes.push(`${numero.format(r.sem_whatsapp)} sem celular`)
      showSuccessToast(`${partes.join(", ")}.`)
      setAberto(false)
      onFeito()
      qc.invalidateQueries({ queryKey: ["leads"] })
      qc.invalidateQueries({ queryKey: ["fila"] })
    },
    onError: (e: unknown) => {
      const detalhe = (e as { body?: { detail?: string } })?.body?.detail
      showErrorToast(detalhe || "Não foi possível mandar para o disparo.")
    },
  })

  const abrir = () => {
    setQuais(marcados.length ? "marcados" : "todos")
    setAberto(true)
  }

  return (
    <>
      <Button disabled={!total} onClick={abrir}>
        <Send /> Mandar para o disparo
      </Button>
      <Dialog open={aberto} onOpenChange={setAberto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mandar para o disparo</DialogTitle>
            <DialogDescription>
              Os leads entram na fila do WhatsApp, da nota mais alta para a mais
              baixa, e os 5 números vão tirando um por vez. Quem já está no
              disparo ou não tem celular fica de fora.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <label className="flex items-center gap-2" htmlFor="quais-marcados">
              <input
                id="quais-marcados"
                type="radio"
                className="accent-primary"
                checked={quais === "marcados"}
                disabled={!marcados.length}
                onChange={() => setQuais("marcados")}
              />
              <Label htmlFor="quais-marcados" className="font-normal">
                Só os marcados ({numero.format(marcados.length)})
              </Label>
            </label>
            <label className="flex items-center gap-2" htmlFor="quais-todos">
              <input
                id="quais-todos"
                type="radio"
                className="accent-primary"
                checked={quais === "todos"}
                onChange={() => setQuais("todos")}
              />
              <Label htmlFor="quais-todos" className="font-normal">
                Todos do filtro, até 3.000 (
                {numero.format(Math.min(total, 3000))})
              </Label>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAberto(false)}>
              Cancelar
            </Button>
            <Button disabled={mandar.isPending} onClick={() => mandar.mutate()}>
              <Send /> {mandar.isPending ? "Mandando…" : "Mandar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
