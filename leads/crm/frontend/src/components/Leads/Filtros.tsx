import type { Opcoes } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { type FiltrosBusca, filtrosPadrao } from "./api"

const selectCls =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-input/30"

type Props = {
  opcoes?: Opcoes
  valor: FiltrosBusca
  onChange: (f: FiltrosBusca) => void
  onBuscar: () => void
}

function Marca({
  id,
  label,
  checked,
  onChange,
}: {
  id: string
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <Checkbox
        id={id}
        checked={checked}
        onCheckedChange={(v) => onChange(v === true)}
      />
      <Label htmlFor={id} className="font-normal">
        {label}
      </Label>
    </div>
  )
}

export function Filtros({ opcoes, valor: f, onChange, onBuscar }: Props) {
  const set = <K extends keyof FiltrosBusca>(k: K, v: FiltrosBusca[K]) =>
    onChange({ ...f, [k]: v })
  const cidades = (opcoes?.cidades ?? []).filter((c) => !f.uf || c.uf === f.uf)
  const trocaEstado = (uf: string) => {
    const cidade = opcoes?.cidades.find((c) => c.id === f.cidade)
    // a cidade escolhida só fica se for do novo estado
    onChange({
      ...f,
      uf,
      cidade: !uf || cidade?.uf === uf ? f.cidade : "",
    })
  }

  return (
    <form
      className="grid gap-4 rounded-lg border p-4"
      onSubmit={(e) => {
        e.preventDefault()
        onBuscar()
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="grid gap-1.5">
          <Label htmlFor="oferta">Nota pensando em</Label>
          <select
            id="oferta"
            className={selectCls}
            value={f.oferta}
            onChange={(e) => set("oferta", e.target.value)}
          >
            {opcoes?.ofertas.map((o) => (
              <option key={o.id} value={o.id}>
                {o.nome}
                {o.clientes ? ` (${o.clientes} clientes)` : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="nicho">Nicho</Label>
          <select
            id="nicho"
            className={selectCls}
            value={f.nicho}
            onChange={(e) => set("nicho", e.target.value)}
          >
            <option value="">Todos</option>
            {opcoes?.nichos.map((n) => (
              <option key={n.id} value={n.id}>
                {n.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="uf">Estado</Label>
          <select
            id="uf"
            className={selectCls}
            value={f.uf}
            onChange={(e) => trocaEstado(e.target.value)}
          >
            <option value="">Todos</option>
            {opcoes?.ufs.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="cidade">Cidade</Label>
          <select
            id="cidade"
            className={selectCls}
            value={f.cidade}
            onChange={(e) => set("cidade", e.target.value)}
          >
            <option value="">Todas</option>
            {cidades.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="bairro">Bairro</Label>
          <Input
            id="bairro"
            value={f.bairro}
            onChange={(e) => set("bairro", e.target.value)}
            placeholder="ex.: Centro"
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="nome">Nome da empresa</Label>
          <Input
            id="nome"
            value={f.nome}
            onChange={(e) => set("nome", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5">
          <Label>Tempo de empresa (anos)</Label>
          <div className="flex gap-2">
            <Input
              type="number"
              min={0}
              placeholder="de"
              value={f.anos_min}
              onChange={(e) => set("anos_min", e.target.value)}
            />
            <Input
              type="number"
              min={0}
              placeholder="até"
              value={f.anos_max}
              onChange={(e) => set("anos_max", e.target.value)}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label>Capital social (R$)</Label>
          <div className="flex gap-2">
            <Input
              inputMode="numeric"
              placeholder="mínimo"
              value={f.capital_min}
              onChange={(e) => set("capital_min", e.target.value)}
            />
            <Input
              inputMode="numeric"
              placeholder="máximo"
              value={f.capital_max}
              onChange={(e) => set("capital_max", e.target.value)}
            />
          </div>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="nota_min">Nota mínima</Label>
          <Input
            id="nota_min"
            type="number"
            min={0}
            max={100}
            placeholder="0 a 100"
            value={f.nota_min}
            onChange={(e) => set("nota_min", e.target.value)}
          />
        </div>
        <div className="grid gap-1.5 sm:col-span-2">
          <Label>
            Porte{" "}
            <span className="font-normal text-muted-foreground">
              (média e grande separadas pelo capital de R$ 10 milhões)
            </span>
          </Label>
          <div className="flex flex-wrap gap-x-4 gap-y-2 pt-1">
            {opcoes?.portes
              .filter((p) => p.id !== "00")
              .map((p) => (
                <Marca
                  key={p.id}
                  id={`porte-${p.id}`}
                  label={p.nome}
                  checked={f.porte.includes(p.id)}
                  onChange={(v) =>
                    set(
                      "porte",
                      v
                        ? [...f.porte, p.id]
                        : f.porte.filter((x) => x !== p.id),
                    )
                  }
                />
              ))}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <Marca
          id="celular"
          label="Tem celular (WhatsApp)"
          checked={f.celular}
          onChange={(v) => set("celular", v)}
        />
        <Marca
          id="email"
          label="Tem e-mail"
          checked={f.email}
          onChange={(v) => set("email", v)}
        />
        <Marca
          id="socio"
          label="Tem sócio pessoa física"
          checked={f.socio}
          onChange={(v) => set("socio", v)}
        />
        <Marca
          id="secundario"
          label="Nicho também na atividade secundária"
          checked={f.secundario}
          onChange={(v) => set("secundario", v)}
        />
        <Marca
          id="esconder"
          label="Esconder quem já está no disparo"
          checked={f.esconder_disparo}
          onChange={(v) => set("esconder_disparo", v)}
        />
        <div className="ml-auto flex gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onChange(filtrosPadrao)}
          >
            Limpar
          </Button>
          <Button type="submit">Buscar</Button>
        </div>
      </div>
    </form>
  )
}
