# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10.7
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install dependencies (cached separately for efficiency)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update && apt-get install -y gcc libpq-dev && \
    python -m pip install -r requirements.txt && \
    python -m pip install psycopg2-binary

# Copy all source code (including the data directory) into /app
COPY . .

# Ensure the 'data' directory has the correct permissions
RUN chown -R appuser:appuser /app/data
RUN chmod -R 755 /app/data

# Switch to the non-privileged user to run the application.
USER appuser

# Run the bot
CMD ["python", "bot.py"]
