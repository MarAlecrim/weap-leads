import { useQuery } from "@tanstack/react-query"
import { ExternalLink, MapPin, MessageCircle } from "lucide-react"

import { LeadsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { corDaNota } from "./api"

type Props = {
  cnpj: string | null
  oferta: string
  onClose: () => void
}

const moeda = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
})

function cnpjBonito(c: string) {
  return c.length === 14
    ? `${c.slice(0, 2)}.${c.slice(2, 5)}.${c.slice(5, 8)}/${c.slice(8, 12)}-${c.slice(12)}`
    : c
}

export function Ficha({ cnpj, oferta, onClose }: Props) {
  const { data: l, isLoading } = useQuery({
    queryKey: ["lead", cnpj, oferta],
    queryFn: () => LeadsService.ficha({ cnpj: cnpj!, oferta }),
    enabled: !!cnpj,
  })

  return (
    <Sheet open={!!cnpj} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        {isLoading || !l ? (
          <div className="grid gap-3 p-6">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <>
            <SheetHeader>
              <div className="flex items-start gap-3">
                <span
                  className={`rounded-md px-2 py-1 text-lg font-semibold tabular-nums ${corDaNota(l.nota)}`}
                >
                  {l.nota}
                </span>
                <div>
                  <SheetTitle>{l.nome}</SheetTitle>
                  <SheetDescription>
                    {l.razao_social} · CNPJ {cnpjBonito(l.cnpj)}
                  </SheetDescription>
                </div>
              </div>
            </SheetHeader>
            <div className="grid gap-5 px-4 pb-6 text-sm">
              {l.no_disparo && (
                <Badge variant="secondary" className="w-fit">
                  Já está no disparo
                </Badge>
              )}
              <section className="grid gap-1">
                <h3 className="font-medium">Por que essa nota</h3>
                {l.motivos.length ? (
                  <ul className="list-inside list-disc text-muted-foreground">
                    {l.motivos.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">
                    Não se parece com os clientes atuais.
                  </p>
                )}
              </section>
              <Separator />
              <section className="grid grid-cols-2 gap-x-4 gap-y-2">
                <Info rotulo="Atividade" valor={l.atividade} largo />
                <Info rotulo="Porte" valor={l.porte} />
                <Info
                  rotulo="Tempo de empresa"
                  valor={l.anos == null ? "" : `${l.anos} anos`}
                />
                <Info
                  rotulo="Capital social"
                  valor={moeda.format(l.capital_social)}
                />
                <Info rotulo="Sócios" valor={String(l.n_socios)} />
                <Info rotulo="Endereço" valor={l.endereco} largo />
                <Info rotulo="Telefone 1" valor={l.telefone1} />
                <Info rotulo="Telefone 2" valor={l.telefone2} />
                <Info rotulo="E-mail" valor={l.email} largo />
              </section>
              <div className="flex flex-wrap gap-3">
                {l.whatsapp && (
                  <a
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                    href={`https://wa.me/55${l.whatsapp}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <MessageCircle className="size-4" /> WhatsApp
                  </a>
                )}
                <a
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                  href={`https://www.google.com/maps/search/${encodeURIComponent(`${l.nome} ${l.endereco}`)}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <MapPin className="size-4" /> Google Maps
                </a>
              </div>
              <Separator />
              <section className="grid gap-2">
                <h3 className="font-medium">Sócios</h3>
                {l.socios.length === 0 && (
                  <p className="text-muted-foreground">
                    A Receita não lista sócios (empresário individual ou MEI: o
                    dono é o próprio titular).
                  </p>
                )}
                {l.socios.map((s) => (
                  <div
                    key={`${s.nome}-${s.desde}`}
                    className="flex items-start justify-between gap-3 rounded-md border p-3"
                  >
                    <div>
                      <div className="font-medium">
                        {s.nome}
                        {s.nome === l.decisor && (
                          <Badge className="ml-2">Decisor</Badge>
                        )}
                      </div>
                      <div className="text-muted-foreground">
                        {s.qualificacao}
                        {s.desde
                          ? ` · desde ${new Date(s.desde).getFullYear()}`
                          : ""}
                      </div>
                    </div>
                    {s.pessoa_fisica && (
                      <a
                        className="inline-flex shrink-0 items-center gap-1 text-primary hover:underline"
                        href={`https://www.google.com/search?q=${encodeURIComponent(`"${s.nome}" ${l.nome} site:linkedin.com`)}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        LinkedIn <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                ))}
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function Info({
  rotulo,
  valor,
  largo,
}: {
  rotulo: string
  valor: string
  largo?: boolean
}) {
  if (!valor) return null
  return (
    <div className={largo ? "col-span-2" : ""}>
      <div className="text-xs text-muted-foreground">{rotulo}</div>
      <div>{valor}</div>
    </div>
  )
}
