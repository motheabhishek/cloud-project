import os, json, threading
import boto3, torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from transformers import AutoTokenizer, AutoModelForCausalLM

torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))

MODEL_URI = os.environ.get("MODEL_URI", "s3://models/models/v1/")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "64"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0")
POD = os.environ.get("HOSTNAME", "local")
LOCAL = "/tmp/model"
INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query",
           "calendar_remove", "weather_query", "datetime_query", "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}
state = {"model": None, "tok": None}
app = FastAPI()

def load():
    if MODEL_URI.startswith("file://"):
        path = MODEL_URI[len("file://"):]
        state["tok"] = AutoTokenizer.from_pretrained(path)
        state["tok"].pad_token = state["tok"].eos_token
        state["model"] = AutoModelForCausalLM.from_pretrained(path).float().eval()
        return
    bucket, _, prefix = MODEL_URI[len("s3://"):].partition("/")
    s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT or None,
                      aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
                      aws_secret_access_key=os.environ.get("S3_SECRET_KEY"))
    os.makedirs(LOCAL, exist_ok=True)
    print(f"Downloading model from s3://{bucket}/{prefix} via {S3_ENDPOINT}", flush=True)
    n = 0
    for o in s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", []):
        name = o["Key"].split("/")[-1]
        if name:
            s3.download_file(bucket, o["Key"], os.path.join(LOCAL, name))
            n += 1
    print(f"Downloaded {n} files from object storage", flush=True)
    state["tok"] = AutoTokenizer.from_pretrained(LOCAL)
    state["tok"].pad_token = state["tok"].eos_token
    state["model"] = AutoModelForCausalLM.from_pretrained(LOCAL).float().eval()

@app.on_event("startup")
def startup():
    threading.Thread(target=load, daemon=True).start()

def valid(d):
    if not isinstance(d, dict) or set(d) != KEYS or d["intent"] not in INTENTS:
        return False
    return all(d[k] is None or isinstance(d[k], str) for k in ("date", "time", "place"))

def generate(text):
    tok, model = state["tok"], state["model"]
    x = tok(f"Command: {text}\nJSON:", return_tensors="pt")
    with torch.no_grad():
        y = model.generate(**x, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, no_repeat_ngram_size=8,
                           pad_token_id=tok.pad_token_id)
    return tok.decode(y[0][x["input_ids"].shape[1]:], skip_special_tokens=True).strip()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/readyz")
def readyz():
    if state["model"] is None:
        return JSONResponse({"status": "loading"}, status_code=503)
    return {"status": "ready"}

@app.post("/parse")
def parse(body: dict):
    hdr = {"X-Model-Version": MODEL_VERSION, "X-Served-By": POD}
    if state["model"] is None:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=hdr)
    out = generate(str(body.get("text", "")))
    if FAULT_INJECT == "1":
        out = "not json"
    try:
        d = json.loads(out)
    except Exception:
        d = None
    if not valid(d):
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=hdr)
    return JSONResponse(d, status_code=200, headers=hdr)
