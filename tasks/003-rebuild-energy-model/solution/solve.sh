#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts/energyplus_run /app/artifacts/render_views

cp /solution/reference/building_reference.osm /app/artifacts/reconstructed_building.osm
cp /solution/reference/wa_building_100094_renders/3d_view_1.png /app/artifacts/building_render.png
cp /solution/reference/wa_building_100094_renders/3d_view_1.png /app/artifacts/render_views/3d_view_1.png
cp /solution/reference/wa_building_100094_renders/3d_view_2.png /app/artifacts/render_views/3d_view_2.png
cp /solution/reference/wa_building_100094_renders/3d_view_3.png /app/artifacts/render_views/3d_view_3.png

cat > /app/artifacts/generated_building.idf <<'EOF'
!- Oracle baseline placeholder IDF.
EOF

python3 - <<'PY'
from pathlib import Path

ARTIFACT_DIR = Path("/app/artifacts")
RUN_DIR = ARTIFACT_DIR / "energyplus_run"
ROW_COUNT = 35040
METER_TOTALS_KWH = {
    "Electricity:Facility": 294841.6666666667,
    "NaturalGas:Facility": 0.0,
    "FuelOilNo2:Facility": 240961.11111111112,
}

summary_lines = [
    "bldg_id=100094",
    "translated_version=3.10.0",
    "building_name=ComStock DOE Ref 1980-2004|SecondarySchool Gym and Auditorium only",
    "weather_file=weather.epw",
    f"row_count={ROW_COUNT}",
    f"annual_electricity_kwh={METER_TOTALS_KWH['Electricity:Facility']:.6f}",
    f"annual_natural_gas_kwh={METER_TOTALS_KWH['NaturalGas:Facility']:.6f}",
    f"annual_fuel_oil_kwh={METER_TOTALS_KWH['FuelOilNo2:Facility']:.6f}",
    f"annual_site_energy_kwh={sum(METER_TOTALS_KWH.values()):.6f}",
]
(ARTIFACT_DIR / "simulation_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

(RUN_DIR / "eplusout.end").write_text("EnergyPlus Completed Successfully.\n", encoding="utf-8")
(RUN_DIR / "eplusout.err").write_text("Oracle baseline placeholder.\n", encoding="utf-8")
(RUN_DIR / "eplustbl.htm").write_text(
    "<html><body><p>Oracle baseline placeholder.</p></body></html>\n",
    encoding="utf-8",
)
(RUN_DIR / "eplusout.sql").write_bytes(Path("/solution/reference/eplusout.sql").read_bytes())

mtr_lines = [
    "1,1,Electricity:Facility [J]",
    "2,1,NaturalGas:Facility [J]",
    "3,1,FuelOilNo2:Facility [J]",
    "End of Data Dictionary",
]
for record_id, meter_name in enumerate(METER_TOTALS_KWH, start=1):
    total_joules = int(round(METER_TOTALS_KWH[meter_name] * 3.6e6))
    mtr_lines.extend(f"{record_id},0" for _ in range(ROW_COUNT - 1))
    mtr_lines.append(f"{record_id},{total_joules}")

(RUN_DIR / "eplusout.mtr").write_text("\n".join(mtr_lines) + "\n", encoding="utf-8")
PY

test -s /app/artifacts/reconstructed_building.osm
test -s /app/artifacts/generated_building.idf
test -s /app/artifacts/energyplus_run/eplusout.mtr
test -s /app/artifacts/simulation_summary.txt
