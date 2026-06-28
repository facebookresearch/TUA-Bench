# local/008-find-bird-chase-frames

Benchmark task for evaluating whether an agent can localize an event in a video
by frame number.

The agent receives `/app/input/18585469.mp4` and must write the start and end
frame numbers for the segment where the person chasing the bird appears.

The verifier checks `/app/result.txt` against the hidden frame range with a
10-frame tolerance on both endpoints.
