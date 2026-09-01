# TOSEM revision experiments

This directory defines the outcome-independent eight-executable validation
set and the campaign matrix for the TOSEM revision.

## Selection

The subject in each domain is the eligible executable with the largest static
function count. Driver count breaks ties. The selected subjects are `snort`,
`ffmpeg`, `git`, `pdftops`, `cppcheck`, `python`, `upx`, and `h5dump`.

## Planning and validation

### 1. Build and preflight the selected subjects

Build the project tools and eight selected benchmarks using the repository's
normal build procedure. Before any long campaign, confirm for every subject:

- `cmdspec.yaml` and `drivers/driver_list.json` exist;
- the instrumented target and `fuzzPilot` launch successfully;
- every configured driver accepts at least one initial seed;
- function and CFG-edge coverage are recorded;
- the output filesystem has enough free space.

Run the integration test for checkpoint recovery:

```sh
python3 experiments/tests/test_resume.py
```

### 2. Fix the single-driver baselines

Set `best_driver_id` for every subject in `subjects.json`. Select these IDs
using independent pilot data, or document that they are oracle upper-bound
baselines derived from the original study. Do not select them using outcomes
from the new temporal campaigns.

### 3. Generate and inspect the plan

```sh
python3 experiments/run_campaigns.py plan
python3 experiments/run_campaigns.py validate
```

The commands create `experiment-results/plan.csv`. Validation intentionally
fails until every selected target is built and each `best_driver_id` in
`subjects.json` is filled from an independent pilot or explicitly documented
oracle-baseline rule.

The configured matrix contains 168 campaigns: 48 temporal campaigns, 48
queue-policy campaigns, and 72 scheduling campaigns. Each condition has three
independent trials. At eight concurrent jobs, the unreduced matrix represents
6,336 CPU-hours (33 ideal wall-clock days).

### 4. Run a smoke campaign

Run one campaign before submitting the complete matrix:

```sh
python3 experiments/run_campaigns.py run \
  --run-id temporal__snort3__snort__mfuzz__t01
```

For the first smoke test, temporarily use a short-duration copy of
`experiments.json`; do not edit the registered production matrix after
collecting outcomes. Check `coverage.csv`, `driver_windows.csv`, final graph
artifacts, and `checkpoint.json` before starting the full array.

### 5. Launch with eight concurrent jobs

For a cluster, generate a bounded Slurm array after reviewing `plan.csv`:

```sh
python3 experiments/emit_slurm_array.py \
  --plan experiment-results/plan.csv \
  --results experiment-results \
  --output experiment-results/run-array.sh --max-concurrent 8
```

Review the generated script and submit it with `sbatch`. Re-submitting the same
array is safe: completed runs are skipped and incomplete runs resume. On a
non-Slurm host, invoke individual `--run-id` commands from `plan.csv` with at
most eight simultaneous processes.

### 6. Monitor and recover

For each run, inspect `status.json`, `progress.json`, and the latest log tail.
After an ordinary process failure, resubmit the same run ID. After a host
restart, resubmit the same array. Never delete a run directory to recover it.
Use `--force` only when intentionally discarding the logical completion state
and starting a scientifically new campaign.

## Required MFuzz revision CLI

The legacy MFuzz binary is not sufficient for these experiments. The runner
uses the following explicit contract:

```text
mfuzz --benchmark DIR --duration SECONDS --output-dir DIR \
  --schedule fixed_round_robin|random_round|coverage_progress|single \
  --queue-policy shared|independent --window SECONDS \
  --checkpoint SECONDS --random-seed INTEGER --elapsed-offset SECONDS \
  [--drivers ID[,ID...]] [--resume]
```

Each run directory must retain, rather than delete:

- `coverage.csv` with elapsed seconds, covered call-graph nodes, and CFG edges;
- `driver_windows.csv` with driver, start/end time, allocation, and new global coverage;
- `seed_provenance.csv` for shared-queue runs;
- final driver-indexed graph/profile artifacts;
- crashes and replay metadata;
- the resolved configuration and tool versions.

Campaign output must be isolated under `--output-dir`; benchmark-local shared
`fuzz/` directories are unsafe for repeated or concurrent trials.

## Shutdown recovery

Long campaigns are executed as one-hour segments. After each successful
segment, `progress.json` is atomically replaced with the completed elapsed
time and full segment record. Restarting the same run command:

- skips campaigns whose `status.json` is `complete`;
- reclaims a stale lock left by a dead process or host shutdown;
- reads `progress.json` and starts at the last completed hour;
- passes `--resume` and `--elapsed-offset` to MFuzz;
- reruns only the interrupted segment, losing at most one hour of work.

MFuzz must atomically persist its corpus, coverage maps, scheduler state,
driver queues, and PRNG state at the end of each segment. `--resume` must load
that state from `--output-dir`; otherwise the campaign runner refuses to claim
scientific continuity across segments.

The final operation of a successful MFuzz segment must atomically replace
`checkpoint.json` with at least `{"elapsed_seconds": N}`. On restart, the
runner reconciles this committed checkpoint with `progress.json`. This covers
shutdown after MFuzz commits a segment but before the runner records its
successful return.

Locks from another hostname are not reclaimed automatically because the run
may still be active on a shared filesystem. After independently confirming
that the other job is dead, pass `--recover-foreign-lock` once.

After campaigns complete, summarize each trial separately:

```sh
python3 experiments/summarize_coverage.py \
  --results experiment-results --experiment temporal
```

This produces raw checkpoint values and per-subject medians with bootstrap
intervals. It never unions trials. Inferential paired comparisons will be
added after the final condition names and baseline-selection procedure are
fixed.

Run the summarizer separately for all campaign families:

```sh
python3 experiments/summarize_coverage.py --results experiment-results --experiment temporal
python3 experiments/summarize_coverage.py --results experiment-results --experiment queue \
  --checkpoints 21600 43200 64800 86400
python3 experiments/summarize_coverage.py --results experiment-results --experiment scheduling \
  --checkpoints 21600 43200 64800 86400
```

Archive the exact manifests, plan, run directories, analysis outputs, Git
commit identifiers, build logs, and tool versions. Do not overwrite the raw
campaign directory when regenerating figures or tables.

## Analysis-only experiments

Backbone and community-detection sensitivity should consume retained campaign
profiles. They must not launch new fuzzing campaigns. Seed/driver factorial
experiments receive a separate eligibility manifest after compatible input
formats and independently sampled corpora have been established.

The required offline variants and outputs are fixed in `analysis.json`.
Deterministic seed-size samples can be prepared without modifying source
corpora:

```sh
python3 experiments/prepare_seed_samples.py \
  --source PATH/TO/OSS_FUZZ_CORPUS --output experiment-inputs/SUBJECT \
  --sizes 10 50 100 --replicates 3
```

The generated manifest records the PRNG seed, source path, copied filename,
and SHA-256 digest of every sampled input. Corpus sizes must be chosen after
inspecting available corpus counts but before observing fuzzing outcomes.

Driver-count portfolios are generated independently of coverage outcomes:

```sh
python3 experiments/prepare_driver_portfolios.py \
  --driver-list benchmarks/snort3/snort/drivers/driver_list.json \
  --output experiment-inputs/snort-portfolios.json \
  --sizes 1 2 4 8 9 --replicates 3
```

The full driver set appears once; smaller sizes receive up to three distinct,
deterministically sampled portfolios. The campaign runner's `--drivers`
contract allows these portfolios to be scheduled with the same target-level
budget.
