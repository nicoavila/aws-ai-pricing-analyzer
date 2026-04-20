FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management (required by awslabs MCP server)
RUN pip install uv

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install the AWS Pricing MCP server so it's available at runtime
RUN uvx awslabs.aws-pricing-mcp-server@latest --help 2>/dev/null || true

COPY entrypoint.py .

ENTRYPOINT ["python", "/app/entrypoint.py"]
