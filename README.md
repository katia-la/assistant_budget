# 💰 Assistant Budget - End-to-End AI Agent Project

> A financial assistant that analyzes your banking transactions.  

> An evolving project, designed to learn and experiment with **conversational AI**.

### Purpose

Build and ship a full AI agent solution for analyzing bank transactions - from tool setup and prompts to a deployement on AWS.

### Problem solved & benefits
- Faster insights: Answers questions about spending patterns instantly instead of manual spreadsheet analysis.
- Operationalized AI: Users can query their finances through natural language, via a REST API.
- Repeatable delivery: CI/CD + containers mean every change can be rebuilt, tested, and redeployed in a consistent way.

### What I built

- Model and setup : OpenAI API + model configuration.
- Inference service: FastAPI app.
- Containerization: Docker image with uvicorn.
- CI/CD: GitHub Actions builds the image and pushes to Docker Hub; optionally triggers an ECS service update.
- Orchestration: AWS ECS Fargate runs the container (serverless).


[//]: # "- Networking: Application Load Balancer (ALB) on HTTP:80 forwarding to a Target Group (IP targets on HTTP:8000). - Security: Security groups scoped to allow ALB inbound 80 from the internet, and task inbound 8000 from the ALB SG. - Observability: CloudWatch Logs for container stdout/stderr and ECS service events.
"


## Installation

Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances.

```bash
uv sync
```