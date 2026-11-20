FROM postgres:16
RUN apt-get update && apt-get install -y --no-install-recommends python3 curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY filtro.py importar.sh importar-simples.sh /importador/
RUN chmod +x /importador/importar.sh /importador/importar-simples.sh
ENTRYPOINT ["/importador/importar.sh"]
