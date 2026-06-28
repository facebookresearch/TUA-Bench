# local/006-extract-gym-auditorium

This task gives the agent the full WA ComStock building 100094 OpenStudio model
and asks it to create a reduced OpenStudio model containing only the gym,
auditorium, and gym audience spaces.

The agent must:

1. Read `/app/input/building.osm`.
2. Write `/app/artifacts/gym_auditorium_only.osm`.
3. Preserve a valid OpenStudio model that can be translated and simulated with
   the supplied `/app/input/weather.epw`.

The verifier checks that the output OSM exists, that its actual spaces are only
gym/auditorium-related spaces and match the expected reduced model size/area,
and that the candidate model runs through EnergyPlus without severe or fatal
errors.
