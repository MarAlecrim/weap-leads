import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { LeadsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/clientes")({
  component: Clientes,
  head: () => ({ meta: [{ title: "Clientes atuais - Weap" }] }),
})

const moeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
})

function Clientes() {
  const { data, isLoading } = useQuery({
    queryKey: ["clientes"],
    queryFn: () => LeadsService.clientes(),
  })
  const { data: opcoes } = useQuery({
    queryKey: ["opcoes"],
    queryFn: () => LeadsService.opcoes(),
    staleTime: Number.POSITIVE_INFINITY,
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Clientes atuais</h1>
        <p className="text-muted-foreground">
          A base da nota: cada lead é comparado com o perfil destes clientes na
          Receita. Para mudar a lista, edite o arquivo
          leads/banco/04-clientes-atuais.sql.
        </p>
      </div>

      {opcoes && (
        <div className="rounded-lg border p-4 text-sm">
          <h2 className="mb-2 font-medium">Como a nota é calculada</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(opcoes.pesos).map(([k, v]) => (
              <Badge key={k} variant="outline">
                {opcoes.motivos[k]}: {v} pontos
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Cliente</TableHead>
              <TableHead>Comprou</TableHead>
              <TableHead className="hidden md:table-cell">Atividade</TableHead>
              <TableHead className="hidden lg:table-cell">Porte</TableHead>
              <TableHead className="hidden lg:table-cell">Anos</TableHead>
              <TableHead className="hidden md:table-cell">Cidade</TableHead>
              <TableHead className="hidden lg:table-cell">Sócios</TableHead>
              <TableHead className="text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={8}>Carregando…</TableCell>
              </TableRow>
            )}
            {data?.map((c) => (
              <TableRow key={c.nome}>
                <TableCell>
                  <div className="font-medium">{c.nome}</div>
                  {!c.ativo && <Badge variant="secondary">inativo</Badge>}
                  {!c.achou && (
                    <Badge variant="outline">não achado na Receita</Badge>
                  )}
                </TableCell>
                <TableCell>{c.ofertas.join(", ")}</TableCell>
                <TableCell className="hidden md:table-cell">
                  {c.atividade}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {c.porte}
                </TableCell>
                <TableCell className="hidden lg:table-cell">{c.anos}</TableCell>
                <TableCell className="hidden md:table-cell">
                  {c.cidade}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {c.achou ? c.socios : ""}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {c.valor ? moeda.format(c.valor) : ""}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
