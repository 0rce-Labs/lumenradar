import glob
import json

from lumenradar.pipeline import analyze_source

rows = []
for p in sorted(glob.glob("dataset-mac/*.mp4")):
    r = analyze_source(p)
    name = p.split("/")[-1]
    d = r["detection"]
    rows.append({"name": name, "roi_mode": r["roi"]["mode"], "det": d})
    status = d["status"]
    cls = str(d["signal_class"])
    print(
        f"{name:35s} roi={r['roi']['mode']:12s} -> {status:18s} "
        f"class={cls:10s} conf={d['confidence']} f={d['peak_freq_hz']}",
        flush=True,
    )
with open("docs/paper/results/mac_redetect.json", "w") as fh:
    json.dump(rows, fh, indent=1)
print("saved docs/paper/results/mac_redetect.json")
