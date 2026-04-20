<p align="center">
  <img src="https://raw.githubusercontent.com/nicoavila/aws-ai-pricing-analyzer/b84ee479b60fbf2c352620b027d30f5844ba4798/icon.png" width="150" alt=">AWS Pricing AI Analyzer logo" />
</p>

<h1 align="center">AWS Pricing AI Analyzer</h1>

<p align="center">A GitHub Action that uses AI to analyze your Terraform plan and estimate the AWS infrastructure cost for a given time frame.</p>

## About

AWS Pricing AI Analyzer takes a Terraform plan (JSON format), queries the [AWS Pricing MCP Server](https://awslabs.github.io/mcp/servers/aws-pricing-mcp-server) for up-to-date pricing data, and passes the results to an LLM via [OpenRouter](https://openrouter.ai) to generate a structured cost breakdown with optimization recommendations.

## Try it

Add this to any workflow that generates a Terraform plan:

```yaml
steps:
  - uses: actions/checkout@v4

  - name: Analyze Terraform costs
    id: pricing
    uses: nicolasavila/aws-pricing-analyzer@v1
    env:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    with:
      tfplan-path: path/to/tfplan.json
      aws-region: us-east-1
      time-frame: monthly

  - name: Print cost estimate
    run: |
      echo "Estimated cost: ${{ steps.pricing.outputs.total-cost }} USD/month"
```

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `tfplan-path` | Yes | — | Path to the Terraform plan in JSON format |
| `aws-region` | No | `us-east-1` | AWS region for pricing lookup |
| `time-frame` | No | `monthly` | Cost unit: `hourly`, `monthly`, or `yearly` |
| `model` | No | `openai/gpt-4o` | OpenRouter model to use for analysis |

### Outputs

| Output | Description |
|---|---|
| `total-cost` | Estimated total cost for the given time frame |
| `cost-report` | Full cost breakdown as a JSON string |

## Setup

### 1. Generate a Terraform plan in JSON format

```bash
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
```

### 2. Create an IAM user with pricing read access

Attach the following policy to a new IAM user (`github-actions-pricing`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pricing:GetProducts",
        "pricing:DescribeServices",
        "pricing:GetAttributeValues"
      ],
      "Resource": "*"
    }
  ]
}
```

Then generate an access key for that user.

### 3. Configure repository secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `OPENROUTER_API_KEY` | Your API key from [openrouter.ai](https://openrouter.ai) |
| `AWS_ACCESS_KEY_ID` | Access key ID from the IAM user above |
| `AWS_SECRET_ACCESS_KEY` | Secret access key from the IAM user above |

## How it works

```
Terraform plan (JSON)
       │
       ▼
AWS Pricing MCP Server          ← queries live AWS pricing data
       │
       ▼
OpenRouter (LLM)                ← generates structured cost analysis
       │
       ▼
Cost report + GitHub outputs
```

1. The action reads the Terraform plan JSON and extracts the resource changes
2. It spawns the [AWS Pricing MCP Server](https://awslabs.github.io/mcp/servers/aws-pricing-mcp-server) as a subprocess and calls `analyze_terraform_project()` to fetch real pricing data
3. The pricing data and plan are sent to an LLM via OpenRouter, which returns a structured JSON report with per-resource costs and optimization recommendations
4. The total cost and full report are exposed as action outputs

## Contribute

Contributions are welcome. To run the example locally:

```bash
cd examples/terraform
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json

export OPENROUTER_API_KEY=your_key
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export TFPLAN_PATH=examples/terraform/tfplan.json
export AWS_REGION=us-east-1
export TIME_FRAME=monthly

python entrypoint.py
```

To open a PR, fork the repo, create a branch, and submit your changes. Please keep PRs focused on a single concern.

## Motivation

Estimating AWS costs before applying a Terraform plan is tedious — it requires cross-referencing the AWS Pricing page for each resource type, doing the math manually, and repeating it every time the plan changes.

Tools like [Infracost](https://www.infracost.io) do a fantastic job at solving this problem and the work behind it is genuinely admirable. However, for my particular needs I wanted a simpler solution built on technologies that are widely available today — an MCP server for live pricing data and an LLM for the analysis — without the overhead of a dedicated SaaS platform.

This action automates that process directly in CI, so cost visibility becomes part of the normal pull request workflow rather than an afterthought.

## License

[MIT](LICENSE)
