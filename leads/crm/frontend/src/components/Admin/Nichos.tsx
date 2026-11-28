import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { useState } from "react"

import { LeadsService, type Nicho } from "@/client"
import { EscolheCnae } from "@/components/Leads/EscolheCnae"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useCustomToast from "@/hooks/useCustomToast"

type Editando = { id: string | null; nome: string; cnaes: string[] }

function detalhe(e: unknown, padrao: string) {
  const d = (e as { body?: { detail?: unknown } })?.body?.detail
  return typeof d === "string" ? d : padrao
}

function Formulario({
  inicial,
  onFechar,
}: {
  inicial: Editando
  onFechar: () => void
}) {
  const [nome, setNome] = useState(inicial.nome)
  const [cnaes, setCnaes] = useState(inicial.cnaes)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const qc = useQueryClient()
  const { data: opcoes } = useQuery({
    queryKey: ["opcoes"],
    queryFn: () => LeadsService.opcoes(),
  })

  const salvar = useMutation({
    mutationFn: () =>
      inicial.id
        ? LeadsService.alterarNicho({
            nicho: inicial.id,
            requestBody: { nome, cnaes },
          })
        : LeadsService.criarNicho({ requestBody: { nome, cnaes } }),
    onSuccess: () => {
      showSuccessToast(inicial.id ? "Nicho salvo." : "Nicho criado.")
      qc.invalidateQueries({ queryKey: ["nichos"] })
      qc.invalidateQueries({ queryKey: ["opcoes"] })
      onFechar()
    },
    onError: (e: unknown) =>
      showErrorToast(detalhe(e, "Não foi possível salvar.")),
  })

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault()
        salvar.mutate()
      }}
    >
      <div className="grid gap-1.5">
        <Label htmlFor="nicho-nome">Nome do nicho</Label>
        <Input
          id="nicho-nome"
          value={nome}
          placeholder="ex.: Padaria e confeitaria"
          onChange={(e) => setNome(e.target.value)}
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="nicho-cnae">
          Atividades (CNAE) que entram no nicho
        </Label>
        <EscolheCnae
          id="nicho-cnae"
          cnaes={opcoes?.cnaes ?? []}
          valor={cnaes}
          onChange={setCnaes}
        />
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

/** Nichos da Busca de leads: nome e as atividades (CNAE) de cada um. */
export function Nichos() {
  const { data: nichos, isLoading } = useQuery({
    queryKey: ["nichos"],
    queryFn: () => LeadsService.nichos(),
  })
  const [editando, setEditando] = useState<Editando | null>(null)
  const [apagando, setApagando] = useState<Nicho | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const qc = useQueryClient()
  const apagar = useMutation({
    mutationFn: (n: Nicho) => LeadsService.apagarNicho({ nicho: n.id }),
    onSuccess: () => {
      showSuccessToast("Nicho apagado.")
      qc.invalidateQueries({ queryKey: ["nichos"] })
      qc.invalidateQueries({ queryKey: ["opcoes"] })
      setApagando(null)
    },
    onError: (e: unknown) =>
      showErrorToast(detalhe(e, "Não foi possível apagar.")),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Nichos da busca</h2>
          <p className="text-muted-foreground">
            Cada nicho junta as atividades (CNAE) que aparecem no filtro "Nicho"
            da Busca de leads
          </p>
        </div>
        <Button onClick={() => setEditando({ id: null, nome: "", cnaes: [] })}>
          <Plus /> Novo nicho
        </Button>
      </div>
      {isLoading ? null : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-56">Nicho</TableHead>
                <TableHead>Atividades</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(nichos ?? []).map((n) => (
                <TableRow key={n.id}>
                  <TableCell className="align-top font-medium">
                    {n.nome}
                  </TableCell>
                  <TableCell className="whitespace-normal text-sm text-muted-foreground">
                    {n.cnaes.map((c) => c.nome).join(" · ")}
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Editar ${n.nome}`}
                        onClick={() =>
                          setEditando({
                            id: n.id,
                            nome: n.nome,
                            cnaes: n.cnaes.map((c) => c.id),
                          })
                        }
                      >
                        <Pencil />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Apagar ${n.nome}`}
                        onClick={() => setApagando(n)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
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
              {editando?.id ? "Editar nicho" : "Novo nicho"}
            </DialogTitle>
            <DialogDescription>
              O nicho aparece na Busca de leads assim que for salvo.
            </DialogDescription>
          </DialogHeader>
          {editando && (
            <Formulario
              key={editando.id ?? "novo"}
              inicial={editando}
              onFechar={() => setEditando(null)}
            />
          )}
        </DialogContent>
      </Dialog>
      <Dialog
        open={apagando !== null}
        onOpenChange={(v) => !v && setApagando(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Apagar o nicho {apagando?.nome}?</DialogTitle>
            <DialogDescription>
              Ele sai da lista da Busca de leads. As empresas não mudam.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApagando(null)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              disabled={apagar.isPending}
              onClick={() => apagando && apagar.mutate(apagando)}
            >
              Apagar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
