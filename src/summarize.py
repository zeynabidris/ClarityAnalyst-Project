import json, pandas as pd
r = pd.DataFrame([json.loads(l) for l in open("results/results.jsonl")])
r = r[r.model != "mock"]
ans = r[r.type != "unanswerable"]
t = ans.groupby(["model", "config"]).agg(correct=("correct", "sum"), n=("correct", "size"), avg_sec=("seconds", "mean")).reset_index()
print("ANSWERABLE QUESTIONS\n", t.to_string(index=False))
b = r[r.config == "B"].groupby("model").exec_ok.agg(["sum", "size"]); print("\nB code execution success\n", b)
u = r[r.type == "unanswerable"][["model", "config", "correct", "final"]]; print("\nUNANSWERABLE (needs manual check)\n", u.to_string(index=False))
