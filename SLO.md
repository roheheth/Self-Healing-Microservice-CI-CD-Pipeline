# Service Level Objective (SLO) & Error Budget Framework

> **Service:** `self-healing-api` (Financial Market Data Service)  
> **Framework Version:** 1.0.0  
> **Status:** Active / Production Baseline  
> **Last Review Date:** 2026-09-14  

---

## 1. Service Overview

The `self-healing-api` is an asynchronous microservice delivering real-time financial market ticker quotations (e.g., LSEG, AAPL, MSFT, GOOGL) to downstream consumers. Because market data feeds directly impact algorithmic trading and real-time portfolio valuations, this service prioritizes strict response latency, rapid self-healing under pod/node disruption, and continuous availability verification via container health probes.

---

## 2. Service Level Indicators (SLIs)

An SLI is a quantifiable metric that measures the level of service provided to users over a defined evaluation window.

| SLI Name | Definition | Measurement Method & Formula | Data Source |
| :--- | :--- | :--- | :--- |
| **Availability SLI** | Percentage of probe and synthetic health checks returning HTTP `200 OK`. | $$\text{SLI}_{\text{avail}} = \frac{\sum \text{Successful Probes (HTTP 200)}}{\sum \text{Total Probe Invocations}} \times 100$$ | Kubernetes Kubelet Probe Events & Datadog HTTP Monitor (`/health`) |
| **Latency SLI** | Percentage of valid financial data requests completing in less than $10\text{ms}$. | $$\text{SLI}_{\text{latency}} = \frac{\sum \text{Requests with } \text{latency} < 10\text{ms}}{\sum \text{Total } \text{GET } /\text{data Requests}} \times 100$$ | Datadog APM (`trace.fastapi.request.duration`) & `stdout` JSON logs |
| **Recovery SLI** | Percentage of induced or spontaneous failure events recovering to a healthy state within $\le 35\text{s}$. | $$\text{SLI}_{\text{recovery}} = \frac{\sum \text{Recovery Events } \le 35\text{s}}{\sum \text{Total Failure Incidents}} \times 100$$ | Kubernetes Controller Audit Logs & Benchmark Harness (`benchmark/results.csv`) |

---

## 3. Service Level Objectives (SLOs)

An SLO is the agreed-upon reliability target that the engineering team commits to maintaining.

| SLO Objective | Target | Measurement Window | Operational Rationale |
| :--- | :--- | :--- | :--- |
| **Availability SLO** | $\ge \mathbf{99.5\%}$ | Rolling 30 Days | Allows sufficient error budget for rolling deployments, node updates, and transient probe failures while guaranteeing $\le 3.6\text{ hours}$ total downtime per month. |
| **Latency SLO** | $\ge \mathbf{95.0\%} < 10\text{ms}$ | Rolling 7 Days | Ensures fast quote lookups for traders under standard traffic concurrency (10–50 concurrent users) as verified in [loadtest/RESULTS.md](./loadtest/RESULTS.md). |
| **Recovery SLO** | $\ge \mathbf{99.0\%} \le 35\text{s}$ | Rolling 30 Days | Asserts that Kubernetes self-healing reconciliation loops resolve crashes before client-side timeouts cascade across upstream microservices. |

---

## 4. Error Budget Derivation

The **Error Budget** represents the maximum allowable unreliability (downtime or failed requests) before engineering must halt feature delivery to focus exclusively on stability.

$$\text{Error Budget} = 1.00 - \text{SLO Target} = 1.00 - 0.995 = 0.005 \text{ (or } 0.5\% \text{)}$$

### 30-Day Calendar Error Budget (Availability)

| Time Horizon | Total Duration | Allowed Unavailability ($0.5\%$) |
| :--- | :--- | :--- |
| **30 Days (Standard)** | $30 \times 24 \times 60 = 43,200 \text{ minutes}$ | $\mathbf{216.0 \text{ minutes}}$ ($\mathbf{3 \text{ hours } 36 \text{ minutes}}$ or $12,960\text{s}$) |
| **7 Days (Weekly)** | $7 \times 24 \times 60 = 10,080 \text{ minutes}$ | $50.4 \text{ minutes}$ ($3,024\text{s}$) |
| **24 Hours (Daily)** | $24 \times 60 = 1,440 \text{ minutes}$ | $7.2 \text{ minutes}$ ($432\text{s}$) |

---

## 5. Worked Example: Budget Consumption from Recorded Incidents

Using the empirical recovery timelines documented in [INCIDENT.md](./INCIDENT.md) and verified in [benchmark/summary.md](./benchmark/summary.md):

