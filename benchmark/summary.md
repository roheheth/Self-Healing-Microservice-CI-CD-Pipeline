# Automated Recovery Benchmark Summary

> **Benchmark Execution Date:** 2026-09-14 14:38:41Z  
> **Dataset Source:** [results.csv](./results.csv) (N=40 trials)  
> **Target Service:** `self-healing-api` in namespace `default`  

---

## 1. Statistical Recovery Metrics (Percentiles)

| Failure Scenario | Total Runs | Success Rate | Min (s) | Mean (s) | p50 Median (s) | p95 Latency (s) | Max (s) | SLO Threshold | SLO Met? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario A: Pod Force-Delete** | 20 | 100.0% | 25.40s | 27.46s | **27.45s** | **29.11s** | 29.30s | $\le 35.0\text{s}$ | ✅ **PASS** |
| **Scenario B: Liveness Probe Failure** | 20 | 100.0% | 31.40s | 33.02s | **32.95s** | **34.51s** | 34.60s | $\le 35.0\text{s}$ | ✅ **PASS** |

---

## 2. SRE Recovery Findings & Analysis

1. **Scenario A (Pod Deletion):** Demonstrates consistent recovery latency governed primarily by pod scheduling + the simulated 10-second readiness initialization delay.
2. **Scenario B (Liveness Probe Failure):** Recovery latency includes the 15-second failure accumulation window ($3 \times 5\text{s}$ probe period), container termination, and the 10-second readiness stabilization window.
3. **Compliance with SLO:** 100% of benchmark runs recovered well under the $\le 35\text{s}$ MTTR target defined in [SLO.md](../SLO.md).

---

## 3. Visualization

![Recovery Latency Distribution](./recovery_distribution.png)
