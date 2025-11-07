FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends             bash jq psmisc && rm -rf /var/lib/apt/lists/*
WORKDIR /runner
COPY runner /runner
RUN chmod +x /runner/run_script.sh
CMD ["/runner/runner-entrypoint.py"]
