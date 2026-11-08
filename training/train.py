import argparse, csv, hashlib, json, os, random
import numpy as np, torch, yaml
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="training/config.yaml")
ap.add_argument("--subset", type=int, default=0)
args = ap.parse_args()
cfg = yaml.safe_load(open(args.config))
seed = cfg["seed"]
random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
n = args.subset or cfg["n_train"]
recs = [json.loads(l) for l in open(cfg["train_file"]) if l.strip()][:n]
tok = AutoTokenizer.from_pretrained(cfg["base_model"])
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(cfg["base_model"]).float()

def encode(r):
    p = tok(f"Command: {r['text']}\nJSON:")["input_ids"]
    t = tok(" " + r["teacher_raw"])["input_ids"] + [tok.eos_token_id]
    ids = (p + t)[:cfg["max_len"]]
    labels = ([-100] * len(p) + t)[:cfg["max_len"]]
    return ids, labels

data = [encode(r) for r in recs]
print("training examples:", len(data), flush=True)

def batchify(items):
    m = max(len(i) for i, _ in items)
    ids = torch.full((len(items), m), tok.pad_token_id)
    lab = torch.full((len(items), m), -100)
    att = torch.zeros((len(items), m), dtype=torch.long)
    for k, (i, l) in enumerate(items):
        ids[k, :len(i)] = torch.tensor(i)
        lab[k, :len(l)] = torch.tensor(l)
        att[k, :len(i)] = 1
    return ids, att, lab

opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"])
g = torch.Generator().manual_seed(seed)
out_dir = "models/subset-test" if args.subset else cfg["output_dir"]
loss_csv = "training/loss_subset.csv" if args.subset else cfg["loss_csv"]
rows = []
model.train()
for ep in range(1, cfg["epochs"] + 1):
    order = torch.randperm(len(data), generator=g).tolist()
    tot, nb = 0.0, 0
    for s in range(0, len(order), cfg["batch_size"]):
        ids, att, lab = batchify([data[j] for j in order[s:s + cfg["batch_size"]]])
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        loss.backward(); opt.step(); opt.zero_grad()
        tot += loss.item(); nb += 1
    rows.append((ep, round(tot / nb, 6)))
    print(f"epoch {ep}: loss {tot / nb:.4f}", flush=True)

with open(loss_csv, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["epoch", "train_loss"]); w.writerows(rows)
os.makedirs(out_dir, exist_ok=True)
model.save_pretrained(out_dir); tok.save_pretrained(out_dir)
json.dump({"version": cfg["version"], "base_model": cfg["base_model"], "seed": seed,
           "n_train": len(data), "epochs": cfg["epochs"], "learning_rate": cfg["learning_rate"],
           "torch": torch.__version__, "transformers": transformers.__version__},
          open(os.path.join(out_dir, "version.json"), "w"), indent=2)
with open(os.path.join(out_dir, "model.sha256"), "w") as f:
    for name in sorted(os.listdir(out_dir)):
        if name != "model.sha256":
            h = hashlib.sha256(open(os.path.join(out_dir, name), "rb").read()).hexdigest()
            f.write(f"{h}  {name}\n")
print("saved to", out_dir)
