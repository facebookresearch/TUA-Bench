# local/002-count-enter-key-presses

Benchmark task for evaluating whether an agent can localize an event in a video
and count repeated actions.

The agent receives `/app/input/85229750.mp4` and must write how many times the
person hits the Enter key.

The verifier checks `/app/result.txt` against the hidden count.
