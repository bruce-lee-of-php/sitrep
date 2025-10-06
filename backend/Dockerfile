FROM python:3.11-slim

# Install postgresql-client (for pg_isready) and dos2unix (to fix line endings)
RUN apt-get update && apt-get install -y postgresql-client dos2unix && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy the wait script into the container
COPY ./wait-for-db.sh /code/wait-for-db.sh

# --- FIX: Ensure the script is executable and has correct line endings ---
# 1. Convert line endings from Windows format to Unix format.
RUN dos2unix /code/wait-for-db.sh
# 2. Make the script executable.
RUN chmod +x /code/wait-for-db.sh

# Copy and install Python dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application code
COPY . /code

# The ENTRYPOINT is now our wait script. It will receive the CMD as arguments.
ENTRYPOINT ["/code/wait-for-db.sh", "db"]

# This command is passed to the entrypoint script after the database is ready.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

