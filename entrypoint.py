import asyncio
import json
import os
import re
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openrouter import OpenRouter

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o")


def load_tfplan(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def validate_env():
    missing = [v for v in ["OPENROUTER_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"] if not os.environ.get(v)]
    if missing:
        for var in missing:
            print(f"::error::Missing required environment variable: {var}")
        sys.exit(1)


async def analyze_with_mcp(terraform_dir: str, aws_region: str) -> str:
    server_params = StdioServerParameters(
        command="uvx",
        args=["awslabs.aws-pricing-mcp-server@latest"],
        env={
            **os.environ,
            "AWS_REGION": aws_region,
            "FASTMCP_LOG_LEVEL": "ERROR",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "analyze_terraform_project",
                arguments={"project_path": terraform_dir},
            )

            return result.content[0].text if result.content else ""


def extract_json(text: str) -> dict:
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response:\n{text}")
    return json.loads(text[start:end])


def analyze_with_llm(mcp_output: str, tfplan: dict, time_frame: str) -> dict:
    api_key = os.environ["OPENROUTER_API_KEY"]

    resources_summary = json.dumps(
        tfplan.get("resource_changes", []), indent=2
    )[:4000]

    prompt = f"""You are an AWS cost analysis expert. You have been given:

1. A Terraform plan with the following resource changes:
{resources_summary}

2. An AWS Pricing analysis from the MCP server:
{mcp_output}

Based on this information, provide a structured cost analysis with:
- A breakdown of costs per resource type
- The estimated total cost ({time_frame})
- Any cost optimization recommendations

Respond ONLY with a valid JSON object using this exact structure, no markdown:
{{
  "resources": [
    {{"name": "resource_name", "type": "aws_resource_type", "estimated_cost": 0.00, "unit": "{time_frame}"}}
  ],
  "total_cost": 0.00,
  "currency": "USD",
  "time_frame": "{time_frame}",
  "recommendations": ["recommendation 1", "recommendation 2"]
}}"""

    with OpenRouter(api_key=api_key) as client:
        response = client.chat.send(
            messages=[{"role": "user", "content": prompt}],
            model=OPENROUTER_MODEL,
        )

    return extract_json(response.choices[0].message.content)


def set_github_output(key: str, value: str):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        print(f"::warning::GITHUB_OUTPUT not set, skipping output: {key}")
        return
    with open(output_file, "a") as f:
        f.write(f"{key}={value}\n")


async def main():
    validate_env()

    tfplan_path = os.environ.get("TFPLAN_PATH")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    time_frame = os.environ.get("TIME_FRAME", "monthly")

    if not tfplan_path:
        print("::error::TFPLAN_PATH is required")
        sys.exit(1)

    if not os.path.exists(tfplan_path):
        print(f"::error::Terraform plan file not found: {tfplan_path}")
        sys.exit(1)

    terraform_dir = os.path.dirname(os.path.abspath(tfplan_path))

    print(f"Loading Terraform plan from: {tfplan_path}")
    tfplan = load_tfplan(tfplan_path)

    print(f"Querying AWS Pricing MCP server (region: {aws_region})...")
    mcp_output = await analyze_with_mcp(terraform_dir, aws_region)

    print(f"Analyzing costs with {OPENROUTER_MODEL}...")
    report = analyze_with_llm(mcp_output, tfplan, time_frame)

    print("\n=== AWS Cost Analysis Report ===")
    print(f"Time frame : {report['time_frame']}")
    print(f"Total cost : ${report['total_cost']:.2f} {report['currency']}")
    print("\nBreakdown:")
    for resource in report.get("resources", []):
        print(f"  - {resource['name']} ({resource['type']}): ${resource['estimated_cost']:.2f}/{resource['unit']}")

    if report.get("recommendations"):
        print("\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")

    set_github_output("total-cost", str(report["total_cost"]))
    set_github_output("cost-report", json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
