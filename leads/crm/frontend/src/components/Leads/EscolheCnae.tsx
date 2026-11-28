import { X } from "lucide-react"
import { useId, useState } from "react"

import type { Opcao } from "@/client"
import { Input } from "@/components/ui/input"

type Props = {
  id: string
  cnaes: Opcao[]
  valor: string[]
  onChange: (v: string[]) => void
}

/** Escolhe uma ou mais atividades (CNAE): pela lista ou digitando o código (4781-4/00 ou 4781400). */
export function EscolheCnae({ id, cnaes, valor, onChange }: Props) {
  const [texto, setTexto] = useState("")
  const lista = useId()
  const nome = (c: string) => cnaes.find((x) => x.id === c)?.nome ?? c
  const add = (v: string) => {
    const achado = cnaes.find((c) => c.nome === v)
    const digitos = v.replace(/\D/g, "")
    const c =
      achado?.id ??
      (digitos.length === 7 && /^[\d\s./-]+$/.test(v.trim()) ? digitos : "")
    if (!c) return false
    if (!valor.includes(c)) onChange([...valor, c])
    setTexto("")
    return true
  }

  return (
    <>
      <Input
        id={id}
        list={lista}
        value={texto}
        placeholder="digite o código ou parte do nome e escolha"
        onChange={(e) => {
          // escolher na lista já adiciona
          if (!add(e.target.value)) setTexto(e.target.value)
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && texto) {
            e.preventDefault()
            add(texto)
          }
        }}
      />
      <datalist id={lista}>
        {cnaes.map((c) => (
          <option key={c.id} value={c.nome} />
        ))}
      </datalist>
      {valor.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {valor.map((c) => (
            <span
              key={c}
              className="inline-flex max-w-full items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs"
            >
              <span className="truncate">{nome(c)}</span>
              <button
                type="button"
                aria-label={`Tirar ${c}`}
                className="text-muted-foreground hover:text-foreground"
                onClick={() => onChange(valor.filter((x) => x !== c))}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </>
  )
}
