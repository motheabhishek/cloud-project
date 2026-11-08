import argparse, glob, hashlib, json, os

INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query",
           "calendar_remove", "weather_query", "datetime_query", "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}

ap = argparse.ArgumentParser()
ap.add_argument("--shards", default="results/teacher")
ap.add_argument("--out-dir", default="results/clean")
ap.add_argument("--upload", action="store_true", help="upload to SeaweedFS (needs S3_* env vars)")
args = ap.parse_args()

records = []
for path in sorted(glob.glob(f"{args.shards}/shard-*.jsonl")):
    for line in open(path):
        if line.strip():
            records.append(json.loads(line))
records.sort(key=lambda r: r["id"])

counts = {"input": len(records), "bad_json": 0, "bad_keys": 0,
          "bad_intent": 0, "bad_slot": 0, "duplicates": 0, "kept": 0}
kept, seen = [], set()

for r in records:
    try:
        obj = json.loads(r["teacher_raw"])
    except Exception:
        counts["bad_json"] += 1; continue
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        counts["bad_keys"] += 1; continue
    if obj["intent"] not in INTENTS:
        counts["bad_intent"] += 1; continue
    ok = True
    for k in ("date", "time", "place"):
        v = obj[k]
        if v is not None and not (isinstance(v, str) and v in r["text"]):
            ok = False
    if not ok:
        counts["bad_slot"] += 1; continue
    if r["text"] in seen:
        counts["duplicates"] += 1; continue
    seen.add(r["text"])
    kept.append(r)
    counts["kept"] += 1

total = sum(counts[k] for k in ("bad_json", "bad_keys", "bad_intent", "bad_slot", "duplicates", "kept"))
assert total == counts["input"], "counts do not add up"

os.makedirs(args.out_dir, exist_ok=True)
train = os.path.join(args.out_dir, "train.jsonl")
with open(train, "w") as f:
    for r in kept:
        f.write(json.dumps({"id": r["id"], "text": r["text"], "teacher_raw": r["teacher_raw"]}) + "\n")
digest = hashlib.sha256(open(train, "rb").read()).hexdigest()
open(os.path.join(args.out_dir, "train.sha256"), "w").write(f"{digest}  train.jsonl\n")
json.dump(counts, open(os.path.join(args.out_dir, "counts.json"), "w"), indent=2)
print(json.dumps(counts, indent=2)); print("sha256", digest)

if args.upload:
    import boto3
    s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT", "http://localhost:8333"),
                      aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                      aws_secret_access_key=os.environ["S3_SECRET_KEY"], region_name="us-east-1")
    for name in ("train.jsonl", "train.sha256"):
        s3.upload_file(os.path.join(args.out_dir, name), "datasets", f"v1/{name}")
    for p in sorted(glob.glob(f"{args.shards}/shard-*.jsonl")):
        s3.upload_file(p, "datasets", f"teacher/{os.path.basename(p)}")
    print("uploaded to datasets/v1/ and datasets/teacher/")
