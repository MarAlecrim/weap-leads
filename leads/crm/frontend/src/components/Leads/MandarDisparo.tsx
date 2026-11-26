import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Send } from "lucide-react"
import { useState } from "react"

import { LeadsService, type Numero } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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

/** "Weap-7533 · 7533 · Fabiano · SP" */
function descreve(n: Numero) {
  const final = n.numero.slice(-4)
  const partes = [n.instancia]
  if (final && !n.instancia.includes(final)) partes.push(final)
  if (n.responsavel) partes.push(n.responsavel)
  partes.push(n.ufs.length ? n.ufs.join(", ") : "demais estados")
  return partes.join(" · ")
}

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
  // quem dispara: automático pela regra de estados, ou só os números escolhidos
  const [modo, setModo] = useState<"auto" | "escolhidos">("auto")
  const [escolhidos, setEscolhidos] = useState<string[]>([])
  const { data: numeros } = useQuery({
    queryKey: ["numeros"],
    queryFn: () => LeadsService.numeros(),
  })
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const qc = useQueryClient()

  const mandar = useMutation({
    mutationFn: () =>
      LeadsService.mandarParaDisparo({
        requestBody: {
          filtros: filtrosDoPedido(filtros),
          cnpjs: quais === "marcados" ? marcados : [],
          pular_disparo: true,
          instancias: modo === "escolhidos" ? escolhidos : [],
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
    setModo("auto")
    // sugestão: os números que atendem o estado filtrado
    setEscolhidos(
      (numeros ?? [])
        .filter((n) => n.ativo && filtros.uf && n.ufs.includes(filtros.uf))
        .map((n) => n.instancia),
    )
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
              baixa, e os números vão tirando um por vez. Quem já está no
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
          {numeros && numeros.length > 0 && (
            <div className="grid gap-3 border-t pt-3">
              <p className="text-sm font-medium">Quem dispara</p>
              <label className="flex items-center gap-2" htmlFor="modo-auto">
                <input
                  id="modo-auto"
                  type="radio"
                  className="accent-primary"
                  checked={modo === "auto"}
                  onChange={() => setModo("auto")}
                />
                <Label htmlFor="modo-auto" className="font-normal">
                  Automático: cada número pega os leads dos estados dele
                </Label>
              </label>
              <label
                className="flex items-center gap-2"
                htmlFor="modo-escolhidos"
              >
                <input
                  id="modo-escolhidos"
                  type="radio"
                  className="accent-primary"
                  checked={modo === "escolhidos"}
                  onChange={() => setModo("escolhidos")}
                />
                <Label htmlFor="modo-escolhidos" className="font-normal">
                  Só estes números
                </Label>
              </label>
              {modo === "escolhidos" && (
                <div className="grid max-h-48 gap-2 overflow-y-auto pl-6">
                  {numeros.map((n) => (
                    <div key={n.instancia} className="flex items-center gap-2">
                      <Checkbox
                        id={`num-${n.instancia}`}
                        checked={escolhidos.includes(n.instancia)}
                        onCheckedChange={(v) =>
                          setEscolhidos((atual) =>
                            v === true
                              ? [...atual, n.instancia]
                              : atual.filter((x) => x !== n.instancia),
                          )
                        }
                      />
                      <Label
                        htmlFor={`num-${n.instancia}`}
                        className="font-normal"
                      >
                        {descreve(n)}
                        {!n.ativo &&
                          " · desligado (os leads esperam ele ligar)"}
                      </Label>
                    </div>
                  ))}
                  {!escolhidos.length && (
                    <p className="text-sm text-muted-foreground">
                      Marque pelo menos um número.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setAberto(false)}>
              Cancelar
            </Button>
            <Button
              disabled={
                mandar.isPending ||
                (modo === "escolhidos" && !escolhidos.length)
              }
              onClick={() => mandar.mutate()}
            >
              <Send /> {mandar.isPending ? "Mandando…" : "Mandar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
