FROM python:3.11-slim

# Install postgresql-client, which contains the 'pg_isready' command
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy the wait script into the container and make it executable
COPY ./wait-for-db.sh /code/wait-for-db.sh
RUN chmod +x /code/wait-for-db.sh

# Copy and install Python dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application code
COPY . /code

# The ENTRYPOINT is now our wait script. It will receive the CMD as arguments.
ENTRYPOINT ["/code/wait-for-db.sh", "db"]

# This command is passed to the entrypoint script after the database is ready.
# Note: --reload is removed as it's not ideal for a production-like VPS deployment.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
