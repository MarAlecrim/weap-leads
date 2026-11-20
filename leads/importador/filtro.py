#!/usr/bin/env python3
"""Lê os .zip da Receita (CNPJ dados abertos), filtra e devolve CSV limpo em UTF-8 para o \\copy do psql.

Uso:  filtro.py <tipo> <pasta_dos_zips>
tipo: estabelecimentos | empresas | socios | simples | cnaes | municipios | qualificacoes | naturezas

Variáveis: RECEITA_UFS="PR,SP" (padrão PR). O passo "estabelecimentos" grava basicos.txt na pasta,
que os passos "empresas" e "socios" usam para guardar só as empresas que interessam.
"""
import csv, io, os, sys, zipfile, glob, datetime

TIPO, PASTA = sys.argv[1], sys.argv[2]
UFS = {u.strip().upper() for u in os.environ.get("RECEITA_UFS", "PR").split(",") if u.strip()}
MES = os.environ.get("RECEITA_MES", datetime.date.today().strftime("%Y-%m")) + "-01"
PREFIXO = {"estabelecimentos": "Estabelecimentos", "empresas": "Empresas", "socios": "Socios", "simples": "Simples",
           "cnaes": "Cnaes", "municipios": "Municipios", "qualificacoes": "Qualificacoes",
           "naturezas": "Naturezas"}[TIPO]
out = csv.writer(sys.stdout, lineterminator="\n")


def linhas():
    arquivos = sorted(glob.glob(os.path.join(PASTA, PREFIXO + "*.zip")))
    if not arquivos:
        sys.exit(f"Nenhum {PREFIXO}*.zip em {PASTA}")
    for arq in arquivos:
        with zipfile.ZipFile(arq) as z:
            for nome in z.namelist():
                with z.open(nome) as f:
                    texto = io.TextIOWrapper(f, encoding="latin-1", newline="")
                    yield from csv.reader(texto, delimiter=";", quotechar='"')


def data(v):
    v = (v or "").strip()
    if len(v) != 8 or v == "00000000":
        return ""
    try:
        return datetime.date(int(v[:4]), int(v[4:6]), int(v[6:])).isoformat()
    except ValueError:
        return ""


def fone(ddd, num):
    d = "".join(c for c in (ddd or "") if c.isdigit())
    n = "".join(c for c in (num or "") if c.isdigit())
    d = d.lstrip("0")
    if len(d) != 2 or len(n) < 8 or not n.strip("0"):
        return ""
    if len(n) == 8 and n[0] in "6789":   # celular no formato antigo, sem o 9
        n = "9" + n
    return d + n


def ordena_fones(a, b):
    # celular primeiro
    cel = lambda t: len(t) == 11 and t[2] == "9"
    return (b, a) if (not cel(a) and cel(b)) else (a, b)


def limpa(v):
    return (v or "").strip().replace("\x00", "")


def basicos():
    with open(os.path.join(PASTA, "basicos.txt")) as f:
        return {l.strip() for l in f if l.strip()}


if TIPO == "estabelecimentos":
    vistos = set()
    for r in linhas():
        if len(r) < 28 or r[19].upper() not in UFS or r[5] != "02":   # 02 = ATIVA
            continue
        cnpj = r[0] + r[1] + r[2]
        if cnpj in vistos:
            continue
        vistos.add(cnpj)
        sec = [c for c in (r[12] or "").split(",") if c.strip()]
        out.writerow([cnpj, r[0], r[3] == "1", limpa(r[4]), data(r[10]), r[11],
                      "{" + ",".join(sec) + "}",
                      limpa((r[13] + " " + r[14]).strip()), limpa(r[15]), limpa(r[16]), limpa(r[17]),
                      limpa(r[18]), r[19].upper(), r[20],
                      *ordena_fones(fone(r[21], r[22]), fone(r[23], r[24])), limpa(r[27]).lower(), MES])
    with open(os.path.join(PASTA, "basicos.txt"), "w") as f:
        f.write("\n".join(sorted({c[:8] for c in vistos})))

elif TIPO == "empresas":
    ok = basicos()
    for r in linhas():
        if len(r) >= 6 and r[0] in ok:
            ok.discard(r[0])  # a Receita repete algumas empresas
            out.writerow([r[0], limpa(r[1]), r[2], (r[4] or "0").replace(".", "").replace(",", "."), r[5]])

elif TIPO == "socios":
    ok = basicos()
    for r in linhas():
        if len(r) >= 11 and r[0] in ok:
            # r[3] (CPF/CNPJ do sócio) é ignorado de propósito
            out.writerow([r[0], r[1], limpa(r[2]), r[4], data(r[5]), r[10]])

elif TIPO == "simples":
    # cnpj_basico; opção Simples (S/N); datas; opção MEI (S/N); datas. Só quem tem opção vigente.
    ok = basicos()
    for r in linhas():
        if len(r) >= 7 and r[0] in ok:
            ok.discard(r[0])
            out.writerow([r[0], r[1].strip().upper() == "S", r[4].strip().upper() == "S"])

else:  # tabelas de apoio: código;descrição
    for r in linhas():
        if len(r) >= 2:
            out.writerow([r[0].strip(), limpa(r[1])])
