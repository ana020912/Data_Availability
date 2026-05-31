#!/usr/bin/env python3
"""
Microbenchmark isolating the retrieval pattern that the composite-key design changes.

Model
-----
Custody events are stored under composite keys (case, evidence, seq). In Hyperledger
Fabric the state DB (LevelDB) keeps keys in lexicographic order, so a partial-key
query GetStateByPartialCompositeKey(case) returns every event of a case via ONE
ordered range scan. The naive alternative is an N+1 pattern: one query to find the
k evidence items of a case, then k independent history lookups (k+1 store accesses).

We reproduce both patterns on a file-backed, index-ordered embedded store (sqlite3
with a composite index on (case_id, evidence_id, seq)). This isolates the access
pattern. It is NOT a full Fabric-network benchmark (no consensus, endorsement, or
gossip); that is stated as a limitation in the paper.
"""
import sqlite3, os, time, random, statistics, csv

random.seed(20260531)
DB = "custody_bench.sqlite"
if os.path.exists(DB):
    os.remove(DB)

EVENTS_PER_EVIDENCE = 5          # register, request, approve, analysis, complete
N_CASES = 6000
K_MAX = 50                       # max evidence items per case
PAYLOAD = "x" * 64               # small metadata blob (hash + role + ts placeholder)

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("PRAGMA journal_mode=WAL;")
cur.execute("""CREATE TABLE events(
    case_id INTEGER, evidence_id INTEGER, seq INTEGER, payload TEXT)""")

# Build dataset: each case has k evidence items, k drawn uniformly in [1, K_MAX].
case_k = {}
rows = []
for c in range(N_CASES):
    k = random.randint(1, K_MAX)
    case_k[c] = k
    for e in range(k):
        for s in range(EVENTS_PER_EVIDENCE):
            rows.append((c, e, s, PAYLOAD))
random.shuffle(rows)                       # insert out of order: realistic
cur.executemany("INSERT INTO events VALUES(?,?,?,?)", rows)
con.commit()
# Composite, lexicographically-meaningful index == Fabric's sorted-key state model.
cur.execute("CREATE INDEX idx_ck ON events(case_id, evidence_id, seq)")
con.commit()
total_rows = len(rows)

def reconstruct_rangescan(cur, c):
    """One ordered partial-key scan -> models GetStateByPartialCompositeKey(case)."""
    cur.execute("SELECT evidence_id, seq, payload FROM events WHERE case_id=? "
                "ORDER BY evidence_id, seq", (c,))
    return cur.fetchall(), 1            # 1 store access

def reconstruct_nplus1(cur, c):
    """Discover k evidence ids, then k independent history lookups (N+1)."""
    cur.execute("SELECT DISTINCT evidence_id FROM events WHERE case_id=?", (c,))
    eids = [r[0] for r in cur.fetchall()]
    out = []
    for e in eids:                      # k independent probes
        cur.execute("SELECT evidence_id, seq, payload FROM events "
                    "WHERE case_id=? AND evidence_id=? ORDER BY seq", (c, e))
        out.extend(cur.fetchall())
    return out, 1 + len(eids)           # 1 + k store accesses

# Bucket cases by k, sample, and time each method.
from collections import defaultdict
buckets = defaultdict(list)
for c, k in case_k.items():
    buckets[k].append(c)

K_REPORT = [1, 2, 5, 10, 20, 30, 50]
REPEAT = 40                              # repeats per case for stable timing
results = []
# sanity: both methods must return identical event counts
for k in K_REPORT:
    cases = buckets[k][:120]             # up to 120 cases per k
    t_rs, t_np = [], []
    for c in cases:
        rs, ops_rs = reconstruct_rangescan(cur, c)
        np_, ops_np = reconstruct_nplus1(cur, c)
        assert len(rs) == len(np_) == k * EVENTS_PER_EVIDENCE, (len(rs), len(np_), k)
        # time range scan
        best = 1e9
        for _ in range(REPEAT):
            t0 = time.perf_counter_ns()
            reconstruct_rangescan(cur, c)
            best = min(best, time.perf_counter_ns() - t0)
        t_rs.append(best)
        # time N+1
        best = 1e9
        for _ in range(REPEAT):
            t0 = time.perf_counter_ns()
            reconstruct_nplus1(cur, c)
            best = min(best, time.perf_counter_ns() - t0)
        t_np.append(best)
    mrs = statistics.mean(t_rs) / 1000.0          # microseconds
    mnp = statistics.mean(t_np) / 1000.0
    results.append((k, ops_rs, 1 + k, mrs, mnp, mnp / mrs))

con.close()

print(f"dataset: {N_CASES} cases, {total_rows} event rows, "
      f"{EVENTS_PER_EVIDENCE} events/evidence, index on (case,evidence,seq)\n")
print(f"{'k':>3} {'ops_RS':>7} {'ops_N+1':>8} {'RS_us':>9} {'N+1_us':>9} {'speedup':>8}")
for k, ors, onp, mrs, mnp, sp in results:
    print(f"{k:>3} {ors:>7} {onp:>8} {mrs:>9.2f} {mnp:>9.2f} {sp:>7.2f}x")

with open("bench_results.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["k", "ops_rangescan", "ops_nplus1", "rangescan_us", "nplus1_us", "speedup"])
    w.writerows(results)
print("\nsaved bench_results.csv")
