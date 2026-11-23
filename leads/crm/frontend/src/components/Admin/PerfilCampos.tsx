import { useQuery } from "@tanstack/react-query"
import type { Control, FieldValues, Path } from "react-hook-form"

import { FunilService } from "@/client"
import { Checkbox } from "@/components/ui/checkbox"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"

export const PERFIS = [
  { id: "admin", nome: "Administrador", desc: "vê e configura tudo" },
  { id: "gestor", nome: "Gestor", desc: "vê todos os leads e conversas" },
  { id: "vendedor", nome: "Vendedor", desc: "vê só os leads dos seus números" },
]

export const nomeDoPerfil = (id: string | undefined) =>
  PERFIS.find((p) => p.id === id)?.nome ?? "Vendedor"

const selectCls =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-input/30"

/** Perfil (admin, gestor, vendedor) e os números de WhatsApp do usuário, no cadastro do Admin. */
export function PerfilCampos<T extends FieldValues>({
  control,
}: {
  control: Control<T>
}) {
  const { data } = useQuery({
    queryKey: ["funil-opcoes"],
    queryFn: () => FunilService.opcoes(),
    staleTime: 60_000,
  })
  const numeros = data?.numeros ?? []

  return (
    <>
      <FormField
        control={control}
        name={"perfil" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Perfil</FormLabel>
            <FormControl>
              <select
                className={selectCls}
                value={field.value ?? "vendedor"}
                onChange={(e) => field.onChange(e.target.value)}
              >
                {PERFIS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}: {p.desc}
                  </option>
                ))}
              </select>
            </FormControl>
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name={"numeros" as Path<T>}
        render={({ field }) => {
          const marcados: string[] = field.value ?? []
          return (
            <FormItem>
              <FormLabel>Números de WhatsApp</FormLabel>
              <div className="grid gap-2">
                {numeros.map((n) => (
                  <label
                    key={n.id}
                    className="flex items-center gap-2 text-sm"
                    title={n.id}
                    htmlFor={`numero-${n.id}`}
                  >
                    <Checkbox
                      id={`numero-${n.id}`}
                      checked={marcados.includes(n.id)}
                      onCheckedChange={(v) =>
                        field.onChange(
                          v
                            ? [...marcados, n.id]
                            : marcados.filter((x) => x !== n.id),
                        )
                      }
                    />
                    {n.nome}
                  </label>
                ))}
                {!numeros.length && (
                  <p className="text-muted-foreground text-sm">
                    Nenhum número encontrado no banco do agente.
                  </p>
                )}
              </div>
              <p className="text-muted-foreground text-xs">
                Os leads destes números ficam com esta pessoa. O vendedor vê só
                eles e os que forem passados para ele.
              </p>
            </FormItem>
          )
        }}
      />
    </>
  )
}