### Incident Log Data

```
Scenario A (Pod Force-Kill):       28.0 seconds total downtime (ReplicaSet scheduling + readiness delay)
Scenario B (Liveness Probe 500):   33.0 seconds total downtime (15s probe detection + 10s init delay + 8s stabilization)
---------------------------------------------------------------------------------------------------------
Total Unavailability Incurred:     61.0 seconds (1 minute 1 second)
```

### Error Budget Impact Analysis

$$\text{Total 30-Day Budget} = 216 \text{ minutes} = 12,960 \text{ seconds}$$

$$\text{Budget Consumed} = \frac{61 \text{ seconds}}{12,960 \text{ seconds}} \times 100 = \mathbf{0.47\%}$$

$$\text{Remaining Error Budget} = 100\% - 0.47\% = \mathbf{99.53\%} \text{ (214 minutes 59 seconds remaining)}$$

> **SRE Finding:** Both combined failure scenarios consumed less than **$0.5\%$** of the service's monthly error budget. The automated self-healing mechanisms maintained compliance within the $99.5\%$ SLO threshold without human intervention.

---

## 6. Burn-Rate Alerting Policy

A burn rate of **$1\text{x}$** means the error budget will be completely exhausted in exactly 30 days. Burn-rate alerting triggers proactive alerts when error budget consumption accelerates rapidly.

```
Burn Rate Factor = (Error Rate Observed) / (1 - SLO)
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SLO BURN RATE ALERT MATRIX                         │
├─────────────┬───────────┬────────────────┬───────────────┬──────────────────┤
│ Alert Level │ Burn Rate │ Budget Consumed│ Window Size   │ Action Required  │
├─────────────┼───────────┼────────────────┼───────────────┼──────────────────┤
│ CRITICAL    │ 14.4x     │ > 5.0% in 1h   │ 1 Hour        │ Page On-Call SRE │
│ WARNING     │ 6.0x      │ > 10.0% in 6h  │ 6 Hours       │ Open SRE Ticket  │
│ INFORMATIONAL│ 1.0x     │ Normal pacing  │ 30 Days       │ Monthly Review   │
└─────────────┴───────────┴────────────────┴───────────────┴──────────────────┘
```

1. **Fast-Burn Alert (Critical - Page On-Call):**
   * **Condition:** Error rate exceeds $7.2\%$ over a 1-hour window (consuming $>5\%$ of the monthly budget in 1 hour).
   * **Action:** Automated notification via PagerDuty/Slack to the primary on-call engineer; immediate triage required.
   * **Implemented Monitor:** Configured in [`datadog/monitors.json`](./datadog/monitors.json) as `self-healing-api - error budget fast burn (critical)`.

2. **Slow-Burn Alert (Warning - JIRA / Slack Ticket):**
   * **Condition:** Error rate exceeds $1.0\%$ over a 6-hour window (consuming $>10\%$ of the monthly budget in 6 hours).
   * **Action:** Automated ticket logged to the SRE board for investigation during business hours.
   * **Implemented Monitor:** Configured in [`datadog/monitors.json`](./datadog/monitors.json) as `self-healing-api - error budget slow burn (warning)`.

3. **Budget Exhaustion Policy (Budget Burned Out):**
   * **Condition:** Remaining error budget drops to $\le 0\%$.
   * **Action:** Feature freezes enforced. All deployment pipelines block non-critical feature releases; only reliability fixes and rollbacks permitted until the 30-day rolling window resets.

> 🛠️ **Monitor-as-Code Automation:** All burn-rate alerts are provisioned idempotently using [`datadog/apply_monitors.py`](./datadog/apply_monitors.py).


---

## 7. Review Cadence & Continuous Improvement

* **Monthly Reliability Review:** The SRE team and service owners review SLI trends, incident post-mortems, and error budget consumption on the 1st of every month.
* **SLO Tuning:** If the service consistently achieves $100\%$ availability with zero budget burn over 3 consecutive quarters, SLO targets may be tightened (e.g., $99.5\% \rightarrow 99.9\%$) to reflect actual reliability expectations.

---

## 8. Cross-References

* 📄 **Incident Post-Mortem:** [INCIDENT.md](./INCIDENT.md)
* 📊 **Recovery Benchmarking Data:** [benchmark/summary.md](./benchmark/summary.md)
* ⚡ **Load Testing Performance Results:** [loadtest/RESULTS.md](./loadtest/RESULTS.md)
* 📘 **System Architecture & Quickstart:** [README.md](./README.md)
