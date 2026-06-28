# local/real-estate-openstudio-comstock-wa-osm-to-idf

This task uses a vendored OpenStudio CLI bundle with a ComStock OpenStudio
model and precomputed metadata derived from the matching timeseries parquet.

The agent must:

1. Forward-translate the supplied `.osm` model into an EnergyPlus `.idf`.
2. Parse the translated IDF for stable metadata.
3. Write a deterministic summary using task metadata derived from the source parquet.
4. Write both outputs to `/app` so the verifier can persist them as artifacts.
