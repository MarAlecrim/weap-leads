import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const icone = (
    <span
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground",
        className,
      )}
    >
      W
    </span>
  )
  const nome = (
    <span className="text-lg font-semibold tracking-tight">
      Weap <span className="text-primary">Leads</span>
    </span>
  )

  const content =
    variant === "icon" ? (
      icone
    ) : variant === "responsive" ? (
      <span className="flex items-center gap-2">
        {icone}
        <span className="group-data-[collapsible=icon]:hidden">{nome}</span>
      </span>
    ) : (
      <span className="flex items-center gap-2">
        {icone}
        {nome}
      </span>
    )

  if (!asLink) return content
  return <Link to="/">{content}</Link>
}
