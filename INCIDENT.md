# Incident Report — Simulated Failure & Self-Healing Demonstration

**Project:** Self-Healing API with Monitoring  
**Date:** 2026-08-04  
**Author:** SRE Portfolio Project  
**Severity:** SEV-3 (Non-production, controlled simulation)  
**Status:** Resolved — Automatically by Kubernetes self-healing  

---

## Incident Overview

Two failure scenarios were simulated to demonstrate Kubernetes self-healing capabilities and the end-to-end observability loop. Both scenarios were resolved automatically without manual intervention beyond the initial trigger.

---

## Scenario A — Manual Pod Deletion (Simulated Node/Pod Crash)

### Description
A running pod was forcefully deleted to simulate a scenario where a node crashes or a pod is evicted from the cluster. This mirrors real-world events such as node failures, OOM kills, or accidental pod deletions by an operator.

### Timeline of Events

| Time | Event |
|------|-------|
| T+0s | Pod `self-healing-api-<hash>` confirmed running and serving traffic on NodePort 30080 |
| T+5s | `kubectl delete pod self-healing-api-<hash>` executed — pod enters `Terminating` state |
| T+6s | Kubernetes Deployment controller detects replica count drop below desired (1 → 0) |
| T+8s | New pod `self-healing-api-<new-hash>` created and scheduled on node |
| T+18s | Readiness probe on `/ready` begins returning HTTP 503 (simulated 10-second init delay) |
| T+28s | Readiness probe returns HTTP 200 — pod enters `Running/Ready` state |
| T+28s | Service resumes routing traffic to new pod |

**Total Recovery Time: ~28 seconds** (10s for Kubernetes pod scheduling + 10s for simulated app initialization)

### Detection Method
- Primary: `kubectl get pods -w` (watch flag) — observed pod status transition in real time
- Secondary: Datadog dashboard showed a brief drop in request throughput during pod recreation window

### Root Cause
Intentional manual deletion via `kubectl delete pod` to demonstrate the Kubernetes ReplicaSet controller's self-healing loop.

### Resolution
Resolved automatically. Kubernetes ReplicaSet controller detected the pod count fell below `replicas: 1` and immediately scheduled a replacement pod on the same node.

### Improvement Recommendation
> **Add a Pod Disruption Budget (PDB) [IMPLEMENTED in [`k8s-ha/`](./k8s-ha/)]:** In a multi-replica environment, configuring a `PodDisruptionBudget` (`minAvailable: 2`) guarantees that at least two pods remain available during voluntary disruptions (e.g., node drains or rolling updates). This has been implemented and validated with 0% dropped requests under load in [`k8s-ha/ROLLOUT_RESULTS.md`](./k8s-ha/ROLLOUT_RESULTS.md).


---

## Scenario B — Application Liveness Failure (Simulated Internal Crash)

### Description
The `/simulate-unhealthy` endpoint was called, which sets an internal flag causing the `/health` endpoint to return HTTP 500 instead of HTTP 200. This simulates a scenario where the application process is still running (no pod crash) but has entered an internally broken state (e.g., a deadlock, corrupted in-memory state, or a dependency failure).

### Timeline of Events

| Time | Event |
|------|-------|
| T+0s | Application confirmed healthy — `/health` returns HTTP 200 |
| T+5s | `GET /simulate-unhealthy` called — application internal health flag flipped to `false` |
| T+6s | `/health` endpoint now returns HTTP 500 |
| T+11s | Kubernetes liveness probe detects first failure (`failureThreshold` not yet reached) |
| T+16s | Kubernetes liveness probe detects second consecutive failure |
| T+21s | Kubernetes liveness probe detects third consecutive failure — `failureThreshold: 3` reached |
| T+22s | Kubernetes terminates the container and records a `Restart` event |
| T+23s | Container restarts — `is_healthy` flag resets to `True` (fresh process) |
| T+23s | `/health` begins returning HTTP 200 again |
| T+33s | Readiness probe passes — pod re-enters `Ready` state and resumes traffic |

**Total Recovery Time: ~33 seconds** (21s for probe failure accumulation + 10s re-initialization + 2s for readiness)

### Detection Method
- Primary: `kubectl describe pod self-healing-api-<hash>` — showed `Liveness probe failed: HTTP probe failed with statuscode: 500` events and incremented restart count
- Secondary: Datadog alert fired on elevated error rate (5xx responses from `/health` endpoint)

### Root Cause
Intentional state manipulation via the `/simulate-unhealthy` debug endpoint. In a real scenario, this models a bug that causes an application to enter a broken state without crashing outright — the most dangerous class of failure as it can silently serve errors without triggering OS-level crash detection.

### Resolution
Resolved automatically. Kubernetes liveness probe reached `failureThreshold: 3` and restarted the container. Upon restart, the application process initialized fresh, resetting the health state to `True`.

### Improvement Recommendation
> **Tune probe thresholds based on SLO:** The current `failureThreshold: 3` with `periodSeconds: 5` means a broken application can serve errors for up to 15 seconds before Kubernetes intervenes. In a production environment, this threshold should be balanced against alert noise — too low and transient hiccups cause unnecessary restarts; too high and users experience extended degraded service. For this service's mock financial data use case, a tighter threshold of `failureThreshold: 2` and `periodSeconds: 3` would reduce the error window to ~6 seconds.

---

## Summary & Measured Benchmark Metrics

| Metric | Scenario A (Pod Deletion) | Scenario B (Liveness Failure) |
|--------|--------------------------|-------------------------------|
| **Detection Method** | `kubectl get pods -w` / ReplicaSet Controller | Kubernetes liveness probe (`/health`) |
| **Auto-Recovery?** | ✅ Yes (Automated) | ✅ Yes (Automated) |
| **Recovery Latency (Single Run)** | ~28.0 seconds | ~33.0 seconds |
| **Measured p50 Median (N=20)** | **27.45 seconds** | **32.85 seconds** |
| **Measured p95 Latency (N=20)** | **29.11 seconds** | **34.51 seconds** |
| **SLO Recovery Target (≤35s)** | ✅ Met ($100\%$ compliance) | ✅ Met ($100\%$ compliance) |
| **Error Budget Consumed** | $0.22\%$ of 30-day budget | $0.25\%$ of 30-day budget |
| **Human Intervention Required?** | None | None |
| **Datadog Alert Fired?** | Request drop visible | Yes — error rate spike |

> 📊 **Empirical Dataset:** Full recovery distributions, min/max metrics, and box plots are available in [benchmark/summary.md](./benchmark/summary.md).  
> 📑 **Error Budget Model:** Full mathematical derivation and burn-rate alerting policies are documented in [SLO.md](./SLO.md).

### Key SRE Takeaways
1. **Kubernetes self-healing is not magic** — it requires correctly configured probes with appropriate thresholds. Without liveness/readiness probes, a broken-but-running container would serve errors indefinitely.
2. **Readiness probes prevent premature traffic routing** — the 10-second simulated init delay on `/ready` demonstrates that traffic is withheld from a pod that isn't yet ready, preventing errors during cold-start.
3. **Observability is essential for measuring MTTD** — without Datadog metrics, the detection of Scenario B would have relied entirely on a user noticing errors, dramatically increasing Mean Time to Detect (MTTD).
4. **The liveness probe failure window is part of your error budget** — the combined downtime of both incidents ($61\text{s}$) consumed only **$0.47\%$** of the 30-day error budget ($216\text{ minutes}$), leaving $99.53\%$ budget remaining.

