# Self-Healing API with Monitoring

> **A production-inspired SRE portfolio project** demonstrating the full reliability engineering loop:  
> **Build → Containerize → Deploy → Observe → Detect Failure → Self-Heal → Benchmark → Alert → HA Rollout → Document**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-teal?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-29.x-blue?logo=docker)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-local-blue?logo=kubernetes)](https://kubernetes.io)
[![Jenkins](https://img.shields.io/badge/Jenkins-CI%2FCD%20Pipeline-red?logo=jenkins)](./Jenkinsfile)
[![Datadog](https://img.shields.io/badge/Datadog-APM%20%2B%20Logs%20%2B%20Monitors-purple?logo=datadog)](https://datadoghq.com)
[![Terraform](https://img.shields.io/badge/Terraform-1.x-purple?logo=terraform)](https://terraform.io)
[![k6](https://img.shields.io/badge/k6-Load%20Tested-purple?logo=k6)](https://k6.io)
[![SLO](https://img.shields.io/badge/SLO-99.5%25%20Availability-green)](./SLO.md)
[![HA](https://img.shields.io/badge/HA-3%20Replicas%20%2B%20PDB-blue)](./k8s-ha/)

---

## Overview

This project demonstrates hands-on Site Reliability Engineering practices through a containerized REST API deployed on Kubernetes with self-healing capabilities, end-to-end observability via Datadog, cloud infrastructure provisioned via Terraform, declarative Monitor-as-Code alerting, and high-availability rolling updates under continuous load testing.

The API serves mock financial market ticker data (LSEG, AAPL, MSFT, GOOGL) using FastAPI and supports both single-replica failure recovery demonstrations and 3-replica zero-downtime rolling updates protected by a PodDisruptionBudget.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Local Machine                            │
│                                                                 │
│  ┌──────────┐   HTTP    ┌──────────────────────────────────┐   │
│  │  Client  │ ────────► │  Kubernetes (Minikube/kind)      │   │
│  └──────────┘           │                                  │   │
│                         │  ┌────────────┐                  │   │
│                         │  │  Service   │  NodePort:30080  │   │
│                         │  │ (NodePort) │                  │   │
│                         │  └─────┬──────┘                  │   │
│                         │        │                          │   │
│                         │  ┌─────▼──────────────────────┐  │   │
│                         │  │  Pods: FastAPI (1 or 3)    │  │   │
│                         │  │                            │  │   │
│                         │  │  GET /health  ◄── Liveness │  │   │
│                         │  │  GET /ready   ◄── Readiness│  │   │
│                         │  │  GET /data                 │  │   │
│                         │  │  GET /simulate-unhealthy   │  │   │
│                         │  └─────┬──────────────────────┘  │   │
│                         │        │                          │   │
│                         │  [PodDisruptionBudget: min 2]    │   │
│                         └────────┼─────────────────────────┘   │
│                                  │ traces + logs                │
│                         ┌────────▼─────────┐                   │
│                         │  Datadog Agent   │                   │
│                         │   (DaemonSet)    │                   │
│                         └────────┬─────────┘                   │
│                                  │                              │
└──────────────────────────────────┼──────────────────────────────┘
                                   │ HTTPS
                          ┌────────▼────────────────┐
                          │ Datadog Cloud            │
                          │ Dashboard + 5 Monitors   │
                          └────────┬────────────────┘
                                   │ Alerts / Webhooks
                          ┌────────▼────────────────┐
                          │ PagerDuty / Slack       │
                          │ (Fast & Slow Burn Paging)│
                          └─────────────────────────┘

[Terraform] ──► provisions ──► AWS S3 Log Bucket (eu-west-2)
```

---

## Features

| Feature | Implementation | Evidence / Artifact |
|---------|---------------|-------------------|
| **REST API** | FastAPI with structured JSON logging to stdout | [`app.py`](./app.py) |
| **Health Probes** | `/health` (liveness) + `/ready` (readiness with 10s init delay) | [`k8s/deployment.yaml`](./k8s/deployment.yaml) |
| **Mock Market Data** | `/data` endpoint with simulated price fluctuations | [`app.py`](./app.py) |
| **Failure Simulation** | `/simulate-unhealthy` flips liveness to 500, triggering K8s restart | [`INCIDENT.md`](./INCIDENT.md) |
| **Containerization** | Multi-stage Docker build, non-root user (UID 10001) | [`Dockerfile`](./Dockerfile) |
| **Single-Pod Self-Healing**| Deployment with automated reconciliation loop | [`k8s/deployment.yaml`](./k8s/deployment.yaml) |
| **HA Scaling & Rollouts** | 3-replica deployment, `RollingUpdate` strategy, PDB | [`k8s-ha/ROLLOUT_RESULTS.md`](./k8s-ha/ROLLOUT_RESULTS.md) |
| **CI/CD Pipeline** | Jenkins declarative pipeline (Lint, Trivy scan, Deploy, k6 gate) | [`Jenkinsfile`](./Jenkinsfile) |
| **Observability** | Datadog APM traces, container logs, CPU/memory dashboard | [`datadog/dashboard.json`](./datadog/dashboard.json) |
| **Monitors-as-Code** | 5 declarative monitors wired to webhook alerts | [`datadog/monitors.json`](./datadog/monitors.json) |
| **SLO Framework** | 99.5% Availability SLO, worked incident error budget burn | [`SLO.md`](./SLO.md) |
| **Recovery Benchmarking**| Automated N=20 trials measuring p50/p95 MTTR percentiles | [`benchmark/summary.md`](./benchmark/summary.md) |
| **Load Testing** | Staged k6 load testing (10–200 VUs) with latency profile | [`loadtest/RESULTS.md`](./loadtest/RESULTS.md) |
| **IaC** | Terraform provisions versioned + encrypted S3 bucket | [`terraform/main.tf`](./terraform/main.tf) |
| **Incident Post-Mortem** | Formal post-mortem analyzing detection and recovery | [`INCIDENT.md`](./INCIDENT.md) |

---

## Project Structure

```
.
├── app.py                         # FastAPI application
├── requirements.txt               # Python dependencies (FastAPI, uvicorn, ddtrace)
├── Dockerfile                     # Multi-stage, non-root container build using uvicorn
├── Jenkinsfile                    # Jenkins declarative CI/CD pipeline
├── .gitignore
├── .env.example                   # Template for secrets (DD_API_KEY, DD_APP_KEY, AWS)
├── SLO.md                         # SLIs, SLOs, Error Budget & Burn-Rate Policy
│
├── benchmark/                     # Automated Recovery Benchmarking Suite
│   ├── run_recovery_benchmark.py  # Python harness for Scenario A & B testing
│   ├── requirements.txt           # kubernetes, pandas, matplotlib, requests
│   ├── results.csv                # Raw empirical recovery dataset (N=40 trials)
│   ├── summary.md                 # Statistical percentile summary report
│   └── recovery_distribution.png  # Box plot visualization of recovery times
│
├── loadtest/                      # Staged Load Testing Baseline
│   ├── data_endpoint.js           # k6 load test script with thresholds
│   ├── raw_results.json           # k6 summary export data
│   └── RESULTS.md                 # Throughput-vs-latency benchmark report
│
├── k8s/                           # Baseline Single-Replica Deployment
│   ├── deployment.yaml            # Deployment with liveness/readiness probes
│   └── service.yaml               # NodePort Service (port 30080)
│
├── k8s-ha/                        # High-Availability & Zero-Downtime Rollout Variant
│   ├── deployment.yaml            # 3-replica deployment (RollingUpdate strategy)
│   ├── pdb.yaml                   # PodDisruptionBudget (minAvailable: 2)
│   ├── service.yaml               # NodePort Service (port 30080)
│   └── ROLLOUT_RESULTS.md         # Zero-downtime rollout & PDB audit report
│
├── datadog/
│   ├── datadog-values.yaml        # Helm values for Datadog Agent installation
│   ├── dashboard.json             # Importable Datadog dashboard definition
│   ├── monitors.json              # 5 declarative Monitor-as-Code definitions
│   ├── apply_monitors.py          # Idempotent Datadog Monitors API upsert script
│   └── webhook-config.json        # Notification channel integration template
│
├── terraform/
│   ├── main.tf                    # AWS S3 bucket with encryption + versioning
│   ├── variables.tf               # Region and environment variables
│   └── outputs.tf                 # Bucket name and ARN outputs
│
├── INCIDENT.md                    # Post-mortem for two simulated failure scenarios
└── README.md                      # This file
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | 4.x+ | [docker.com](https://docker.com) |
| Minikube | 1.x+ | `winget install Kubernetes.minikube` |
| kubectl | 1.34+ | Bundled with Docker Desktop or `winget install Kubernetes.kubectl` |
| Helm | 3.x+ | `winget install Helm.Helm` |
| Terraform | 1.x+ | `winget install Hashicorp.Terraform` |
| k6 | 0.48+ | `winget install k6` |

---

## Quick Start (< 15 minutes)

### Step 1 — Start Local Kubernetes Cluster

```powershell
winget install Kubernetes.minikube
minikube start --driver=docker
```

### Step 2 — Build & Load Image

```powershell
cd C:\Users\erohi\Downloads\LSEG
docker build -t self-healing-api:latest .
minikube image load self-healing-api:latest
```

### Step 3 — Deploy Baseline or High-Availability Variant

```powershell
# Option A: Baseline single-replica (for self-healing crash demo)
kubectl apply -f k8s/

# Option B: High-Availability 3-replica (for zero-downtime rollouts)
kubectl apply -f k8s-ha/
```

### Step 4 — Verify Application Endpoints

```powershell
# Health check (Liveness)
curl http://localhost:30080/health

# Readiness check (returns 503 during 10s cold-start, then 200)
curl http://localhost:30080/ready

# Market data payload
curl http://localhost:30080/data
```

---

## Datadog Alerting & Monitor-as-Code

The project provisions 5 production monitors declaratively via [`datadog/apply_monitors.py`](./datadog/apply_monitors.py):

1. **Latency Regression:** Alerts if $p95 > 10\text{ms}$ for 5 minutes.
2. **Container Restart:** Fires immediately upon any self-healing pod restart event.
3. **Readiness Gate Stuck:** Detects cold-starts stuck $>30\text{s}$ beyond initial warm-up.
4. **Fast Error Budget Burn (Critical - Page):** Fires if $>5\%$ of 30-day budget burns in 1 hour.
5. **Slow Error Budget Burn (Warning - Ticket):** Fires if $>10\%$ of 30-day budget burns in 6 hours.

```powershell
# Deploy monitors to Datadog idempotently
set DD_API_KEY=<your_api_key>
set DD_APP_KEY=<your_app_key>
python datadog/apply_monitors.py
```

---

## High-Availability & Zero-Downtime Rollout Demo

As verified in [`k8s-ha/ROLLOUT_RESULTS.md`](./k8s-ha/ROLLOUT_RESULTS.md):

```powershell
# 1. Apply HA deployment & PDB
kubectl apply -f k8s-ha/

# 2. In Terminal 1: Run continuous load test
k6 run loadtest/data_endpoint.js --duration 5m

# 3. In Terminal 2: Trigger rolling update mid-load
kubectl set env deployment/self-healing-api-ha DEMO_VERSION=v2
kubectl rollout status deployment/self-healing-api-ha
# Result: 0% error rate across rollout window!

# 4. In Terminal 3: Verify PDB protects against concurrent eviction
kubectl delete pod <pod-name>
kubectl get pdb self-healing-api-pdb   # ALLOWED DISRUPTIONS drops to 0 during warm-up
```

---

## Self-Healing Benchmarks & Load Testing

* **Recovery Benchmarking:** 40 trials in [`benchmark/summary.md`](./benchmark/summary.md) ($p50=27.45\text{s}$ for pod deletes, $p50=32.85\text{s}$ for liveness restarts).
* **Load Testing:** Staged ramp (10–200 VUs) in [`loadtest/RESULTS.md`](./loadtest/RESULTS.md) ($p95=7.40\text{ms}$ at 95 RPS).

---

## Terraform — AWS S3 Log Bucket

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

To clean up cloud resources:
```powershell
terraform destroy
```

---

## Resume Bullet Points

> • Engineered a containerized **FastAPI** microservice on **Kubernetes** with liveness/readiness self-healing probes ($<35\text{s}$ MTTR) and a 3-replica **PodDisruptionBudget** configuration, empirically proving zero-downtime rolling updates (0% error rate) under concurrent **k6** load testing.

> • Defined and validated an **SLO Framework** ($99.5\%$ availability, $3\text{h } 36\text{m}$ error budget) with automated recovery benchmarking ($p50=27.5\text{s}$, $p95=29.1\text{s}$); provisioned **Datadog Monitors-as-Code** (latency regression, self-heal alerts, and fast/slow burn-rate paging) wired to webhook notification channels.

---

## Cleanup

```powershell
kubectl delete -f k8s-ha/
kubectl delete -f k8s/
minikube stop
docker rmi self-healing-api:latest
cd terraform && terraform destroy
```
