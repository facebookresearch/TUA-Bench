# local/real-estate-openstudio-comstock-gym-auditorium-simulate

This task gives the agent the full WA ComStock building 100094 OpenStudio model
and asks it to produce an EnergyPlus simulation for only the gym, auditorium,
and gym audience spaces. The intent is to test whether the agent realizes the
whole-school model must be reduced before simulation.

The agent must:

1. Read `/app/input/building.osm`.
2. Create `/app/artifacts/gym_auditorium_only.osm` containing only the target
   gym/auditorium scope.
3. Translate that reduced model to `/app/artifacts/generated_building.idf`.
4. Run EnergyPlus with `/app/input/weather.epw`.
5. Save the run outputs under `/app/artifacts/energyplus_run/`, including
   `eplusout.sql`, `eplusout.end`, and `eplusout.err`.

The verifier checks that the expected artifacts exist, that the EnergyPlus run
completed successfully, and that key annual results in the agent's
`eplusout.sql` match the hidden gym/auditorium reference SQL within 1% relative
tolerance.
