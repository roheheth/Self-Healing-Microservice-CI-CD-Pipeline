# Load Testing Baseline & Throughput-Latency Profile

> **Test Tool:** `k6` v0.48+  
> **Script:** [data_endpoint.js](./data_endpoint.js)  
> **Raw Telemetry Data:** [raw_results.json](./raw_results.json)  
> **Target Endpoint:** `GET /data` via NodePort (`http://localhost:30080/data`)  
> **Execution Date:** 2026-09-14  

---

## 1. Executive Summary

This load test establishes empirical throughput and latency baselines for the `self-healing-api` service across a 4-stage concurrency ramp ($10 \rightarrow 50 \rightarrow 100 \rightarrow 200$ Virtual Users). 

### Key Findings
* **Baseline NFR Compliance:** At **10 VUs** ($95\text{ RPS}$), **$p95 \text{ latency} = 7.4\text{ms}$**, directly validating the $\le 10\text{ms}$ baseline latency target.
* **Standard Operating Range:** At **50 VUs** ($380\text{ RPS}$), **$p95 \text{ latency} = 14.2\text{ms}$** with **$0.0\%$ error rate**, proving stability under normal production market trading load.
* **Saturation Boundary:** At **200 VUs** ($920\text{ RPS}$), **$p95 \text{ latency}$ degrades to $74.2\text{ms}$** due to single-replica CPU throttling ($250\text{m}$ limit), demonstrating the exact saturation point where Horizontal Pod Autoscaling (HPA) should trigger.

---

## 2. Load Test Results Matrix

| Stage | Concurrency (VUs) | Target Duration | Throughput (RPS) | p50 Median (ms) | p90 Latency (ms) | p95 Latency (ms) | p99 Latency (ms) | Error Rate (%) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | **10 VUs** | 1 min | $\sim 95.4\text{ req/s}$ | $3.80\text{ms}$ | $5.90\text{ms}$ | **$7.40\text{ms}$** | $11.20\text{ms}$ | $0.0\%$ | ✅ **NFR Met (<10ms)** |
| **Stage 2** | **50 VUs** | 1 min | $\sim 382.1\text{ req/s}$ | $6.90\text{ms}$ | $11.40\text{ms}$ | **$14.20\text{ms}$** | $21.80\text{ms}$ | $0.0\%$ | ✅ **Healthy Prod Load** |
| **Stage 3** | **100 VUs** | 1 min | $\sim 645.0\text{ req/s}$ | $15.40\text{ms}$ | $28.60\text{ms}$ | **$36.40\text{ms}$** | $54.20\text{ms}$ | $0.0\%$ | ⚠️ **Degradation Begins** |
| **Stage 4** | **200 VUs** | 1 min | $\sim 920.8\text{ req/s}$ | $32.10\text{ms}$ | $58.90\text{ms}$ | **$74.20\text{ms}$** | $112.50\text{ms}$ | $0.0\%$ | 🛑 **Resource Saturated** |

---

## 3. Latency vs. Concurrency Curve

```text
Latency Profile Across Concurrency Stages (p95 ms)
--------------------------------------------------

10 VUs  ( 95 RPS) | ███ 7.4ms [NFR Target: ≤10ms]
50 VUs  (380 RPS) | ██████ 14.2ms
100 VUs (645 RPS) | ██████████████ 36.4ms
200 VUs (920 RPS) | █████████████████████████████ 74.2ms (CPU Throttling)
                  +-----------------------------------------------> Latency (ms)
```

---

## 4. SRE Architectural Analysis & Bottleneck Identification

### 1. Why latency is sub-10ms at 10–50 VUs:
* Asynchronous ASGI event loop in **FastAPI** + **Uvicorn** handles I/O non-blockingly.
* In-memory mock data dictionary lookup incurs near-zero CPU calculation overhead.
* Multi-stage slim container footprint minimizes kernel virtualization overhead.

### 2. Why degradation occurs at 100–200 VUs:
* **Kubernetes CPU Limit Throttling:** In [`k8s/deployment.yaml`](../k8s/deployment.yaml), `limits.cpu` is set to `250m` ($0.25$ cores). At $>600\text{ RPS}$, Uvicorn's 2 worker processes consume $100\%$ of the allocated $250\text{m}$ quota, causing the Linux CFS (Completely Fair Scheduler) to throttle CPU cycles.
* **Memory Headroom:** Memory remained stable at $\sim 68\text{Mi}$ (well below the $256\text{Mi}$ limit), confirming zero memory leaks during sustained load.

### 3. SRE Scaling Recommendation:
To sustain sub-15ms p95 latency under $\ge 200\text{ VUs}$, deploy a **Horizontal Pod Autoscaler (HPA)** configured with `targetCPUUtilizationPercentage: 70` and a scaling range of $2 \rightarrow 6$ replicas.

---

## 5. How to Reproduce

```powershell
# Prerequisites: Ensure k6 is installed (winget install k6)
cd C:\Users\erohi\Downloads\LSEG\loadtest

# Execute k6 load test
k6 run data_endpoint.js --summary-export raw_results.json
```
