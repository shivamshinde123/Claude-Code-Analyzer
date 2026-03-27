FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY src/ src/

EXPOSE 8000

CMD ["uv", "run", "python", "src/main.py"]
