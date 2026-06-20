# 🛰️ NOC Agentic AI — Network Operation Centre Automation Platform

> An end-to-end, multi-agent AI system that automates alarm detection, root cause analysis, ticketing, traffic migration, and maintenance workflows for optical transport networks (SDH / OTN / DWDM) — built with LangGraph, Claude, FastAPI, React, and AWS.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![Claude](https://img.shields.io/badge/Claude-Sonnet%204.6-D97757?logo=anthropic&logoColor=white)](https://www.anthropic.com/)
[![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/ecs/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📡 Overview

Network Operation Centres managing optical transport infrastructure (SDH, OTN, DWDM) traditionally rely on engineers manually polling NMS dashboards every 30 minutes to catch alarms, collect logs, raise JIRA tickets, and notify management — a process that adds **30–60 minutes of detection-to-response latency** to every incident.

**NOC Agentic AI** replaces that manual loop with an 8-agent LangGraph pipeline powered by Claude that triages alarms, performs root cause analysis, proposes traffic migrations, drafts MDT requests, opens JIRA tickets, and emails management — all within seconds of an alarm firing, with human-in-the-loop approval gates for any traffic-affecting action.

This is a full-stack, cloud-deployable system: React dashboard, FastAPI + LangGraph backend, PostgreSQL/Redis data layer, and AWS CDK infrastructure-as-code for production deployment on ECS Fargate.

---

## ✨ Key Features

- 🔴 **Real-time alarm dashboard** — live WebSocket feed of SDH/OTN/DWDM alarms with severity-based triage (Critical / High / Memo)
- 🤖 **8-agent LangGraph pipeline** — Supervisor → Triage → RCA → Migration/MDT → Ticketing → Notification → Report
- 🎫 **Automated JIRA ticketing** — severity-mapped priority, full alarm context, RCA summary auto-populated
- 📧 **Management email alerts** — auto-generated, severity-gated notifications
- 🔀 **Traffic migration HITL workflow** — AI proposes a migration plan (source/target port, risk, optical budget); a human approves or rejects before execution
- 🛠️ **MDT (Maintenance Down Time) workflow** — structured card-reset requests with pre-checks, reset procedure, and approval gate
- 📊 **Daily shift reports** — MTTR/MTTD KPIs, alarm trend charts, top-affected-node ranking, auto-generated shift narrative
- 🔍 **Full observability** — every agent decision traced in LangSmith
- ☁️ **Cloud-native deployment** — AWS CDK provisions VPC, ECS Fargate, RDS PostgreSQL (pgvector), ElastiCache Redis, and ALB
- 🧪 **Demo-ready out of the box** — built-in NMS simulator generates realistic alarms every 30s, no real network required

---

## 🏗️ Architecture

```
┌─────────────┐     WebSocket      ┌──────────────────┐
│   React UI   │◄──────────────────│   FastAPI Server  │
│  (Dashboard, │     REST API       │   + WebSocket Hub  │
│  HITL, MDT)  │◄──────────────────►│                    │
└─────────────┘                    └─────────┬──────────┘
                                              │
                              ┌───────────────▼────────────────┐
                              │      LangGraph Agent Pipeline    │
                              │                                  │
                              │  Supervisor ──► Triage ──► RCA   │
                              │       │                    │     │
                              │       ▼                    ▼     │
                              │   Migration   ◄──┐   Ticketing   │
                              │    (HITL)         │       │       │
                              │       │           │       ▼       │
                              │      MDT ─────────┘  Notification │
                              │    (HITL)                  │       │
                              │                             ▼       │
                              │                          Report     │
                              └─────────────────┬────────────────┘
                                                 │
                          ┌──────────────────────┼──────────────────────┐
                          ▼                       ▼                      ▼
                  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
                  │  PostgreSQL    │      │     Redis      │      │   Claude API   │
                  │  + pgvector    │      │  (state/cache) │      │  (Sonnet 4.6)  │
                  └───────────────┘      └───────────────┘      └───────────────┘
```

**NMS Layer:** Mock simulator generates SDH/OTN/DWDM alarms for demo; swap in real NETCONF/REST/SNMP adapters for production (see [Roadmap](#-roadmap)).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand, Recharts |
| **Backend** | FastAPI, Python 3.11, WebSockets, Uvicorn |
| **AI / Agents** | LangGraph, LangChain, Claude Sonnet 4.6, LangSmith |
| **Database** | PostgreSQL 16 + pgvector, Redis 7 |
| **Infrastructure** | AWS ECS Fargate, RDS, ElastiCache, ALB, CDK (TypeScript) |
| **CI/CD** | GitHub Actions, Docker multi-stage builds |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js ≥ 20, Python ≥ 3.11 (for local dev outside containers)
- An [Anthropic API key](https://console.anthropic.com) and a [LangSmith API key](https://smith.langchain.com)

### Run Locally

```bash
git clone https://github.com/<your-username>/noc-agentic-ai.git
cd noc-agentic-ai

cp .env.example .env
# Fill in ANTHROPIC_API_KEY, LANGCHAIN_API_KEY, and other keys

docker compose up --build
```

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

Alarms start streaming automatically within 30 seconds — no real NMS required for the demo.

### Deploy to AWS

```bash
cd infrastructure/cdk
npm install
cdk bootstrap aws://<ACCOUNT_ID>/<REGION>
cdk deploy --all
```

Full step-by-step setup, testing, and AWS deployment instructions are in [`docs/Implementation_Deployment_Guide.docx`](docs/).

---

## 📂 Project Structure

```
noc-system/
├── backend/                  # FastAPI + LangGraph agents
│   ├── app/agents/           # 8-agent pipeline (graph.py, tools.py, state.py)
│   ├── app/api/routes/       # REST endpoints (alarms, tickets, migration, mdt, reports)
│   ├── app/services/         # NMS simulator, alarm processor
│   └── app/websocket/        # Real-time broadcast manager
├── frontend/                 # React + TypeScript dashboard
│   └── src/components/       # dashboard, alarms, tickets, migration, mdt, reports
├── infrastructure/cdk/       # AWS CDK stack (VPC, ECS, RDS, ElastiCache, ALB)
├── scripts/deploy.sh         # One-command build → push → deploy
├── docker-compose.yml        # Local multi-service orchestration
└── .env.example              # Required environment variables
```

---

## 🧠 The 8-Agent Pipeline

| Agent | Responsibility |
|---|---|
| **Supervisor** | Classifies severity, decides if migration/MDT/human approval is needed |
| **Triage** | Enriches the raw alarm with topology, circuit, and impact context |
| **RCA** | Performs root cause analysis with confidence scoring and RFO categorisation |
| **Migration** | Proposes a traffic migration plan to a free port on the same route (HITL-gated) |
| **MDT** | Drafts a maintenance-down-time card-reset request (HITL-gated) |
| **Ticketing** | Auto-generates a structured JIRA ticket with full context |
| **Notification** | Sends severity-gated email alerts to management |
| **Report** | Compiles a final processing summary for the shift report |

---

## 🗺️ Roadmap

- [ ] Real NMS adapters (NETCONF/RESTCONF/SNMP) for Ciena, Nokia, Huawei, Infinera
- [ ] pgvector-backed RCA knowledge base for pattern-matched root cause suggestions
- [ ] Predictive alarm detection from PM trend analysis
- [ ] Arabic / RTL UI for Vision 2030-aligned GCC deployments
- [ ] Mobile on-call app (Capacitor wrapper)

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙋 About

Built by **Faraz Khan**, Forward Deployment Engineer (FDE) specialising in agentic AI automation for telecom NOC operations. This project demonstrates production-grade multi-agent system design, full-stack engineering, and cloud infrastructure-as-code — built as a portfolio piece for AI/Solution Engineering roles in the GCC market.
