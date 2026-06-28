Given `/app/input/building.osm`, run an EnergyPlus simulation for only the gym, auditorium, and gym audience portion of the school.

Inputs:
- `/app/input/building.osm`: the school ComStock OpenStudio model
- `/app/input/weather.epw`: the weather file to use for the simulation

Required final outputs:
- `/app/artifacts/gym_auditorium_only.osm`: the reduced OpenStudio model you simulated
- `/app/artifacts/generated_building.idf`: the IDF translated from that reduced model
- `/app/artifacts/energyplus_run/eplusout.sql`: the EnergyPlus SQL output from the scoped simulation
- `/app/artifacts/energyplus_run/eplusout.end`
- `/app/artifacts/energyplus_run/eplusout.err`
