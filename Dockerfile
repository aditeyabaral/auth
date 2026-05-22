FROM python:3.12-slim-bookworm

WORKDIR /pesu-auth

COPY requirements.txt .
COPY pyproject.toml .
COPY README.md .
COPY app ./app

RUN pip install -r requirements.txt && pip install --no-deps .

CMD ["python", "-m", "app.app"]
