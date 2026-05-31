#!/usr/bin/env python3
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

k, rs, npl = [], [], []
with open("bench_results.csv") as f:
    for row in csv.DictReader(f):
        k.append(int(row["k"]))
        rs.append(float(row["rangescan_us"]))
        npl.append(float(row["nplus1_us"]))

plt.rcParams.update({"font.size": 9, "font.family": "serif",
                     "axes.linewidth": 0.8, "figure.dpi": 150})
fig, ax = plt.subplots(figsize=(3.3, 2.25))
ax.plot(k, npl, "k--s", markersize=4, linewidth=1.1,
        label="N+1 lookups (k+1 accesses)")
ax.plot(k, rs, "k-o", markersize=4, linewidth=1.1,
        label="Composite-key scan (1 access)")
ax.set_xlabel("Evidence items per case, $k$")
ax.set_ylabel("Reconstruction time ($\\mu$s)")
ax.legend(frameon=False, fontsize=7.5, loc="upper left")
ax.grid(True, linewidth=0.3, alpha=0.5)
ax.margins(x=0.02)
fig.tight_layout(pad=0.3)
fig.savefig("bench_plot.pdf", bbox_inches="tight")
print("saved bench_plot.pdf")
