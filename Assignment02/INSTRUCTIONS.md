# HPC Batch Queue Simulation — Run & Validation Instructions

How to run the Python simulator and the GPSS World cross-validation model,
including the manual steps used to produce the validation results in the report.

## 1. Requirements

| Component | Needs |
|-----------|-------|
| Python simulator (`main.py`, `mmc_validation.py`, `doe_runner.py`) | Python 3.10+, standard library only |
| RNG validation (`rng_validation.py`) | Python 3.10+ and `numpy` + `scipy` (`pip install numpy scipy`) |
| GPSS model (`gpss/*.gps`) | GPSS World (Minuteman Software) |

Run all Python commands from the repository root so the local modules
(`simulator.py`, `queue_model.py`, `util.py`, `event.py`) are importable.

## 2. Repository layout

```
main.py              Entry point: HPC cluster run + M/M/1 validation
simulator.py         Event calendar (min-heap), trace mode
queue_model.py       QueueModel (one Kendall node) + Router (BPMN gateway)
util.py              Custom LCG generator + distribution samplers
event.py             Event with (time, priority) ordering
mmc_validation.py    M/M/c Erlang-C validation (multi-server check)
doe_runner.py        2^3 factorial DOE, R=10 replications, CRN
rng_validation.py    5-test RNG battery (custom LCG + Mersenne Twister)
gpss/
  hpc_validation_final.gps     GPSS cross-validation model (manual-run)
  hpc_lognormal_selftest.gps   Log-normal parametrisation self-test
  hpc_validation_results.csv   Raw per-replication GPSS results
doe/
  doe_results.csv              Raw per-replication DOE results (80 rows)
```

## 3. Running the Python simulation

### 3.1 Baseline HPC run (Section 3.1 of the report)

```bash
python3 main.py
```

This calls `run_hpc_cluster()` and prints per-partition statistics
(throughput, W_q, L_q, ρ, P_b) for Short / Standard / Long.

> Note: the baseline reported in the document (Standard W_q ≈ 3.97 h, no
> aging promotion) requires `aging=False`. The shipped `__main__` calls
> `run_hpc_cluster()` with the default `aging=True`, which enables promotion
> and gives different numbers. To reproduce the documented baseline, run with
> aging disabled, e.g. edit the call in `main.py` to `run_hpc_cluster(aging=False)`.

### 3.2 M/M/1 validation vs closed-form theory (Section 6.2)

In `main.py`, enable `run_single_queue_test()` in the `__main__` block
(it is commented out by default), then:

```bash
python3 main.py
```

Runs an M/M/1 queue (λ=1.5, μ=2.0, ρ=0.75, T=50,000 h) and prints the
simulated W_q against the theoretical `ρ/(μ−λ)`, with the percentage error.

### 3.3 M/M/c Erlang-C validation — multi-server check (Section 6.2)

```bash
python3 mmc_validation.py
```

Runs M/M/4 (λ=3.0, μ=1.0/server, ρ=0.75, T=80,000 h) and prints W_q, ρ and
L_q against the Erlang-C formula, plus a Little's Law cross-check
(L_q = λ·W_q). This is the only closed-form validation of the multi-server
dispatch path (every partition has c > 1).

### 3.4 Design of Experiments (Section 8)

```bash
python3 doe/doe_runner.py 10      # 10 replications per cell (default)
```

Prints the 8-cell 2³ factorial table (mean ± 95% CI) and the main/interaction
effects with confidence intervals. Uses common random numbers (CRN): every
stream is seeded by replication index only, so cells that differ only in
c_Standard produce identical Short/Long realisations.

## 4. Random number generation — custom RNG

The simulation draws from a **custom linear congruential generator (LCG)**,
not Python's built-in `random` module, and the statistical test battery is
applied to that same generator.

### 4.1 The generator

`util.LCG` implements the recurrence with the assignment's constants:

```python
class LCG:
    def __init__(self, seed=42, a=1103515245, c=12345, m=2**31):
        self.a, self.c, self.m = a, c, m
        self.state = seed % m
    def random(self):
        self.state = (self.a * self.state + self.c) % self.m
        return self.state / self.m
```

Non-uniform variates are derived from this uniform stream by transform
(no calls to `random.*`):

- `exponential(rate, rng)` — inverse transform: `t = -ln(1-u)/rate`
  (inter-arrival times and M/M service).
- `lognormal(mean, cv, rng)` — Box–Muller from two custom uniforms gives a
  standard normal `Z`, then `exp(μ + σ·Z)` with
  `σ² = ln(1+cv²)`, `μ = ln(mean) − σ²/2` (G service, SD_01).

Each independent stream gets its own `LCG` instance:

| Stream | Seed (baseline) | Use |
|--------|-----------------|-----|
| 1 | `seed`   | arrivals + routing |
| 2 | `seed+1` | Short service |
| 3 | `seed+2` | Standard service |
| 4 | `seed+3` | Long service |

`doe_runner.py` uses the same scheme seeded by replication index only
(`LCG(1000+rep)`, `LCG(2000+rep)`, …) for common random numbers.

### 4.2 Validating the generator

```bash
python3 rng_validation.py
```

