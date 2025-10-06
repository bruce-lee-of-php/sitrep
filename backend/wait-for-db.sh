#!/bin/sh
# wait-for-db.sh

# Exit immediately if a command exits with a non-zero status.
set -e

# The host to check is passed as the first argument
host="$1"
shift
# The command to execute after the DB is ready is passed as the remaining arguments
cmd="$@"

# Loop until pg_isready returns 0 (success)
# It uses the environment variables for user, password, and dbname
until PGPASSWORD=$POSTGRES_PASSWORD pg_isready -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

# When the loop exits, the DB is ready
>&2 echo "Postgres is up - executing command"
# Execute the command that was passed in (e.g., uvicorn)
exec $cmd
