FROM python:3.12-slim

# Lambda Web Adapter: forwards Lambda Function URL / API Gateway events to a
# normal HTTP server. When run outside Lambda (e.g. `docker run` locally),
# this extension is simply inert and the container behaves like a plain
# gunicorn server.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1 /lambda-adapter /opt/extensions/lambda-adapter
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /usr/local/bin/

WORKDIR /var/task

# uv.lock の断面通りに依存関係を再現する (--frozen: lockファイルを更新しない、--no-dev: pytest/ruff等は含めない)
ENV UV_PROJECT_ENVIRONMENT=/var/task/.venv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app.py .
COPY flagquiz/ ./flagquiz/
COPY data/ ./data/
COPY static/ ./static/
COPY templates/ ./templates/

ENV PATH="/var/task/.venv/bin:${PATH}"
ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080", "-w", "1"]
