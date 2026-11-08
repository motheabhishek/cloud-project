# Task 7 summary (measured, standard Locust run: 4 users, 2 min, 2 replicas)

| Measure | Value |
|---|---|
| Requests / failures | 336 / 3 (0.89%) |
| p50 / p95 | 1200 ms / 2800 ms |
| Throughput | 2.81 req/s |
| CPU per Pod (kubectl top) | 1943m and 1934m (limit 2000m) |
| Memory per Pod | 731 MiB and 769 MiB (limit 1 GiB) |
| Replica split | 165 / 168 (49.5% / 50.5%) |
| Cold start (median of 3) | 7 s |

Cost: (2 x 3.50 + 1 x 0.45) = 7.45 INR/replica/h; 2 replicas = 14.90 INR/h; 2.81 x 3600 = 10116 req/h; cost per 1000 requests = 14.90 / 10116 x 1000 = 1.47 INR.
SLO: 99% of requests succeed per run. Budget 3.36 requests; used 3 (89%).

| Component | Evidence (measured) | Limitation | Improvement |
|---|---|---|---|
| Data and storage | Model download of 7 files from SeaweedFS at each start | Single-node object storage, no replication | Replicated storage, model cached on a volume |
| Model quality | 3 of 336 outputs rejected as invalid (0.89%) | 70M student makes format and slot errors | More distillation data, constrained decoding |
| Latency and throughput | p50 1200 ms, p95 2800 ms, 2.81 req/s | CPU-bound; 1 CPU gave p95 7700 ms before the fix | Quantised model, batching |
| Resource utilisation | CPU 1943m of 2000m, memory 769 MiB of 1 GiB | Pods saturated at 4 users | Smaller model, more replicas on a multi-node cluster |
| Reliability and recovery | Cold start median 7 s; replicas split 49.5/50.5 | One node, so no real fault tolerance; HPA stuck at max 2 (189% vs 70% target) | Multi-node cluster, higher HPA maximum |
| Security and cost | Credentials from Kubernetes Secret s3-creds; 1.47 INR per 1000 requests | Secret is only base64; no TLS on Ingress | Sealed secrets, TLS, right-size CPU limit |

## Later runs on the cluster rebuilt with `make up` from a fresh clone
Pod names and timings differ from the first run above; the system was rebuilt and re-verified.

| Test | Measured result |
|---|---|
| Recovery (one Pod deleted under load) | 456 requests, 5 failures (1.10%), all HTTP 500 (consistent with the model invalid-output rate). Replacement Pod Ready in about 18 s. Two Ready Pods restored. |
| HPA scale up | 1 to 2 replicas at cpu 199% against a 70% target |
| HPA scale down | 2 to 1 replica about 5 minutes after load ended (from the HPA AGE column) |
| Second full run (during HPA test) | 843 requests, 9 failures (1.07%), p50 1500 ms, p95 3100 ms, 2.35 req/s |

SLO result: met in the standard run (99.11% success); narrowly missed in the recovery run (98.90%) and the HPA run (98.93%). The failures were all HTTP 500, consistent with the invalid-output rate of the model (about 1%).
Model quality (validation, 100 examples): student full-frame 29%, intent 71%, JSON validity 99%; teacher full-frame 39%, JSON validity 82%.
