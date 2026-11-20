FROM postgres:16
RUN apt-get update && apt-get install -y --no-install-recommends python3 curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY filtro.py importar.sh /importador/
RUN chmod +x /importador/importar.sh
ENTRYPOINT ["/importador/importar.sh"]
