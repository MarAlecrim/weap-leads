import { AxiosError } from "axios"
import type { ApiError } from "./client"

function extractErrorMessage(err: ApiError): string {
  if (err instanceof AxiosError) {
    return err.message
  }

  const errDetail = (err.body as any)?.detail
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    return errDetail[0].msg
  }
  return errDetail || "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: ApiError,
) {
  const errorMessage = extractErrorMessage(err)
  this(errorMessage)
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}

export const validarCNPJ = (cnpj: string): boolean => {
  const cleanedCnpj = cnpj.replace(/\D/g, "")

  if (cleanedCnpj.length !== 14) return false
  if (/^(\d)\1+$/.test(cleanedCnpj)) return false

  const calcDV = (base: string, pesos: number[]) => {
    const soma = base
      .split("")
      .reduce((acc, num, i) => acc + Number(num) * pesos[i], 0)

    const resto = soma % 11
    return resto < 2 ? 0 : 11 - resto
  }

  const base = cleanedCnpj.slice(0, 12)

  const dv1 = calcDV(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
  const dv2 = calcDV(base + dv1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])

  return cleanedCnpj === base + dv1.toString() + dv2.toString()
}

export const formatCNPJ = (value?: string | null) => {
  if (!value) return ""

  const cleaned = value.replace(/\D/g, "")

  return cleaned
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2")
}
