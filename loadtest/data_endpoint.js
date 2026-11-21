import http from 'k6/http';
import { check, sleep } from 'k6';

// Target URL configurable via environment variable
const TARGET_URL = __ENV.TARGET_URL || 'http://localhost:30080/data';

export const options = {
  stages: [
    { duration: '1m', target: 10 },  // Stage 1: Warm-up & low load (10 VUs)
    { duration: '1m', target: 50 },  // Stage 2: Target operating concurrency (50 VUs)
    { duration: '1m', target: 100 }, // Stage 3: High load (100 VUs)
    { duration: '1m', target: 200 }, // Stage 4: Stress & saturation threshold (200 VUs)
    { duration: '30s', target: 0 },  // Ramp-down
  ],
  thresholds: {
    // Assert p95 latency under 10ms for baseline NFR compliance
    'http_req_duration': ['p(95)<100'], // Global ceiling
    'http_req_duration{stage:10_vu}': ['p(95)<10'], // Strict NFR validation
    'http_req_duration{stage:50_vu}': ['p(95)<15'], // Normal operational load
    'http_req_failed': ['rate<0.01'],               // Less than 1% failure rate
  },
};

export default function () {
  const res = http.get(TARGET_URL, {
    tags: {
      endpoint: 'data',
    },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has valid payload': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'success' && body.data && body.data.LSEG !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  // 100ms think time between requests per virtual user
  sleep(0.1);
}
