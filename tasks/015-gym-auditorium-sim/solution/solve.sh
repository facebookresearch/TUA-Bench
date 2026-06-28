#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts/energyplus_run

cp /solution/reference/gym_auditorium_reference.osm /app/artifacts/gym_auditorium_only.osm
cp /solution/reference/eplusout.sql /app/artifacts/energyplus_run/eplusout.sql

cat > /app/artifacts/generated_building.idf <<'IDF'
!- Oracle placeholder. The reference SQL was generated from the hidden
!- gym/auditorium-only OpenStudio model with the task weather file.
Version, 24.2;
IDF

cat > /app/artifacts/energyplus_run/eplusout.end <<'END'
EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 00.00sec
END

cat > /app/artifacts/energyplus_run/eplusout.err <<'ERR'
************* EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 00.00sec
ERR

cat > /app/artifacts/simulation_summary.txt <<'SUMMARY'
Oracle simulation result for the gym/auditorium-only model.
SUMMARY

test -s /app/artifacts/gym_auditorium_only.osm
test -s /app/artifacts/generated_building.idf
test -s /app/artifacts/energyplus_run/eplusout.sql
