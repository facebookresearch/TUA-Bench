# local/003-rebuild-energy-model

This task exposes only an annotated floor plan PNG and the matching EPW weather
file to the agent. The full render pack and exact reference model stay hidden in
the task codebase for oracle generation and offline evaluation.

The agent must:

1. Read the floor plan sheet and reconstruct an OpenStudio `.osm` model.
2. Translate that model to EnergyPlus `.idf`, append the required meters, and
   run the real simulator with the supplied EPW.
3. Render review PNGs from the reconstructed model.
4. Write model, simulation, render, and summary artifacts under `/app/artifacts`.

Available local tools include:

- `openstudio`
- bundled `EnergyPlus`
- `tesseract` for OCR
- `/opt/task-support/render_openstudio_model.py` for mesh-based floorplan and 3D PNG rendering

The verifier checks annual energy totals against hidden EnergyPlus SQL ground
truth with `1%` relative tolerance. All agent artifacts are still copied out
for manual review.