Applies a five-test battery at N=10,000, α=0.05 to the custom LCG
(and, for comparison, to Python's Mersenne Twister):

| Test | Detects | H0 |
|------|---------|-----|
| Frequency (KS) | Global non-uniformity over [0,1) | x ~ Uniform(0,1) |
| Gap | Clustering / voids between hits in [0,0.5) | gaps ~ Geometric(0.5) |
| Order (d=4) | Higher-dimensional correlation in 4-tuples | all 4! orders equally likely |
| Runs (up/down) | Trends / oscillation | run count ~ independence |
| Serial (lag-1) | Correlation between consecutive draws | corr(xᵢ, xᵢ₊₁)=0 |

A p-value ≥ 0.05 fails to reject H0 ("appears random"). The custom LCG passes
all five at N=10,000. `rng_validation.generate_lcg()` draws from `util.LCG`, so
the tested stream is exactly the one feeding the simulation.

## 5. Running the GPSS cross-validation (manual steps)

### 5.1 Log-normal parametrisation self-test

1. Open `gpss/hpc_lognormal_selftest.gps` in GPSS World.
2. `Command → Create Simulation`, then `START` as instructed in the file.
3. Read the recorded variate's mean and standard deviation.
4. Confirm MEAN ≈ 2.0, STD.DEV ≈ 3.0, CV ≈ 1.5 — verifying that
   `LogNormal(stream, 0, 0.103820, 1.085659)` reproduces SD_01
   (μ = ln2 − σ²/2 = 0.103820, σ = √ln(1+1.5²) = 1.085659).

### 5.2 The cross-validation model

Open `gpss/hpc_validation_final.gps`. Pick the scenario by editing the
arrival `GENERATE` line (mean inter-arrival time, IAT = 1/λ):

| Scenario | λ (jobs/h) | IAT to enter | Offered ρ_Standard |
|----------|-----------|--------------|--------------------|
| Saturated baseline | 45 | `0.022222` | ≈ 1.13 |
| High-subcritical (priority point) | 38 | `0.026316` | ≈ 0.95 |
| Moderate | 30 | `0.033333` | ≈ 0.75 |

```
GENERATE  (Exponential(1,0,0.022222))   ; edit the third argument per scenario
```

### 5.3 Manual run procedure (per replication)

The model uses a 500 h warm-up followed by a 4000 h collection window,
implemented as two single-shot timer transactions. Repeat for each of the
5 replications, using a new seed set each time:

```
1.  RMULT  s1,s2,s3,s4      ; 4 distinct seeds (stream 1=arrivals/routing,
                            ;  2/3/4 = Short/Standard/Long service)
2.  START  1,NP             ; runs to clock = 500  (warm-up timer fires)
3.  SAVEVALUE SARR,0        ; zero the Standard arrival counter
4.  SAVEVALUE SBLK,0        ; zero the Standard blocked counter
5.  START  1,NP             ; runs to clock = 4500 (collection = 4000 h)
6.  (read results — see 5.4)
7.  CLEAR                   ; then return to step 1 with a NEW seed set
```

Resetting `SARR`/`SBLK` at the warm-up boundary makes P_b reflect the
collection window only. The 5 seed sets used for the reported results were
`(11,22,33,44)`, `(12,23,34,45)`, `(13,24,35,46)`, `(14,25,36,47)`,
`(15,26,37,48)` (see `gpss/hpc_validation_results.csv`).

### 5.4 Reading the results

Type these into the Command / Journal window after step 5:

```
SHOW QT$SH_WAIT          -> W_q Short    (hours)
SHOW QT$STD_WAIT         -> W_q Standard
SHOW QT$LONG_WAIT        -> W_q Long
SHOW SR$SHORT_SRV/1000   -> rho Short
SHOW SR$STD_SRV/1000     -> rho Standard
SHOW SR$LONG_SRV/1000    -> rho Long
SHOW X$SBLK/X$SARR       -> P_b Standard
```

If your GPSS World version won't evaluate the division inside `SHOW`, read the
raw `SR$...` and `X$...` values and divide manually.

## 6. Reproducing the reported validation

| Result | Command / procedure | Expected |
|--------|---------------------|----------|
| M/M/1 (Section 6.2) | §3.2 | W_q ≈ 1.5 h vs theory 1.5 |
| M/M/4 Erlang-C (Section 6.2) | §3.3 | W_q ≈ 0.51 vs theory 0.509 |
| RNG battery (Annex A) | §4.2 | custom LCG passes all 5 tests |
| Log-normal self-test (Section 6.3) | §5.1 | mean 2.0, CV 1.5 |
| GPSS λ=45 (Section 6.3) | §5.2–5.4 at IAT 0.022222 | W_q Std ≈ 3.94, P_b ≈ 0.111 |
| GPSS λ=38 (Section 6.3) | §5.2–5.4 at IAT 0.026316 | W_q Std ≈ 0.50 |
| DOE (Section 8) | §3.4 | 8-cell table + effects |

> The Python numeric results in the report were originally produced with
> Python's Mersenne Twister. Now that the engine draws from the custom LCG,
> re-run §3 and §3.4 to regenerate the baseline and DOE tables before quoting
> exact figures; the distributions are unchanged so values shift only slightly.
