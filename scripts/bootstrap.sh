#!/usr/bin/env bash
set -euo pipefail
REL=https://github.com/motheabhishek/cloud-project/releases/download/v1.0
AK=$(openssl rand -hex 8); SK=$(openssl rand -hex 16)

for ns in data app pipeline; do kubectl create ns $ns --dry-run=client -o yaml | kubectl apply -f -; done

cat > /tmp/s3.json << JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$AK","secretKey":"$SK"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweed-s3 --from-file=s3.json=/tmp/s3.json --dry-run=client -o yaml | kubectl apply -f -
kubectl -n app create secret generic s3-creds --from-literal=S3_ACCESS_KEY=$AK --from-literal=S3_SECRET_KEY=$SK --dry-run=client -o yaml | kubectl apply -f -
rm -f /tmp/s3.json

kubectl apply -f k8s/seaweedfs.yaml
kubectl -n data rollout status deploy/seaweedfs --timeout=300s


W=$(mktemp -d)
for v in v1 v2; do curl -fL -o $W/model_$v.zip $REL/model_$v.zip; unzip -q -o $W/model_$v.zip -d $W; done

kubectl -n data port-forward svc/seaweedfs 8333:8333 >/dev/null 2>&1 &
PF=$!; trap 'kill $PF 2>/dev/null' EXIT
for i in $(seq 30); do curl -s localhost:8333 >/dev/null && break; sleep 2; done
curl -s localhost:8333 >/dev/null || { echo "SeaweedFS port-forward not reachable"; exit 1; }
export AK SK W
python3 - << 'PY'
import boto3, os, glob
s3 = boto3.client("s3", endpoint_url="http://localhost:8333",
    aws_access_key_id=os.environ["AK"], aws_secret_access_key=os.environ["SK"], region_name="us-east-1")
for b in ("datasets", "models"):
    try: s3.create_bucket(Bucket=b)
    except Exception as e: print("bucket:", e)
s3.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
for v in ("v1", "v2"):
    for f in glob.glob(os.environ["W"] + "/" + v + "/*"):
        s3.upload_file(f, "models", "models/%s/%s" % (v, os.path.basename(f)))
print("uploaded")
PY
