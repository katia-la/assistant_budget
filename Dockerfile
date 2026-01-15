FROM python:3.12-slim

# 1. Installer uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 2. Dossier de travail
WORKDIR /app

# 3. Copier uniquement les fichiers de dépendances (cache Docker)
COPY pyproject.toml uv.lock ./

# 4. Installer les dépendances
RUN uv sync --frozen

# 5. Copier le projet dans une image
COPY . .

# 6. expose FastAPI port
EXPOSE 8000

# 7. run FastAPI app
CMD ["uv", "run", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0","--port", "8000"]
 

