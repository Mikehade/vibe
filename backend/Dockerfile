# Base image from Amazon ECR Public (mirror of Docker Hub's official image) — avoids Docker Hub
# rate limits when the image is built in AWS CodeBuild.
FROM public.ecr.aws/docker/library/python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
# All dependencies ship prebuilt wheels for linux/amd64 + Python 3.12, so no compiler is needed (keeps the image small).
COPY requirements.txt .
RUN pip install -r requirements.txt

# Development target (docker compose) — adds test tools
FROM base AS development
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target (AWS App Runner)
FROM base AS production
COPY . .
RUN rm -rf .env dev.db tests .venv && chmod +x start.sh
EXPOSE 8000
CMD ["./start.sh"]
