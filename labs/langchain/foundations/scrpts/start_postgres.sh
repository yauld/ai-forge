#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="langgraph-postgres"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_DB="postgres"
POSTGRES_PORT="5432"
POSTGRES_IMAGE="postgres:17"

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Container '$CONTAINER_NAME' already exists. Starting it..."
  docker start "$CONTAINER_NAME" >/dev/null
else
  echo "Creating and starting container '$CONTAINER_NAME'..."
  docker run --name "$CONTAINER_NAME" \
    -e POSTGRES_USER="$POSTGRES_USER" \
    -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
    -e POSTGRES_DB="$POSTGRES_DB" \
    -p "$POSTGRES_PORT:5432" \
    -d "$POSTGRES_IMAGE" >/dev/null
fi

echo
echo "PostgreSQL is ready (or starting up) at:"
echo "  host: localhost"
echo "  port: $POSTGRES_PORT"
echo "  database: $POSTGRES_DB"
echo "  user: $POSTGRES_USER"
echo "  password: $POSTGRES_PASSWORD"
echo
echo "DB_URI:"
echo "  postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/$POSTGRES_DB?sslmode=disable"
