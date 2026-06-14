# ==============================================================================
# Dockerfile para Implantação do Backend FastAPI no Railway
# ==============================================================================

# Imagem base oficial do Python slim para garantir um container leve (~150MB) e seguro.
FROM python:3.11-slim

# Define a variável de ambiente para desativar o buffer de logs e printar no terminal imediatamente.
ENV PYTHONUNBUFFERED=1

# Define a variável de ambiente informando ao FastAPI e outros serviços o modo de execução de produção.
ENV ENVIRONMENT=production

# Define o diretório de trabalho principal dentro do container Linux.
WORKDIR /app

# Instala o compilador gcc, dependências de compilação C e curl para validação de saúde do container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o arquivo de requerimentos para cachear a camada de dependências do pip.
COPY api/requirements.txt /app/api/requirements.txt

# Instala as dependências Python compilando pacotes se necessário.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/api/requirements.txt

# Copia todo o código-fonte do backend da pasta local api/ para a pasta /app/api no container.
COPY api/ /app/api/
COPY data/ /app/data/

# Define o PYTHONPATH para garantir que o FastAPI resolva os módulos relativos do pacote corretamente.
ENV PYTHONPATH=/app

# Expoe a porta padrão 8000 na qual o servidor ASGI Uvicorn escutará.
EXPOSE 8000

# Executa um teste de saúde a cada 30 segundos utilizando curl para validar que a rota HTTP retorna status 200.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão para iniciar o Uvicorn. Em ambientes de container no Railway, roda com um único worker.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
