# local/009-repair-org-chart-layout

Benchmark task for evaluating whether an agent can repair a flawed draw.io
corporate organizational chart and export a clean PNG.

## Task summary

- The flawed input diagram is available at `/app/input/org_chart.drawio`.
- The agent must generate a repaired draw.io source file at `/app/corporate_org_chart.drawio`.
- The agent must export a PNG preview at `/app/corporate_org_chart.png`.
- The target diagram is a color-coded hierarchy with Co-Chairmen, CEO, COO,
  CFO/CTO/CCO branches, and their subordinates.

## Verifier

`tests/test.sh` first checks that the PNG exists. It then runs four separate
LLM image-judge calls:

1. all target boxes are present
2. connection lines are not jagged or messy
3. boxes do not overlap
4. the overall chart matches the requested corporate org-chart structure

Reward is `0` if the PNG is missing. Otherwise reward is the fraction of the
four visual judge checks that pass: `0.25`, `0.5`, `0.75`, or `1`.
