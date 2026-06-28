# local/real-estate-openstudio-comstock-epw-parquet-check

This task uses a vendored OpenStudio CLI bundle, a ComStock OpenStudio model,
its matching EPW weather file, and verifier-side reference energy totals.

The agent must:

1. Forward-translate the supplied `.osm` model into an EnergyPlus `.idf`.
2. Append required meter outputs in a deterministic way.
3. Run the real EnergyPlus simulator with the supplied `.epw` weather file.
4. Write simulation artifacts and a deterministic summary under `/app/artifacts`.

The verifier checks that the generated IDF is the expected translated model,
that the simulation artifacts exist, and that the annual energy totals stay
within the allowed tolerance of the hidden reference values.
