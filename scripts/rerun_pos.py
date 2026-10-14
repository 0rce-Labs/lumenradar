import glob
import json
import time

from lumenradar.pipeline import analyze_source

t0 = time.time()
rows = []
for p in sorted(glob.glob("dataset-mac/pos_*.mp4")):
    r = analyze_source(p)
    name = p.split('/')[-1]
    d = r['detection']
    rows.append({"name": name, "roi": r['roi'], "det": d})
    print(
        f"{name:35s} roi={r['roi']['mode']:12s} -> {d['status']:18s} "
        f"class={str(d['signal_class']):10s} conf={d['confidence']} f={d['peak_freq_hz']}",
        flush=True,
    )
json.dump(rows, open('/tmp/mac_rerun_p2.json', 'w'))
print(f"DONE in {time.time()-t0:.0f}s", flush=True)
