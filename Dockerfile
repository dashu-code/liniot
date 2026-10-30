FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY liniot ./liniot
COPY web ./web

RUN pip install --no-cache-dir .

ENV LINIOT_DB_PATH=/data/liniot.db
VOLUME ["/data"]
EXPOSE 8000

CMD ["liniot", "run", "--host", "0.0.0.0", "--port", "8000"]
