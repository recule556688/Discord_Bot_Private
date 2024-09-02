# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.10.7
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
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

# Download dependencies as a separate step to take advantage of Docker's caching.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update && apt-get install -y gcc libpq-dev && \
    python -m pip install -r requirements.txt && \
    python -m pip install psycopg2-binary

# Copy the source code into the container.
COPY . .

# Ensure the font file is copied to the working directory.
COPY data/Roboto-Bold.ttf /app/data/Roboto-Bold.ttf


# Switch to the non-privileged user to run the application.
USER appuser

# Run the migration script and then the bot
CMD ["sh", "-c", "python bot.py"]
