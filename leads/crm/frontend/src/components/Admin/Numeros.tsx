import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus } from "lucide-react"
import { useState } from "react"

import { LeadsService, type Numero, type NumeroDados } from "@/client"
import { Badge } from "@/components/ui/badge"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"

const UFS = [
  "AC",
  "AL",
  "AM",
  "AP",
  "BA",
  "CE",
  "DF",
  "ES",
  "GO",
  "MA",
  "MG",
  "MS",
  "MT",
  "PA",
  "PB",
  "PE",
  "PI",
  "PR",
  "RJ",
  "RN",
  "RO",
  "RR",
  "RS",
  "SC",
  "SE",
  "SP",
  "TO",
]

const vazio: NumeroDados = {
  instancia: "",
  numero: "",
  responsavel: "",
  aviso: "",
  cidade: "",
  ativo: true,
  ufs: [],
}

/** 5541991348881 vira (41) 99134-8881 */
function fone(v: string) {
  const d = v.replace(/\D/g, "").replace(/^55/, "")
  if (d.length < 10) return v
  return `(${d.slice(0, 2)}) ${d.slice(2, -4)}-${d.slice(-4)}`
}

function Formulario({
  inicial,
  novo,
  onFechar,
}: {
  inicial: NumeroDados
  novo: boolean
  onFechar: () => void
}) {
  const [d, setD] = useState<NumeroDados>(inicial)
  const set = <K extends keyof NumeroDados>(k: K, v: NumeroDados[K]) =>
    setD((atual) => ({ ...atual, [k]: v }))
  const ufs = d.ufs ?? []
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const qc = useQueryClient()

  const salvar = useMutation({
    mutationFn: () =>
      novo
        ? LeadsService.criarNumero({ requestBody: d })
        : LeadsService.alterarNumero({
            instancia: d.instancia,
            requestBody: d,
          }),
    onSuccess: () => {
      showSuccessToast(novo ? "Número cadastrado." : "Número salvo.")
      qc.invalidateQueries({ queryKey: ["numeros"] })
      onFechar()
    },
    onError: (e: unknown) => {
      const detalhe = (e as { body?: { detail?: unknown } })?.body?.detail
      showErrorToast(
        typeof detalhe === "string" ? detalhe : "Não foi possível salvar.",
      )
    },
  })

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        salvar.mutate()
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label htmlFor="n-instancia">Instância na Evolution</Label>
          <Input
            id="n-instancia"
            value={d.instancia}
            disabled={!novo}
            placeholder="ex.: Weap-8526-1094"
            onChange={(e) => set("instancia", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="n-numero">Número do WhatsApp</Label>
          <Input
            id="n-numero"
            value={d.numero ?? ""}
            placeholder="41 98526-1094"
            onChange={(e) => set("numero", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="n-resp">Responsável</Label>
          <Input
            id="n-resp"
            value={d.responsavel}
            onChange={(e) => set("responsavel", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="n-aviso">Celular de aviso (lead interessado)</Label>
          <Input
            id="n-aviso"
            value={d.aviso}
            placeholder="41 99134-8881"
            onChange={(e) => set("aviso", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="n-cidade">Cidade</Label>
          <Input
            id="n-cidade"
            value={d.cidade ?? ""}
            onChange={(e) => set("cidade", e.target.value)}
          />
        </div>
        <div className="flex items-end gap-2 pb-2">
          <Checkbox
            id="n-ativo"
            checked={d.ativo ?? true}
            onCheckedChange={(v) => set("ativo", v === true)}
          />
          <Label htmlFor="n-ativo" className="font-normal">
            Ligado (dispara e recebe leads)
          </Label>
        </div>
      </div>
      <div className="grid gap-2">
        <Label>
          Estados que atende{" "}
          <span className="font-normal text-muted-foreground">
            (nenhum marcado = atende os estados que não são de outro número)
          </span>
        </Label>
        <div className="grid grid-cols-6 gap-x-3 gap-y-2 sm:grid-cols-9">
          {UFS.map((u) => (
            <div key={u} className="flex items-center gap-1.5">
              <Checkbox
                id={`n-uf-${u}`}
                checked={ufs.includes(u)}
                onCheckedChange={(v) =>
                  set(
                    "ufs",
                    v === true ? [...ufs, u] : ufs.filter((x) => x !== u),
                  )
                }
              />
              <Label htmlFor={`n-uf-${u}`} className="font-normal">
                {u}
              </Label>
            </div>
          ))}
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onFechar}>
          Cancelar
        </Button>
        <Button type="submit" disabled={salvar.isPending}>
          {salvar.isPending ? "Salvando…" : "Salvar"}
        </Button>
      </DialogFooter>
    </form>
  )
}

/** Números de WhatsApp do disparo: estados, responsável, celular de aviso e ligado/desligado. */
export function Numeros() {
  const { data: numeros, isLoading } = useQuery({
    queryKey: ["numeros"],
    queryFn: () => LeadsService.numeros(),
  })
  const [editando, setEditando] = useState<{
    dados: NumeroDados
    novo: boolean
  } | null>(null)

  const editar = (n: Numero) =>
    setEditando({
      novo: false,
      dados: {
        instancia: n.instancia,
        numero: n.numero,
        responsavel: n.responsavel,
        aviso: n.aviso ?? "",
        cidade: n.cidade ?? "",
        ativo: n.ativo,
        ufs: n.ufs,
      },
    })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">
            Números de WhatsApp
          </h2>
          <p className="text-muted-foreground">
            Quem dispara para cada estado e quem recebe o aviso de lead
            interessado
          </p>
        </div>
        {numeros && (
          <Button onClick={() => setEditando({ dados: vazio, novo: true })}>
            <Plus /> Adicionar número
          </Button>
        )}
      </div>
      {isLoading ? null : numeros === null || numeros === undefined ? (
        <p className="text-sm text-muted-foreground">
          O CRM ainda não está ligado ao banco do disparo.
        </p>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Instância</TableHead>
                <TableHead>Número</TableHead>
                <TableHead>Responsável</TableHead>
                <TableHead>Aviso</TableHead>
                <TableHead>Estados</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {numeros.map((n) => (
                <TableRow key={n.instancia}>
                  <TableCell className="font-medium">{n.instancia}</TableCell>
                  <TableCell>{fone(n.numero)}</TableCell>
                  <TableCell>{n.responsavel}</TableCell>
                  <TableCell>{fone(n.aviso ?? "")}</TableCell>
                  <TableCell>
                    {n.ufs.length ? (
                      n.ufs.join(", ")
                    ) : (
                      <span className="text-muted-foreground">
                        demais estados
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={n.ativo ? "default" : "secondary"}>
                      {n.ativo ? "Ligado" : "Desligado"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Editar ${n.instancia}`}
                      onClick={() => editar(n)}
                    >
                      <Pencil />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <Dialog
        open={editando !== null}
        onOpenChange={(v) => !v && setEditando(null)}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editando?.novo ? "Adicionar número" : "Editar número"}
            </DialogTitle>
            <DialogDescription>
              Mudanças valem no próximo lead que o número tirar da fila.
            </DialogDescription>
          </DialogHeader>
          {editando && (
            <Formulario
              key={editando.dados.instancia || "novo"}
              inicial={editando.dados}
              novo={editando.novo}
              onFechar={() => setEditando(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
