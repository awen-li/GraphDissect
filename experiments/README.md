# TOSEM revision experiments

This directory defines the outcome-independent eight-executable validation
set and the campaign matrix for the TOSEM revision.

The normal workflow uses only two entry scripts:

```sh
python3 tools/experiments/run_experiments.py
python3 tools/experiments/collect_data.py
```

The first validates and runs all experiments with one worker for each of the
eight executables. Re-running it resumes interrupted campaigns. The second
refuses incomplete datasets by default and produces all analysis-ready CSVs.

Regenerate only the drivers for the eight selected subjects with:

```sh
tools/regenerate_drivers.sh --selected
```

Use `tools/regenerate_drivers.sh --all` for every non-baseline executable.
The script does not rebuild targets or run fuzzing experiments.

Every campaign has a separate output directory:

```text
experiment-results/runs/<experiment>/<benchmark>/<executable>/<condition>/trial-<NN>/
```

For example:

```text
experiment-results/runs/temporal/snort3/snort/mfuzz/trial-01/
experiment-results/runs/queue/snort3/snort/shared/trial-01/
experiment-results/runs/scheduling/snort3/snort/progress/trial-01/
```

MFuzz keeps its existing benchmark-local output behavior. After each one-hour
segment, the runner copies mutable runtime artifacts into the corresponding
campaign directory before another condition can use that executable.

Only mutable fuzzing and runtime results are isolated. The following benchmark
artifacts remain shared, read-only inputs across all experiments and trials:

- executable binaries and instrumentation metadata;
- `cmdspec.yaml`;
- per-driver JSON definitions and the canonical `drivers/driver_list.json`;
- original driver seed metadata and auxiliary configuration files;
- the whole-program static call-graph backbone and function-address map.

For the single-driver condition, the runner uses the existing one-driver
subject under `benchmarks/baseline/<benchmark>/<executable>/`; it does not edit
the multi-driver subject. Runtime snapshots include `driver_runtimes/`,
`fuzz/`, the final marked graph, and MFuzz/honggfuzz logs; driver definitions
are not duplicated.

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
python3 tools/experiments/tests/test_resume.py
```

### 2. Verify the single-driver baselines

Each selected subject must have a one-entry configuration at
`benchmarks/baseline/<benchmark>/<executable>/drivers/driver_list.json`. These
are the established single-driver configurations from the original study.

### 3. Generate and inspect the plan

```sh
python3 tools/experiments/run_campaigns.py plan
python3 tools/experiments/run_campaigns.py validate
```

The commands create `experiment-results/plan.csv`. Validation checks the
multi-driver directory for MFuzz conditions and the corresponding baseline
directory for the single-driver condition.

The configured matrix contains 168 campaigns: 48 temporal campaigns, 48
queue-policy campaigns, and 72 scheduling campaigns. Each condition has three
independent trials. At eight concurrent jobs, the unreduced matrix represents
6,336 CPU-hours (33 ideal wall-clock days).

### 4. Run a smoke campaign

Run one campaign before submitting the complete matrix:

```sh
python3 tools/experiments/run_campaigns.py run \
  --run-id temporal__snort3__snort__mfuzz__t01
```

For the first smoke test, temporarily use a short-duration copy of
`experiments.json`; do not edit the registered production matrix after
collecting outcomes. Check `coverage.csv`, `checkpoints/`, final graph
artifacts, and the MFuzz/honggfuzz logs before starting the full array.

### 5. Launch with eight concurrent jobs

For a cluster, generate a bounded Slurm array after reviewing `plan.csv`:

```sh
python3 tools/experiments/emit_slurm_array.py \
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

## Minimal MFuzz options

Output isolation and segment bookkeeping stay in the experiment runner. MFuzz
uses its original `-b` and `-t` arguments plus four small policy options:

```text
mfuzz -b DIR -t SECONDS -s fixed|random|progress \
  -q shared|independent -w WINDOW_SECONDS -r RANDOM_SEED
```

Each run directory must retain, rather than delete:

- `coverage.csv` with elapsed seconds, covered call-graph nodes, and CFG edges;
- `driver_windows.csv` with driver, start/end time, allocation, and new global coverage;
- `seed_provenance.csv` for shared-queue runs;
- final driver-indexed graph/profile artifacts;
- crashes and replay metadata;
- the resolved configuration and tool versions.

Shared driver definitions and the unmodified static call-graph backbone should
be referenced from run provenance rather than copied into every trial. Record
their paths and content hashes so every runtime result can be tied to the exact
shared inputs used.

Only one campaign per executable runs at a time, so two campaigns never write
the same benchmark-local `fuzz/` directory. Different executables may run
concurrently.

## Shutdown recovery

Long campaigns are executed as one-hour segments. After each successful
segment, runtime artifacts are copied and `progress.json` is atomically
replaced with the completed elapsed time and full segment record. Restarting
the same run command:

- skips campaigns whose `status.json` is `complete`;
- reclaims a stale lock left by a dead process or host shutdown;
- reads `progress.json` and starts at the last completed hour;
- reuses MFuzz's benchmark-local corpus and runs only the remaining segments;
- reruns the interrupted segment, losing at most one hour of accounted time.

This is segment-level continuation, not an exact in-process scheduler
checkpoint. The corpus persists, but MFuzz reconstructs its scheduler when a
new segment starts. Provenance and segment records make that boundary explicit;
exact scheduler-state resume would require a substantially larger MFuzz change.

Locks from another hostname are not reclaimed automatically because the run
may still be active on a shared filesystem. After independently confirming
that the other job is dead, pass `--recover-foreign-lock` once.

After campaigns complete, summarize each trial separately:

```sh
python3 tools/experiments/summarize_coverage.py \
  --results experiment-results --experiment temporal
```

This produces raw checkpoint values and per-subject medians with bootstrap
intervals. It never unions trials. Inferential paired comparisons will be
added after the final condition names and baseline-selection procedure are
fixed.

Run the summarizer separately for all campaign families:

```sh
python3 tools/experiments/summarize_coverage.py --results experiment-results --experiment temporal
python3 tools/experiments/summarize_coverage.py --results experiment-results --experiment queue \
  --checkpoints 21600 43200 64800 86400
python3 tools/experiments/summarize_coverage.py --results experiment-results --experiment scheduling \
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
python3 tools/experiments/prepare_seed_samples.py \
  --source PATH/TO/OSS_FUZZ_CORPUS --output experiment-inputs/SUBJECT \
  --sizes 10 50 100 --replicates 3
```

The generated manifest records the PRNG seed, source path, copied filename,
and SHA-256 digest of every sampled input. Corpus sizes must be chosen after
inspecting available corpus counts but before observing fuzzing outcomes.

Driver-count portfolios are generated independently of coverage outcomes:

```sh
python3 tools/experiments/prepare_driver_portfolios.py \
  --driver-list benchmarks/snort3/snort/drivers/driver_list.json \
  --output experiment-inputs/snort-portfolios.json \
  --sizes 1 2 4 8 9 --replicates 3
```

The full driver set appears once; smaller sizes receive up to three distinct,
deterministically sampled portfolios. The campaign runner's `--drivers`
contract allows these portfolios to be scheduled with the same target-level
budget.
