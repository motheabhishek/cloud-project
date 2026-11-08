GitHub repository: https://github.com/motheabhishek/cloud-project

# Cloud Computing Mini Project (Roll 230101018)

Knowledge distillation of a command parser (Phi-3.5 teacher to Pythia-70M student), deployed on a local k3d Kubernetes cluster.

## Layout
cluster/ (k3d config), k8s/ (manifests), service/ (FastAPI), training/, worker/, prompts/, network/ (subnets and NACL), tools/, tests/, results/ (evidence), report/report.pdf

## Build and deploy
    k3d cluster create --config cluster/k3d.yaml
    docker build -t command-parser:v1c .
    k3d image import command-parser:v1c -c cloudproj
    kubectl apply -f k8s/

## Test
    curl -X POST localhost:8080/parse -H "Content-Type: application/json" -d '{"text": "what is the weather in london"}'
    locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
    python tools/score.py results/pred_v1.jsonl data/validation.jsonl
    python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check

## Tear down
    k3d cluster delete cloudproj

Model weights are in the GitHub Release (model_v1.zip, model_v2.zip, checksums.txt), not in Git.
Read the project handout first. It explains every file here.

    data/commands_pool.jsonl     3,000 commands (text only)
    data/validation.jsonl        100 labelled commands, for evaluation only (never train on them)
    data/schema.json             the four keys, the eight intents and the slot rules
    data/rate_card.json          hypothetical prices for the cost exercise
    tools/score.py               python tools/score.py PREDICTIONS data/validation.jsonl [--min-validity 95]
    tools/locustfile.py          pip install locust, then:
                                 locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
    tools/nacl_sim.py            python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check
    network/packets_sample.jsonl six sample packets with expected decisions

score.py and nacl_sim.py need only Python 3 (standard library); run them with -h for help. The load test needs Locust (https://locust.io).

Data: commands from SLURP (Bastianelli et al., EMNLP 2020), licensed CC BY 4.0.
https://github.com/pswietojanski/slurp
