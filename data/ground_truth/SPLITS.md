# Ground truth splits and their use

The split of each manual is recorded in `data/manifests/manuals.json`. Counts below come
from `python -m src.evaluation.gt_stats --out results/week1/gt_stats.json`.

| Manual | Split | Components | Tri-sync candidates |
|---|---|---|---|
| Toshiba_SY_330 | dev | 158 | 135 |
| McIntosh_MC_2100 | test | 162 | 36 |

A tri-sync candidate is a component annotated in the parts list, the schematic and the PCB.
It is the denominator of T_link.

## Rules

- Thresholds, parameters and code are tuned on the dev manual only.
- A test manual is run and scored; only its aggregate numbers are read. Every run on a test
  manual is logged below with its date and what was looked at.
- A change that helps the dev manual and hurts a test manual is rejected.

## McIntosh_MC_2100

Its parts list covers about half of its components (87 of 162 have a parts list row), which
is why it has 36 candidates against 135 for Toshiba.

The same manual was inspected label by label in the AI-assisted repository on 2026-11-09 to
find two bugs. It is therefore not a clean test manual: a claim of generalization needs a
manual that nobody inspected.

On 2026-11-22 the file was replaced by the version corrected on 2026-11-11 in the
AI-assisted repository. Page 8 shows a schematic and a PCB layout; for C303, C304, R307 and
R310 the schematic box had been recorded as the PCB box and the schematic view was empty.
With the correction the candidates go from 34 to 36.

## Log of test manual runs

| Date | Manual | What was run | What was read |
|---|---|---|---|
