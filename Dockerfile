FROM python:3.12-slim

# Lambda Web Adapter: forwards Lambda Function URL / API Gateway events to a
# normal HTTP server. When run outside Lambda (e.g. `docker run` locally),
# this extension is simply inert and the container behaves like a plain
# gunicorn server.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1 /lambda-adapter /opt/extensions/lambda-adapter

WORKDIR /var/task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY flagquiz/ ./flagquiz/
COPY data/ ./data/
COPY static/ ./static/
COPY templates/ ./templates/

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080", "-w", "1"]
