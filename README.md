# Running the experiment — audit reconstruction microbenchmark
This experiment reproduces the numbers in Table IV and Figure 3 of the paper: the comparison between the naive N+1 pattern and the composite-key pattern (a single ordered scan) for reconstructing a case's chain of custody.
What it actually measures
A case's custody events are stored under composite keys (case, evidence, seq) in an index-ordered, file-backed embedded store (sqlite3) — which models the sorted-key state store that Hyperledger Fabric keeps in LevelDB. The script reconstructs each case's full trail two ways and times both:

N+1 — one query to discover the case's k evidence items, then k independent lookups, one per item (k+1 accesses total).
Composite-key scan — a single ordered partial-key range scan that returns the whole, already-sorted trail (1 access, for any k). This is the analog of Fabric's GetStateByPartialCompositeKey(case).

Scope, stated honestly: the experiment isolates the retrieval access pattern. It does not model Fabric's consensus, endorsement, or gossip, so the absolute microseconds belong to the embedded store. The transferable results are the access count (1 vs k+1) and the trend as k grows. On different machines the absolute times will differ; the speedup ratio and the access counts will not.
Requirements

Python 3.8+ (3.10+ recommended).
bench.py uses only the standard library (sqlite3, time, random, statistics, csv) — nothing to install.
plot.py needs matplotlib (only if you want to regenerate the figure): pip install matplotlib.
Disk space: the generated custody_bench.sqlite is ~70 MB (plus small WAL files). Safe to delete afterward.

Files
bench.py builds the dataset, runs both retrieval patterns, prints a table, and writes bench_results.csv. plot.py reads bench_results.csv and writes bench_plot.pdf (Figure 3). bench_results.csv holds the raw numbers from Table IV. All paths are relative, so run the scripts from the folder that contains them.
How to run it
bash# 1) run the benchmark (prints the table, writes bench_results.csv)
python3 bench.py

# 2) optional: regenerate the figure from the results
python3 plot.py
That's it. The first command takes about a minute, most of which is building the dataset (~760k rows) and the composite index.
Expected output
A table like this (your absolute microseconds will differ; the speedup column and the access counts should match):
  k  ops_RS  ops_N+1     RS_us    N+1_us  speedup
  1       1        2      6.5       9.8     1.5x
  2       1        3     10.0      16.7     1.7x
  5       1        6     20.8      37.7     1.8x
 10       1       11     39.0      73.4     1.9x
 20       1       21     78.4     148.7     1.9x
 30       1       31    121.7     231.3     1.9x
 50       1       51    196.0     376.0     1.9x
Read it as: the composite-key scan stays at one access for any k, while N+1 grows to k+1; the measured time advantage widens from ~1.5× at k=1 to ~1.9× at k=50.
Tuning the experiment
The parameters live at the top of bench.py: N_CASES (default 6000, controls total DB size), K_MAX (50, the max evidence items per case, with k drawn uniformly in [1, K_MAX]), EVENTS_PER_EVIDENCE (5, custody events per item), REPEAT (40, timed repetitions per case — the script takes the minimum for stability), K_REPORT ([1,2,5,10,20,30,50], the reported values), the number of cases sampled per k (120), and random.seed (20260531, fixed for reproducibility — change it for a different draw). Raising N_CASES enlarges the dataset and each index probe, which tends to widen the N+1 disadvantage; lowering it shrinks both. The structural result (1 vs k+1 accesses) is invariant to these choices.
Built-in checks
bench.py uses assert to verify that both methods return the same number of events for each case (k * EVENTS_PER_EVIDENCE). If that assertion ever fails, the dataset or a query was changed in a way that breaks the comparison, and the run stops rather than reporting a misleading speedup.
Cleanup
bashrm -f custody_bench.sqlite custody_bench.sqlite-wal custody_bench.sqlite-shm
Feeding results back into the paper
plot.py writes bench_plot.pdf, which main.tex includes as Figure 3. If you rerun the benchmark and want the paper to reflect the new numbers, regenerate the figure and manually update the seven rows of Table IV in main.tex (the table is written out explicitly, so the source stays self-contained).
