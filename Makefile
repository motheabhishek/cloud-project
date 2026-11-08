CONFIG ?= training/config.yaml
CLUSTER ?= cloudproj
IMAGE ?= command-parser:v1c

.PHONY: train up cluster storage app down

train:
	python training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)

up: cluster storage app

cluster:
	k3d cluster create --config cluster/k3d.yaml
	kubectl wait --for=condition=Ready node --all --timeout=180s

storage:
	bash scripts/bootstrap.sh

app:
	docker build -t $(IMAGE) .
	k3d image import $(IMAGE) -c $(CLUSTER)
	kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml
	kubectl -n app rollout status deploy/parser --timeout=600s

down:
	k3d cluster delete $(CLUSTER)
