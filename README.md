# Cloud Computing Mini Project (Roll 230101018)

Knowledge distillation of a command parser: a Phi-3.5 teacher (via Ollama) labels commands, and a Pythia-70M student is trained on the teacher's replies. The student is served from a local k3d Kubernetes cluster with SeaweedFS as object storage.

GitHub repository: https://github.com/motheabhishek/cloud-project
Final submission commit: tag `final`

## Prerequisites
Docker, k3d, kubectl, make, Python 3 with `boto3`, installed into the same `python3` that `make` uses (on macOS with Homebrew Python use a venv: `python3 -m venv venv && source venv/bin/activate && pip install boto3`, and run `make up` from that shell), curl, unzip, openssl. The repository must be able to download the model from the GitHub Release `v1.0` (no weights are stored in Git).

## Build and deploy (fresh clone)
    git clone https://github.com/motheabhishek/cloud-project
    cd cloud-project
    make up

`make up` runs three steps: (1) creates the k3d cluster from `cluster/k3d.yaml`; (2) `scripts/bootstrap.sh` creates the namespaces and Secrets (credentials are generated at run time, nothing is stored in Git), deploys SeaweedFS, creates the `datasets` and `models` buckets, uploads `commands_pool.jsonl`, and downloads the model from the GitHub Release into `models/v1/` and `models/v2/`; (3) builds the service image, imports it into the cluster, and deploys the app. The first run takes several minutes (image build and about 450 MB of model downloads).

## Test
    curl -s -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}'
    locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
    python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check
    python tools/score.py predictions.jsonl data/validation.jsonl --min-validity 95
    pytest -q tests

## Train
    make train
    make train SUBSET=50

## Tear down
    make down

## Layout
- `cluster/`, `k8s/`: cluster config and manifests (Deployment, Service, Ingress, HPA, SeaweedFS)
- `worker/`: sharded teacher labelling and `clean.py`
- `training/`: training code, `config.yaml`, loss files
- `service/`, `Dockerfile`: inference service
- `network/`: `subnets.md`, `nacl.json`
- `results/`: logs, score reports, Locust output
- `.github/workflows/`: CI pipeline (`ci.yml`)
- `data/`: command pool, validation set, schema, rate card
- `scripts/`: `bootstrap.sh`
- `tools/`: load test, NACL simulator, scoring script
- `tests/`: unit tests
- `prompts/`, `AI_USE.md`: prompts and AI-use record

## Notes and limitations
The cluster runs on one node, so it does not demonstrate fault tolerance across machines. The earlier measurements in `results/` come from the first cluster, which was later rebuilt with `make up` and re-verified.
