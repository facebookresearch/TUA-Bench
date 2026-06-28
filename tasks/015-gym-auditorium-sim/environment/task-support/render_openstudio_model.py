#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Render mesh-based floorplan and exterior PNGs from an OpenStudio model."""

from __future__ import annotations

import argparse
import base64
import colorsys
import csv
import hashlib
import json
import math
import re
import struct
import tempfile
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import openstudio
import openstudiogltf


OUTDOOR_BOUNDARIES = {
    "Outdoors",
    "Ground",
    "GroundFCfactorMethod",
    "Foundation",
    "GroundSlabPreprocessorAverage",
}
EXTERIOR_SURFACE_TYPES = {"Wall", "RoofCeiling", "FixedWindow"}
THREE_D_SURFACE_TYPES = {"Wall", "RoofCeiling", "FixedWindow", "Floor"}
WINDOW_SURFACE_TYPES = {"FixedWindow", "OperableWindow"}
DOOR_SURFACE_TYPES = {"Door", "GlassDoor", "OverheadDoor"}
OPENING_SURFACE_TYPES = WINDOW_SURFACE_TYPES | DOOR_SURFACE_TYPES
ACCESSOR_DTYPES = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
ACCESSOR_WIDTHS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT4": 16,
}
TEXT_SUPERSAMPLE = 4
FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


@dataclass
class MeshObject:
    object_id: int
    name: str
    surface_type: str
    outside_boundary: str
    story: str
    space_name: str
    space_type_name: str
    color: np.ndarray
    alpha: float
    positions: np.ndarray
    triangles: np.ndarray
    construction_thickness_m: float = 0.0


@dataclass
class Camera:
    eye: np.ndarray
    target: np.ndarray
    up: np.ndarray
    fov_y_deg: float


@dataclass
class ProjectedTriangle:
    points: np.ndarray
    depths: np.ndarray
    color: np.ndarray
    alpha: float
    object_id: int
    depth_slack: float
    mean_depth: float


@dataclass
class SpaceSummary:
    room_id: str
    short_name: str
    full_name: str
    area_m2: float
    width_m: float
    depth_m: float
    center_xz: np.ndarray
    bbox_xz: tuple[float, float, float, float]


@dataclass
class OpeningSummary:
    opening_id: str
    opening_type: str
    span_m: float
    sill_m: float
    head_m: float
    center_xz: np.ndarray
    wall_name: str
    space_name: str


@dataclass
class WallBandSummary:
    endpoints_xz: np.ndarray
    outside_boundary: str
    thickness_m: float
    source_name: str


@dataclass
class SpaceTypeLoadSummary:
    space_type_name: str
    area_m2: float
    people_per_m2: float
    lights_w_per_m2: float
    equipment_w_per_m2: float
    oa_per_person_m3_s: float
    oa_per_area_m3_s_m2: float


@dataclass
class EnergyModelMetadata:
    story_count: int
    thermal_zone_count: int
    total_floor_area_m2: float
    air_loop_count: int
    air_loop_names: list[str]
    vav_terminal_count: int
    zone_exhaust_fan_count: int
    fan_efficiency_range: tuple[float, float] | None
    heating_setpoint_range_c: tuple[float, float] | None
    cooling_setpoint_range_c: tuple[float, float] | None
    boiler_count: int
    boiler_fuel: str
    boiler_efficiency_range: tuple[float, float] | None
    chiller_count: int
    chiller_cop_range: tuple[float, float] | None
    cooling_tower_count: int
    service_water_loop_count: int
    water_heater_count: int
    water_heater_fuel: str
    water_heater_efficiency_range: tuple[float, float] | None
    glazing_name: str
    glazing_u_w_m2k: float | None
    glazing_shgc: float | None
    glazing_vt: float | None
    space_type_loads: list[SpaceTypeLoadSummary]


@dataclass
class FloorplanMetadata:
    model_name: str
    selected_story: str
    focus_bbox: tuple[float, float, float, float]
    overall_width_m: float
    overall_depth_m: float
    height_m: float
    x_boundaries_m: list[float]
    z_boundaries_m: list[float]
    spaces: list[SpaceSummary]
    window_count: int
    door_count: int
    exterior_wall_thickness_range_m: tuple[float, float] | None
    interior_wall_thickness_range_m: tuple[float, float] | None
    openings: list[OpeningSummary]
    energy_model: EnergyModelMetadata | None = None


def normalize(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length <= 1e-9:
        return np.zeros_like(vector, dtype=np.float64)
    return vector / length


def edge_function(point_a: np.ndarray, point_b: np.ndarray, x_grid: np.ndarray, y_grid: np.ndarray) -> np.ndarray:
    return (
        (x_grid - point_a[0]) * (point_b[1] - point_a[1])
        - (y_grid - point_a[1]) * (point_b[0] - point_a[0])
    )


def hash_pastel(text: str, *, saturation: float = 0.34, lightness: float = 0.78) -> np.ndarray:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    sat = saturation + 0.10 * (digest[1] / 255.0 - 0.5)
    lit = lightness + 0.08 * (digest[2] / 255.0 - 0.5)
    red, green, blue = colorsys.hls_to_rgb(hue, max(0.55, min(0.88, lit)), max(0.15, min(0.55, sat)))
    return np.array([red, green, blue], dtype=np.float64)


def mix(color_a: np.ndarray, color_b: np.ndarray, fraction: float) -> np.ndarray:
    return color_a * (1.0 - fraction) + color_b * fraction


def write_png(image: np.ndarray, output_path: Path, *, gamma_correct: bool = True) -> None:
    clipped = np.clip(image, 0.0, 1.0)
    if gamma_correct:
        clipped = np.power(clipped, 1.0 / 2.2)
    pixels = (clipped * 255.0 + 0.5).astype(np.uint8)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack("!I", len(payload))
            + tag
            + payload
            + struct.pack("!I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    height, width, _ = pixels.shape
    raw = bytearray()
    for row in range(height):
        raw.append(0)
        raw.extend(pixels[row].tobytes())

    png_bytes = bytearray(b"\x89PNG\r\n\x1a\n")
    png_bytes.extend(
        chunk(
            b"IHDR",
            struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0),
        )
    )
    png_bytes.extend(chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png_bytes.extend(chunk(b"IEND", b""))
    output_path.write_bytes(png_bytes)


def to_os_path(path: Path):
    if hasattr(openstudio, "path"):
        return openstudio.path(str(path))
    return openstudio.toPath(str(path))


def load_model(osm_path: Path):
    translator = openstudio.osversion.VersionTranslator()
    model_opt = translator.loadModel(to_os_path(osm_path))
    if not model_opt.is_initialized():
        raise RuntimeError(f"Failed to load model from {osm_path}")
    return model_opt.get()


def export_gltf(model, gltf_path: Path) -> None:
    gltf_translator = openstudiogltf.GltfForwardTranslator()
    success = gltf_translator.modelToGLTF(model, to_os_path(gltf_path))
    if not success:
        errors = [str(message) for message in gltf_translator.errors()]
        raise RuntimeError(f"OpenStudio glTF export failed: {errors}")


def decode_accessor(document: dict, buffer_bytes: bytes, accessor_index: int) -> np.ndarray:
    accessor = document["accessors"][accessor_index]
    buffer_view = document["bufferViews"][accessor["bufferView"]]
    dtype = ACCESSOR_DTYPES[accessor["componentType"]]
    width = ACCESSOR_WIDTHS[accessor["type"]]
    element_size = np.dtype(dtype).itemsize * width
    byte_offset = buffer_view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    byte_stride = buffer_view.get("byteStride", element_size)

    if byte_stride == element_size:
        array = np.frombuffer(
            buffer_bytes,
            dtype=dtype,
            count=accessor["count"] * width,
            offset=byte_offset,
        ).reshape(accessor["count"], width)
        return array.copy()

    raw = np.frombuffer(
        buffer_bytes,
        dtype=np.uint8,
        count=accessor["count"] * byte_stride,
        offset=byte_offset,
    ).reshape(accessor["count"], byte_stride)
    packed = raw[:, :element_size].tobytes()
    return np.frombuffer(packed, dtype=dtype).reshape(accessor["count"], width).copy()


def matrix_from_gltf(values: list[float] | None) -> np.ndarray:
    if values is None:
        return np.identity(4, dtype=np.float64)
    return np.array(values, dtype=np.float64).reshape((4, 4), order="F")


def transform_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate([points.astype(np.float64), np.ones((len(points), 1), dtype=np.float64)], axis=1)
    return (homogeneous @ matrix.T)[:, :3]


def triangulate_polygon(vertex_count: int) -> np.ndarray:
    if vertex_count < 3:
        return np.empty((0, 3), dtype=np.int64)
    return np.array([[0, index, index + 1] for index in range(1, vertex_count - 1)], dtype=np.int64)


def to_renderer_coords(point) -> np.ndarray:
    # OpenStudio uses Z as vertical; the glTF export path used by the 3D renderer uses Y as vertical.
    return np.array([point.x(), point.z(), point.y()], dtype=np.float64)


def transformed_vertices(vertices, transformation) -> np.ndarray:
    return np.array([to_renderer_coords(transformation * vertex) for vertex in vertices], dtype=np.float64)


def layered_construction_thickness(construction_base) -> float:
    layered = construction_base.to_LayeredConstruction()
    if not layered.is_initialized():
        return 0.0

    thickness = 0.0
    for layer in layered.get().layers():
        opaque = layer.to_StandardOpaqueMaterial()
        if opaque.is_initialized():
            thickness += float(opaque.get().thickness())
    return thickness


def load_floorplan_objects(model) -> list[MeshObject]:
    objects: list[MeshObject] = []
    next_object_id = 1

    for surface in model.getSurfaces():
        space_opt = surface.space()
        if not space_opt.is_initialized():
            continue
        space = space_opt.get()
        story_opt = space.buildingStory()
        story = story_opt.get().nameString() if story_opt.is_initialized() else "Unknown Story"
        space_type_opt = space.spaceType()
        space_type_name = space_type_opt.get().nameString() if space_type_opt.is_initialized() else ""
        positions = transformed_vertices(surface.vertices(), space.transformation())
        triangles = triangulate_polygon(len(positions))
        if len(triangles) == 0:
            continue

        thickness = 0.0
        construction = surface.construction()
        if construction.is_initialized():
            thickness = layered_construction_thickness(construction.get())

        objects.append(
            MeshObject(
                object_id=next_object_id,
                name=surface.nameString(),
                surface_type=surface.surfaceType(),
                outside_boundary=surface.outsideBoundaryCondition(),
                story=story,
                space_name=space.nameString(),
                space_type_name=space_type_name,
                color=np.array([0.72, 0.72, 0.72], dtype=np.float64),
                alpha=1.0,
                positions=positions,
                triangles=triangles,
                construction_thickness_m=thickness,
            )
        )
        next_object_id += 1

        if surface.surfaceType() != "Wall":
            continue

        for sub_surface in surface.subSurfaces():
            sub_positions = transformed_vertices(sub_surface.vertices(), space.transformation())
            sub_triangles = triangulate_polygon(len(sub_positions))
            if len(sub_triangles) == 0:
                continue
            objects.append(
                MeshObject(
                    object_id=next_object_id,
                    name=sub_surface.nameString(),
                    surface_type=sub_surface.subSurfaceType(),
                    outside_boundary=surface.outsideBoundaryCondition(),
                    story=story,
                    space_name=space.nameString(),
                    space_type_name=space_type_name,
                    color=np.array([0.72, 0.72, 0.72], dtype=np.float64),
                    alpha=1.0,
                    positions=sub_positions,
                    triangles=sub_triangles,
                    construction_thickness_m=thickness,
                )
            )
            next_object_id += 1

    return objects


def extract_glazing_properties(model) -> tuple[str, float | None, float | None, float | None]:
    construction_usage: dict[str, int] = defaultdict(int)
    constructions = {}
    for sub_surface in model.getSubSurfaces():
        if sub_surface.subSurfaceType() not in WINDOW_SURFACE_TYPES:
            continue
        construction = sub_surface.construction()
        if not construction.is_initialized():
            continue
        base = construction.get()
        construction_usage[base.nameString()] += 1
        constructions[base.nameString()] = base

    for construction_name, _ in sorted(construction_usage.items(), key=lambda item: (-item[1], item[0])):
        construction_base = constructions[construction_name]
        try:
            construction_opt = construction_base.to_Construction()
        except Exception:
            construction_opt = None
        if construction_opt is None or not construction_opt.is_initialized():
            continue

        for layer in construction_opt.get().layers():
            try:
                simple_glazing_opt = layer.to_SimpleGlazing()
                if simple_glazing_opt.is_initialized():
                    glazing = simple_glazing_opt.get()
                    return (
                        glazing.nameString(),
                        safe_float(glazing.uFactor()),
                        safe_float(glazing.solarHeatGainCoefficient()),
                        safe_float(glazing.visibleTransmittance()),
                    )
            except Exception:
                continue

    return "N A", None, None, None


def collect_space_type_load_summaries(model) -> list[SpaceTypeLoadSummary]:
    summaries: list[SpaceTypeLoadSummary] = []
    for space_type in model.getSpaceTypes():
        area_m2 = sum(space.floorArea() for space in space_type.spaces())
        if area_m2 <= 0.1:
            continue

        people_per_m2 = 0.0
        lights_w_per_m2 = 0.0
        equipment_w_per_m2 = 0.0
        for people in space_type.people():
            value = safe_float(people.peopleDefinition().peopleperSpaceFloorArea())
            if value is not None:
                people_per_m2 += value
        for lights in space_type.lights():
            value = safe_float(lights.lightsDefinition().wattsperSpaceFloorArea())
            if value is not None:
                lights_w_per_m2 += value
        for equipment in space_type.electricEquipment():
            value = safe_float(equipment.electricEquipmentDefinition().wattsperSpaceFloorArea())
            if value is not None:
                equipment_w_per_m2 += value

        oa_per_person_m3_s = 0.0
        oa_per_area_m3_s_m2 = 0.0
        try:
            outdoor_air = space_type.designSpecificationOutdoorAir()
        except Exception:
            outdoor_air = None
        if outdoor_air is not None and outdoor_air.is_initialized():
            specification = outdoor_air.get()
            oa_per_person_m3_s = safe_float(specification.outdoorAirFlowperPerson()) or 0.0
            oa_per_area_m3_s_m2 = safe_float(specification.outdoorAirFlowperFloorArea()) or 0.0

        summaries.append(
            SpaceTypeLoadSummary(
                space_type_name=space_type.nameString(),
                area_m2=area_m2,
                people_per_m2=people_per_m2,
                lights_w_per_m2=lights_w_per_m2,
                equipment_w_per_m2=equipment_w_per_m2,
                oa_per_person_m3_s=oa_per_person_m3_s,
                oa_per_area_m3_s_m2=oa_per_area_m3_s_m2,
            )
        )

    summaries.sort(key=lambda item: (-item.area_m2, item.space_type_name))
    return summaries


def collect_energy_model_metadata(model) -> EnergyModelMetadata:
    story_names = set()
    total_floor_area_m2 = 0.0
    for space in model.getSpaces():
        total_floor_area_m2 += float(space.floorArea())
        story = space.buildingStory()
        if story.is_initialized():
            story_names.add(story.get().nameString())

    fan_efficiency_range = values_range(
        [value for value in (safe_float(fan.fanTotalEfficiency()) for fan in model.getFanVariableVolumes()) if value is not None]
    )

    heating_values: list[float] = []
    cooling_values: list[float] = []
    visited_heating_schedules: set[str] = set()
    visited_cooling_schedules: set[str] = set()
    for zone in model.getThermalZones():
        thermostat = zone.thermostatSetpointDualSetpoint()
        if not thermostat.is_initialized():
            continue
        dual_setpoint = thermostat.get()

        heating_schedule = dual_setpoint.heatingSetpointTemperatureSchedule()
        if heating_schedule.is_initialized():
            schedule = heating_schedule.get()
            if schedule.nameString() not in visited_heating_schedules:
                visited_heating_schedules.add(schedule.nameString())
                schedule_range = schedule_ruleset_min_max(schedule)
                if schedule_range is not None:
                    heating_values.extend(schedule_range)

        cooling_schedule = dual_setpoint.coolingSetpointTemperatureSchedule()
        if cooling_schedule.is_initialized():
            schedule = cooling_schedule.get()
            if schedule.nameString() not in visited_cooling_schedules:
                visited_cooling_schedules.add(schedule.nameString())
                schedule_range = schedule_ruleset_min_max(schedule)
                if schedule_range is not None:
                    cooling_values.extend(schedule_range)

    boiler_fuel_counter: dict[str, int] = defaultdict(int)
    boiler_efficiencies = []
    for boiler in model.getBoilerHotWaters():
        boiler_fuel_counter[humanize_identifier(str(boiler.fuelType()))] += 1
        value = safe_float(boiler.nominalThermalEfficiency())
        if value is not None:
            boiler_efficiencies.append(value)

    chiller_cops = [value for value in (safe_float(chiller.referenceCOP()) for chiller in model.getChillerElectricEIRs()) if value is not None]

    water_heater_fuel_counter: dict[str, int] = defaultdict(int)
    water_heater_efficiencies = []
    for water_heater in model.getWaterHeaterMixeds():
        water_heater_fuel_counter[humanize_identifier(str(water_heater.heaterFuelType()))] += 1
        value = safe_float(water_heater.heaterThermalEfficiency())
        if value is not None:
            water_heater_efficiencies.append(value)

    try:
        zone_exhaust_fan_count = len(model.getFanZoneExhausts())
    except Exception:
        zone_exhaust_fan_count = 0

    glazing_name, glazing_u_w_m2k, glazing_shgc, glazing_vt = extract_glazing_properties(model)
    service_water_loop_count = sum(
        1
        for plant_loop in model.getPlantLoops()
        if "SERVICE WATER" in plant_loop.nameString().upper() or "BOOSTER" in plant_loop.nameString().upper()
    )

    def dominant_label(counter: dict[str, int], default_text: str = "N A") -> str:
        if not counter:
            return default_text
        return max(counter.items(), key=lambda item: (item[1], item[0]))[0]

    return EnergyModelMetadata(
        story_count=len(story_names),
        thermal_zone_count=len(model.getThermalZones()),
        total_floor_area_m2=total_floor_area_m2,
        air_loop_count=len(model.getAirLoopHVACs()),
        air_loop_names=[air_loop.nameString() for air_loop in model.getAirLoopHVACs()],
        vav_terminal_count=len(model.getAirTerminalSingleDuctVAVReheats()),
        zone_exhaust_fan_count=zone_exhaust_fan_count,
        fan_efficiency_range=fan_efficiency_range,
        heating_setpoint_range_c=values_range(heating_values),
        cooling_setpoint_range_c=values_range(cooling_values),
        boiler_count=len(model.getBoilerHotWaters()),
        boiler_fuel=dominant_label(boiler_fuel_counter),
        boiler_efficiency_range=values_range(boiler_efficiencies),
        chiller_count=len(model.getChillerElectricEIRs()),
        chiller_cop_range=values_range(chiller_cops),
        cooling_tower_count=len(model.getCoolingTowerVariableSpeeds()) + len(model.getCoolingTowerSingleSpeeds()),
        service_water_loop_count=service_water_loop_count,
        water_heater_count=len(model.getWaterHeaterMixeds()),
        water_heater_fuel=dominant_label(water_heater_fuel_counter),
        water_heater_efficiency_range=values_range(water_heater_efficiencies),
        glazing_name=glazing_name,
        glazing_u_w_m2k=glazing_u_w_m2k,
        glazing_shgc=glazing_shgc,
        glazing_vt=glazing_vt,
        space_type_loads=collect_space_type_load_summaries(model),
    )


def triangle_area_sum(points: np.ndarray, triangles: np.ndarray) -> float:
    tri_points = points[triangles]
    cross_products = np.cross(tri_points[:, 1] - tri_points[:, 0], tri_points[:, 2] - tri_points[:, 0])
    return float(0.5 * np.linalg.norm(cross_products, axis=1).sum())


def load_mesh_objects(gltf_path: Path) -> list[MeshObject]:
    document = json.loads(gltf_path.read_text())
    buffer_uri = document["buffers"][0]["uri"]
    if not buffer_uri.startswith("data:"):
        raise RuntimeError("The exported glTF referenced an external buffer; this renderer expects embedded data.")
    buffer_bytes = base64.b64decode(buffer_uri.split(",", 1)[1])

    materials: list[np.ndarray] = []
    for material in document.get("materials", []):
        rgba = material.get("pbrMetallicRoughness", {}).get("baseColorFactor", [0.7, 0.7, 0.7, 1.0])
        materials.append(np.array(rgba, dtype=np.float64))

    parents: dict[int, int] = {}
    for node_index, node in enumerate(document["nodes"]):
        for child_index in node.get("children", []):
            parents[child_index] = node_index

    world_cache: dict[int, np.ndarray] = {}

    def world_matrix(node_index: int) -> np.ndarray:
        cached = world_cache.get(node_index)
        if cached is not None:
            return cached

        local = matrix_from_gltf(document["nodes"][node_index].get("matrix"))
        parent = parents.get(node_index)
        combined = local if parent is None else world_matrix(parent) @ local
        world_cache[node_index] = combined
        return combined

    objects: list[MeshObject] = []
    next_object_id = 1

    for node_index, node in enumerate(document["nodes"]):
        mesh_index = node.get("mesh")
        if mesh_index is None:
            continue

        extras = node.get("extras") or {}
        world = world_matrix(node_index)
        mesh = document["meshes"][mesh_index]
        primitives = mesh.get("primitives", [])

        for primitive_index, primitive in enumerate(primitives):
            if primitive.get("mode", 4) != 4:
                continue

            positions_local = decode_accessor(document, buffer_bytes, primitive["attributes"]["POSITION"]).astype(np.float64)
            positions_world = transform_points(positions_local, world)

            if "indices" in primitive:
                indices = decode_accessor(document, buffer_bytes, primitive["indices"]).astype(np.int64).reshape(-1, 3)
            else:
                indices = np.arange(len(positions_world), dtype=np.int64).reshape(-1, 3)

            material_index = primitive.get("material", -1)
            if 0 <= material_index < len(materials):
                rgba = materials[material_index]
            else:
                rgba = np.array([0.7, 0.7, 0.7, 1.0], dtype=np.float64)

            object_name = node.get("name") or extras.get("name") or f"Object {next_object_id}"
            if len(primitives) > 1:
                object_name = f"{object_name} [{primitive_index + 1}]"

            objects.append(
                MeshObject(
                    object_id=next_object_id,
                    name=object_name,
                    surface_type=extras.get("surfaceType", ""),
                    outside_boundary=extras.get("outsideBoundaryCondition", ""),
                    story=extras.get("buildingStoryName", "Unknown Story"),
                    space_name=extras.get("spaceName", object_name),
                    space_type_name=extras.get("spaceTypeName", ""),
                    color=rgba[:3].copy(),
                    alpha=float(rgba[3]),
                    positions=positions_world,
                    triangles=indices,
                )
            )
            next_object_id += 1

    return objects


def fit_plan(points: np.ndarray, width: int, height: int, padding: int) -> tuple[float, float, float]:
    min_x = float(points[:, 0].min())
    max_x = float(points[:, 0].max())
    min_z = float(points[:, 1].min())
    max_z = float(points[:, 1].max())
    span_x = max(max_x - min_x, 1.0)
    span_z = max(max_z - min_z, 1.0)
    scale = min((width - 2 * padding) / span_x, (height - 2 * padding) / span_z)
    return min_x, min_z, scale


def project_plan(points: np.ndarray, min_x: float, min_z: float, scale: float, width: int, height: int, padding: int) -> np.ndarray:
    projected = np.empty((len(points), 2), dtype=np.float64)
    projected[:, 0] = padding + (points[:, 0] - min_x) * scale
    projected[:, 1] = height - (padding + (points[:, 1] - min_z) * scale)
    return projected


def fill_triangle(image: np.ndarray, points: np.ndarray, color: np.ndarray) -> None:
    height, width, _ = image.shape
    min_x = max(0, int(math.floor(float(points[:, 0].min()))))
    max_x = min(width - 1, int(math.ceil(float(points[:, 0].max()))))
    min_y = max(0, int(math.floor(float(points[:, 1].min()))))
    max_y = min(height - 1, int(math.ceil(float(points[:, 1].max()))))
    if min_x > max_x or min_y > max_y:
        return

    xs, ys = np.meshgrid(
        np.arange(min_x, max_x + 1, dtype=np.float64) + 0.5,
        np.arange(min_y, max_y + 1, dtype=np.float64) + 0.5,
    )
    area = edge_function(points[0], points[1], points[2, 0], points[2, 1])
    if abs(area) < 1e-8:
        return

    inv_area = 1.0 / area
    weight0 = edge_function(points[1], points[2], xs, ys) * inv_area
    weight1 = edge_function(points[2], points[0], xs, ys) * inv_area
    weight2 = 1.0 - weight0 - weight1
    inside = (weight0 >= -1e-7) & (weight1 >= -1e-7) & (weight2 >= -1e-7)
    if not np.any(inside):
        return

    tile = image[min_y:max_y + 1, min_x:max_x + 1]
    tile[inside] = color


def draw_thick_line(image: np.ndarray, point_a: np.ndarray, point_b: np.ndarray, color: np.ndarray, thickness: int) -> None:
    x0 = float(point_a[0])
    y0 = float(point_a[1])
    x1 = float(point_b[0])
    y1 = float(point_b[1])
    steps = max(1, int(math.ceil(max(abs(x1 - x0), abs(y1 - y0)))))
    radius = max(1, thickness // 2)

    height, width, _ = image.shape
    for step in range(steps + 1):
        fraction = step / steps
        x = int(round(x0 + (x1 - x0) * fraction))
        y = int(round(y0 + (y1 - y0) * fraction))
        min_x = max(0, x - radius)
        max_x = min(width - 1, x + radius)
        min_y = max(0, y - radius)
        max_y = min(height - 1, y + radius)
        image[min_y:max_y + 1, min_x:max_x + 1] = color


def fill_polygon(image: np.ndarray, polygon: np.ndarray, color: np.ndarray) -> None:
    if len(polygon) < 3:
        return
    for index in range(1, len(polygon) - 1):
        fill_triangle(image, np.array([polygon[0], polygon[index], polygon[index + 1]], dtype=np.float64), color)


def stroke_polygon(image: np.ndarray, polygon: np.ndarray, color: np.ndarray, thickness: int) -> None:
    if len(polygon) < 2:
        return
    for index in range(len(polygon)):
        draw_thick_line(image, polygon[index], polygon[(index + 1) % len(polygon)], color, thickness)


def segment_endpoints(points_xz: np.ndarray, *, tolerance: float = 1e-4) -> np.ndarray | None:
    unique: list[np.ndarray] = []
    for point in points_xz:
        if not any(float(np.linalg.norm(point - other)) <= tolerance for other in unique):
            unique.append(point.astype(np.float64))
    if len(unique) < 2:
        return None

    best_pair: tuple[np.ndarray, np.ndarray] | None = None
    best_distance = -1.0
    for left_index in range(len(unique)):
        for right_index in range(left_index + 1, len(unique)):
            distance = float(np.linalg.norm(unique[right_index] - unique[left_index]))
            if distance > best_distance:
                best_distance = distance
                best_pair = (unique[left_index], unique[right_index])
    if best_pair is None or best_distance <= tolerance:
        return None
    return np.stack(best_pair, axis=0)


def segment_key(points_xz: np.ndarray, *, tolerance: float = 0.02) -> tuple[tuple[int, int], tuple[int, int]] | None:
    endpoints = segment_endpoints(points_xz)
    if endpoints is None:
        return None

    key_points = []
    for point in endpoints:
        key_points.append((int(round(point[0] / tolerance)), int(round(point[1] / tolerance))))
    key_points.sort()
    return key_points[0], key_points[1]


def wall_band_polygon(point_a: np.ndarray, point_b: np.ndarray, thickness_px: float) -> np.ndarray | None:
    direction = point_b - point_a
    length = float(np.linalg.norm(direction))
    if length <= 1e-6:
        return None

    tangent = direction / length
    normal = np.array([-tangent[1], tangent[0]], dtype=np.float64)
    offset = normal * max(thickness_px * 0.5, 1.0)
    return np.array(
        [
            point_a + offset,
            point_b + offset,
            point_b - offset,
            point_a - offset,
        ],
        dtype=np.float64,
    )


def wall_thickness_range(thicknesses: list[float]) -> tuple[float, float] | None:
    filtered = [value for value in thicknesses if value > 1e-4]
    if not filtered:
        return None
    return min(filtered), max(filtered)


def format_thickness_range(thickness_range: tuple[float, float] | None) -> str:
    if thickness_range is None:
        return "N A"
    low, high = thickness_range
    if high - low <= 0.015:
        return f"{low:.2f} M"
    return f"{low:.2f} TO {high:.2f} M"


def format_numeric_range(
    value_range: tuple[float, float] | None,
    *,
    decimals: int = 2,
    suffix: str = "",
) -> str:
    if value_range is None:
        return "N A"
    low, high = value_range
    if abs(high - low) <= 10 ** (-(decimals + 1)):
        return f"{low:.{decimals}f}{suffix}"
    return f"{low:.{decimals}f} TO {high:.{decimals}f}{suffix}"


def compact_loop_name(name: str) -> str:
    return humanize_identifier(name.replace("Zone", "").replace("Loop", "").strip())


def build_simulation_panel_lines(energy_model: EnergyModelMetadata) -> list[str]:
    lines = [
        f"{energy_model.story_count:d} STORIES  {energy_model.thermal_zone_count:d} ZONES  {energy_model.total_floor_area_m2:.0f} M2",
        f"AIR SYSTEM {energy_model.air_loop_count:d} CENTRAL VAV LOOPS",
        f"TERMINALS {energy_model.vav_terminal_count:d} VAV REHEAT  {energy_model.zone_exhaust_fan_count:d} EXHAUST",
        f"HEAT SETPOINT {format_numeric_range(energy_model.heating_setpoint_range_c, decimals=1, suffix=' C')}",
        f"COOL SETPOINT {format_numeric_range(energy_model.cooling_setpoint_range_c, decimals=1, suffix=' C')}",
        f"HEATING {energy_model.boiler_count:d} {energy_model.boiler_fuel} HW BOILER",
        f"BOILER EFF {format_numeric_range(energy_model.boiler_efficiency_range, decimals=3)}",
        f"COOLING {energy_model.chiller_count:d} WATER COOLED CHILLER",
        f"CHILLER COP {format_numeric_range(energy_model.chiller_cop_range, decimals=2)}  TOWERS {energy_model.cooling_tower_count:d}",
        f"SERVICE WATER {energy_model.water_heater_count:d} TANKS  LOOPS {energy_model.service_water_loop_count:d}",
        f"SWH FUEL {energy_model.water_heater_fuel}  EFF {format_numeric_range(energy_model.water_heater_efficiency_range, decimals=3)}",
        f"GLAZING U {energy_model.glazing_u_w_m2k:.2f}  SHGC {energy_model.glazing_shgc:.3f}  VT {energy_model.glazing_vt:.3f}" if energy_model.glazing_u_w_m2k is not None and energy_model.glazing_shgc is not None and energy_model.glazing_vt is not None else "GLAZING DATA NOT RESOLVED FROM WINDOW CONSTRUCTION",
        "WEATHER EPW REQUIRED  NOT EMBEDDED IN OSM",
    ]
    for summary in energy_model.space_type_loads[:3]:
        lines.append(
            f"LOAD {compact_space_type_name(summary.space_type_name)} P {summary.people_per_m2:.3f} L {summary.lights_w_per_m2:.2f} E {summary.equipment_w_per_m2:.2f}"
        )
    return lines


def build_reconstruction_note_lines(metadata: FloorplanMetadata) -> list[str]:
    lines = [
        "PAGE UP IS MODEL NORTH",
        "WALL BANDS USE MODELED CONSTRUCTION THICKNESS",
        "BLUE OPENINGS SHOW EXACT MODELED WINDOW SPANS",
        "ROOM IDS MATCH FLOORPLAN SCHEDULE CSV",
        "OPENING IDS MATCH FLOORPLAN OPENINGS CSV",
        "PLAN DIMENSIONS COME FROM OSM SURFACE COORDINATES",
        f"THIS STORY CONTAINS {metadata.door_count:d} MODELED DOOR SUBSURFACES",
        "SIMULATION INPUTS BELOW COME FROM HVAC AND LOAD OBJECTS IN THE OSM",
        "ANNUAL SIMULATION ALSO NEEDS AN EXTERNAL EPW WEATHER FILE",
        "SPACE TYPE LOADS CSV AND MODEL SUMMARY TXT ARE EXPORTED",
    ]
    return lines


def boundary_edges(triangles: np.ndarray) -> list[tuple[int, int]]:
    counts: dict[tuple[int, int], int] = {}
    for triangle in triangles:
        for start, end in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            key = (int(min(start, end)), int(max(start, end)))
            counts[key] = counts.get(key, 0) + 1
    return [edge for edge, count in counts.items() if count == 1]


def bbox_xz(mesh_object: MeshObject) -> tuple[float, float, float, float]:
    return (
        float(mesh_object.positions[:, 0].min()),
        float(mesh_object.positions[:, 0].max()),
        float(mesh_object.positions[:, 2].min()),
        float(mesh_object.positions[:, 2].max()),
    )


def boxes_overlap(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float], gap: float) -> bool:
    return not (
        box_a[1] < box_b[0] - gap
        or box_b[1] < box_a[0] - gap
        or box_a[3] < box_b[2] - gap
        or box_b[3] < box_a[2] - gap
    )


def merge_boxes(boxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(box[0] for box in boxes),
        max(box[1] for box in boxes),
        min(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def select_focus_bbox(floor_objects: list[MeshObject], all_objects: list[MeshObject]) -> tuple[float, float, float, float]:
    if not floor_objects:
        raise RuntimeError("No floor objects were available to determine the render focus.")

    boxes = [bbox_xz(mesh_object) for mesh_object in floor_objects]
    visited: set[int] = set()
    components: list[list[int]] = []
    gap = 1.5

    for start_index in range(len(floor_objects)):
        if start_index in visited:
            continue
        stack = [start_index]
        component: list[int] = []
        visited.add(start_index)
        while stack:
            current = stack.pop()
            component.append(current)
            for candidate in range(len(floor_objects)):
                if candidate in visited:
                    continue
                if boxes_overlap(boxes[current], boxes[candidate], gap):
                    visited.add(candidate)
                    stack.append(candidate)
        components.append(component)

    def component_score(component: list[int]) -> float:
        return sum(
            triangle_area_sum(floor_objects[index].positions, floor_objects[index].triangles)
            for index in component
        )

    best_component = max(components, key=component_score)
    return merge_boxes([boxes[index] for index in best_component])


def fill_rect(image: np.ndarray, x0: float, y0: float, x1: float, y1: float, color: np.ndarray) -> None:
    height, width, _ = image.shape
    left = max(0, min(int(round(x0)), int(round(x1))))
    right = min(width, max(int(round(x0)), int(round(x1))))
    top = max(0, min(int(round(y0)), int(round(y1))))
    bottom = min(height, max(int(round(y0)), int(round(y1))))
    if left >= right or top >= bottom:
        return
    image[top:bottom, left:right] = color


def stroke_rect(image: np.ndarray, x0: float, y0: float, x1: float, y1: float, color: np.ndarray, thickness: int = 2) -> None:
    fill_rect(image, x0, y0, x1, y0 + thickness, color)
    fill_rect(image, x0, y1 - thickness, x1, y1, color)
    fill_rect(image, x0, y0, x0 + thickness, y1, color)
    fill_rect(image, x1 - thickness, y0, x1, y1, color)


def blend_mask(image: np.ndarray, x: float, y: float, color: np.ndarray, alpha_mask: np.ndarray) -> None:
    height, width, _ = image.shape
    left = int(round(x))
    top = int(round(y))
    right = left + alpha_mask.shape[1]
    bottom = top + alpha_mask.shape[0]

    clip_left = max(0, left)
    clip_top = max(0, top)
    clip_right = min(width, right)
    clip_bottom = min(height, bottom)
    if clip_left >= clip_right or clip_top >= clip_bottom:
        return

    src_left = clip_left - left
    src_top = clip_top - top
    src_right = src_left + (clip_right - clip_left)
    src_bottom = src_top + (clip_bottom - clip_top)

    alpha = alpha_mask[src_top:src_bottom, src_left:src_right][..., None]
    if not np.any(alpha > 0.0):
        return

    tile = image[clip_top:clip_bottom, clip_left:clip_right]
    tile[:] = tile * (1.0 - alpha) + color * alpha


def cluster_values(values: list[float], tolerance: float = 0.25) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    clusters: list[list[float]] = [[sorted_values[0]]]
    for value in sorted_values[1:]:
        current = clusters[-1]
        if abs(value - sum(current) / len(current)) <= tolerance:
            current.append(value)
        else:
            clusters.append([value])
    return [sum(cluster) / len(cluster) for cluster in clusters]


def meters_to_feet(value_m: float) -> float:
    return value_m * 3.28084


def values_range(values: list[float]) -> tuple[float, float] | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return min(filtered), max(filtered)


def safe_float(value) -> float | None:
    try:
        if hasattr(value, "is_initialized"):
            return float(value.get()) if value.is_initialized() else None
        return float(value)
    except Exception:
        return None


def schedule_ruleset_min_max(schedule) -> tuple[float, float] | None:
    ruleset_opt = schedule.to_ScheduleRuleset()
    if not ruleset_opt.is_initialized():
        return None

    values: list[float] = []
    ruleset = ruleset_opt.get()
    for day in [ruleset.defaultDaySchedule(), ruleset.summerDesignDaySchedule(), ruleset.winterDesignDaySchedule()]:
        try:
            values.extend(float(item) for item in day.values())
        except Exception:
            continue
    for rule in ruleset.scheduleRules():
        try:
            values.extend(float(item) for item in rule.daySchedule().values())
        except Exception:
            continue
    return values_range(values)


def humanize_identifier(text: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    spaced = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", spaced)
    spaced = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", spaced)
    spaced = spaced.replace(":", " ").replace("_", " ").replace("-", " ")
    return " ".join(spaced.split())


def compact_space_type_name(text: str) -> str:
    name = text.replace("SecondarySchool ", "")
    name = name.replace(" - ComStock DOE Ref 1980-2004", "")
    name = " ".join(name.split())
    return humanize_identifier(name)


def sanitize_text(text: str) -> str:
    safe = []
    for character in text.upper():
        safe.append(character if character in FONT_5X7 else " ")
    return "".join(safe)


def measure_text(text: str, scale: int) -> tuple[int, int]:
    safe = sanitize_text(text)
    if not safe:
        return 0, 7 * scale
    width = len(safe) * 5 * scale + max(len(safe) - 1, 0) * scale
    return width, 7 * scale


def measure_multiline_text(lines: list[str], scale: int, line_gap: int | None = None) -> tuple[int, int]:
    safe_lines = [sanitize_text(line) for line in lines if line]
    if not safe_lines:
        return 0, 0
    gap = line_gap if line_gap is not None else scale * 2
    widths = [measure_text(line, scale)[0] for line in safe_lines]
    height = len(safe_lines) * 7 * scale + (len(safe_lines) - 1) * gap
    return max(widths), height


def label_box_bounds(
    center_x: float,
    center_y: float,
    lines: list[str],
    scale: int,
    *,
    line_gap: int | None = None,
) -> tuple[float, float, float, float]:
    width, height = measure_multiline_text(lines, scale, line_gap=line_gap)
    padding_x = scale * 2
    padding_y = scale * 2
    return (
        center_x - width / 2.0 - padding_x,
        center_y - height / 2.0 - padding_y,
        center_x + width / 2.0 + padding_x,
        center_y + height / 2.0 + padding_y,
    )


def expand_box(box: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    return (box[0] - margin, box[1] - margin, box[2] + margin, box[3] + margin)


def boxes_overlap_screen(
    box_a: tuple[float, float, float, float],
    box_b: tuple[float, float, float, float],
) -> bool:
    return not (
        box_a[2] <= box_b[0]
        or box_b[2] <= box_a[0]
        or box_a[3] <= box_b[1]
        or box_b[3] <= box_a[1]
    )


def box_within_screen(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
    *,
    margin: float = 0.0,
) -> bool:
    return (
        inner[0] >= outer[0] + margin
        and inner[1] >= outer[1] + margin
        and inner[2] <= outer[2] - margin
        and inner[3] <= outer[3] - margin
    )


def draw_text(
    image: np.ndarray,
    x: float,
    y: float,
    text: str,
    color: np.ndarray,
    scale: int,
    *,
    align: str = "left",
) -> None:
    safe = sanitize_text(text)
    width, _ = measure_text(safe, scale)
    start_x = float(x)
    if align == "center":
        start_x -= width / 2.0
    elif align == "right":
        start_x -= width

    width_px = max(1, width)
    height_px = max(1, 7 * scale)
    ss = TEXT_SUPERSAMPLE
    mask = np.zeros((height_px * ss, width_px * ss), dtype=np.float32)

    cursor_x = 0
    for character in safe:
        glyph = FONT_5X7.get(character, FONT_5X7[" "])
        for row_index, row in enumerate(glyph):
            for col_index, pixel in enumerate(row):
                if pixel != "1":
                    continue
                left = (cursor_x + col_index * scale) * ss
                top = row_index * scale * ss
                right = (cursor_x + (col_index + 1) * scale) * ss
                bottom = (row_index + 1) * scale * ss
                mask[top:bottom, left:right] = 1.0
        cursor_x += 6 * scale

    alpha_mask = mask.reshape(height_px, ss, width_px, ss).mean(axis=(1, 3))
    blend_mask(image, start_x, y, color, alpha_mask)


def draw_multiline_text(
    image: np.ndarray,
    x: float,
    y: float,
    lines: list[str],
    color: np.ndarray,
    scale: int,
    *,
    align: str = "left",
    line_gap: int | None = None,
) -> None:
    gap = line_gap if line_gap is not None else scale * 2
    cursor_y = float(y)
    for line in lines:
        if line:
            draw_text(image, x, cursor_y, line, color, scale, align=align)
        cursor_y += 7 * scale + gap


def draw_label_box(
    image: np.ndarray,
    center_x: float,
    center_y: float,
    lines: list[str],
    *,
    scale: int,
    text_color: np.ndarray,
    fill_color: np.ndarray,
    border_color: np.ndarray,
) -> None:
    x0, y0, x1, y1 = label_box_bounds(center_x, center_y, lines, scale)
    padding_y = scale * 2
    fill_rect(image, x0, y0, x1, y1, fill_color)
    stroke_rect(image, x0, y0, x1, y1, border_color, thickness=max(2, scale // 2))
    draw_multiline_text(
        image,
        center_x,
        y0 + padding_y,
        lines,
        text_color,
        scale,
        align="center",
    )


def choose_label_box_position(
    anchor: np.ndarray,
    outward_normal: np.ndarray,
    tangent: np.ndarray,
    lines: list[str],
    scale: int,
    occupied_boxes: list[tuple[float, float, float, float]],
    container_box: tuple[float, float, float, float],
    *,
    base_distance: float,
    radial_step: float,
    tangent_step: float,
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    radial_factors = [1.0, 1.45, 1.90, 2.35]
    tangential_factors = [0.0, 1.0, -1.0, 2.0, -2.0, 3.0, -3.0]

    for radial_sign in (1.0, -1.0):
        for radial_factor in radial_factors:
            for tangential_factor in tangential_factors:
                center = (
                    anchor
                    + outward_normal * (base_distance + radial_factor * radial_step) * radial_sign
                    + tangent * tangential_factor * tangent_step
                )
                box = label_box_bounds(center[0], center[1], lines, scale)
                if not box_within_screen(box, container_box, margin=2.0):
                    continue
                if any(boxes_overlap_screen(expand_box(box, 4.0), occupied_box) for occupied_box in occupied_boxes):
                    continue
                return center, box

    fallback_center = anchor + outward_normal * (base_distance + 1.90 * radial_step)
    fallback_box = label_box_bounds(fallback_center[0], fallback_center[1], lines, scale)
    return fallback_center, fallback_box


def draw_arrowhead(image: np.ndarray, tip: np.ndarray, direction: np.ndarray, color: np.ndarray, size: float = 12.0) -> None:
    direction = normalize(direction.astype(np.float64))
    if float(np.linalg.norm(direction)) <= 1e-9:
        return
    normal = np.array([-direction[1], direction[0]], dtype=np.float64)
    base = tip - direction * size
    triangle = np.array(
        [
            tip,
            base + normal * size * 0.55,
            base - normal * size * 0.55,
        ],
        dtype=np.float64,
    )
    fill_triangle(image, triangle, color)


def draw_dimension_chain_horizontal(
    image: np.ndarray,
    world_values: list[float],
    screen_values: list[float],
    anchor_y: float,
    chain_y: float,
    overall_y: float,
    color: np.ndarray,
) -> None:
    extension_color = mix(color, np.ones(3, dtype=np.float64), 0.65)
    for screen_x in screen_values:
        draw_thick_line(image, np.array([screen_x, anchor_y]), np.array([screen_x, overall_y + 16]), extension_color, 2)

    for left_world, right_world, left_screen, right_screen in zip(
        world_values[:-1],
        world_values[1:],
        screen_values[:-1],
        screen_values[1:],
    ):
        draw_thick_line(image, np.array([left_screen, chain_y]), np.array([right_screen, chain_y]), color, 2)
        draw_arrowhead(image, np.array([left_screen, chain_y]), np.array([1.0, 0.0]), color, size=10.0)
        draw_arrowhead(image, np.array([right_screen, chain_y]), np.array([-1.0, 0.0]), color, size=10.0)
        draw_label_box(
            image,
            (left_screen + right_screen) / 2.0,
            chain_y - 24,
            [f"{right_world - left_world:.1f} M"],
            scale=3,
            text_color=color,
            fill_color=np.array([0.99, 0.99, 0.99], dtype=np.float64),
            border_color=extension_color,
        )

    draw_thick_line(image, np.array([screen_values[0], overall_y]), np.array([screen_values[-1], overall_y]), color, 2)
    draw_arrowhead(image, np.array([screen_values[0], overall_y]), np.array([1.0, 0.0]), color, size=12.0)
    draw_arrowhead(image, np.array([screen_values[-1], overall_y]), np.array([-1.0, 0.0]), color, size=12.0)
    total_world = world_values[-1] - world_values[0]
    draw_label_box(
        image,
        (screen_values[0] + screen_values[-1]) / 2.0,
        overall_y - 26,
        [f"{total_world:.1f} M OVERALL"],
        scale=3,
        text_color=color,
        fill_color=np.array([0.99, 0.99, 0.99], dtype=np.float64),
        border_color=extension_color,
    )


def draw_dimension_chain_vertical(
    image: np.ndarray,
    world_values: list[float],
    screen_values: list[float],
    anchor_x: float,
    chain_x: float,
    overall_x: float,
    color: np.ndarray,
) -> None:
    extension_color = mix(color, np.ones(3, dtype=np.float64), 0.65)
    for screen_y in screen_values:
        draw_thick_line(image, np.array([anchor_x, screen_y]), np.array([overall_x - 16, screen_y]), extension_color, 2)

    for low_world, high_world, low_screen, high_screen in zip(
        world_values[:-1],
        world_values[1:],
        screen_values[1:],
        screen_values[:-1],
    ):
        draw_thick_line(image, np.array([chain_x, low_screen]), np.array([chain_x, high_screen]), color, 2)
        draw_arrowhead(image, np.array([chain_x, low_screen]), np.array([0.0, -1.0]), color, size=10.0)
        draw_arrowhead(image, np.array([chain_x, high_screen]), np.array([0.0, 1.0]), color, size=10.0)
        draw_label_box(
            image,
            chain_x - 52,
            (low_screen + high_screen) / 2.0,
            [f"{high_world - low_world:.1f} M"],
            scale=3,
            text_color=color,
            fill_color=np.array([0.99, 0.99, 0.99], dtype=np.float64),
            border_color=extension_color,
        )

    draw_thick_line(image, np.array([overall_x, screen_values[-1]]), np.array([overall_x, screen_values[0]]), color, 2)
    draw_arrowhead(image, np.array([overall_x, screen_values[-1]]), np.array([0.0, -1.0]), color, size=12.0)
    draw_arrowhead(image, np.array([overall_x, screen_values[0]]), np.array([0.0, 1.0]), color, size=12.0)
    total_world = world_values[-1] - world_values[0]
    draw_label_box(
        image,
        overall_x - 56,
        (screen_values[0] + screen_values[-1]) / 2.0,
        [f"{total_world:.1f} M"],
        scale=3,
        text_color=color,
        fill_color=np.array([0.99, 0.99, 0.99], dtype=np.float64),
        border_color=extension_color,
    )


def draw_scale_bar(image: np.ndarray, x: float, y: float, scale_px_per_m: float, length_m: float) -> None:
    segment_count = 4
    segment_length_m = length_m / segment_count
    segment_width_px = segment_length_m * scale_px_per_m
    bar_height = 22
    black = np.array([0.12, 0.12, 0.12], dtype=np.float64)
    white = np.array([0.98, 0.98, 0.98], dtype=np.float64)
    outline = np.array([0.24, 0.24, 0.24], dtype=np.float64)
    draw_text(image, x, y - 44, "SCALE BAR", outline, 4)
    for segment_index in range(segment_count):
        fill = black if segment_index % 2 == 0 else white
        fill_rect(
            image,
            x + segment_index * segment_width_px,
            y,
            x + (segment_index + 1) * segment_width_px,
            y + bar_height,
            fill,
        )
    stroke_rect(image, x, y, x + segment_width_px * segment_count, y + bar_height, outline, 2)
    for segment_index in range(segment_count + 1):
        label = f"{segment_index * segment_length_m:.0f}"
        draw_text(
            image,
            x + segment_index * segment_width_px,
            y + bar_height + 14,
            label,
            outline,
            3,
            align="center",
        )
    draw_text(image, x + segment_width_px * segment_count + 24, y + 2, f"{length_m:.0f} M", outline, 3)


def draw_north_arrow(image: np.ndarray, center_x: float, top_y: float, color: np.ndarray) -> None:
    shaft_top = np.array([center_x, top_y + 16], dtype=np.float64)
    shaft_bottom = np.array([center_x, top_y + 132], dtype=np.float64)
    draw_thick_line(image, shaft_bottom, shaft_top, color, 5)
    draw_arrowhead(image, shaft_top, np.array([0.0, -1.0]), color, size=22.0)
    draw_text(image, center_x, top_y + 150, "MODEL", color, 4, align="center")
    draw_text(image, center_x, top_y + 184, "NORTH", color, 4, align="center")


def shorten_space_name(full_name: str) -> str:
    name = full_name
    if " - STORY" in name.upper():
        name = name[: name.upper().rfind(" - STORY")]
    name = name.replace("SecondarySchool ", "")
    name = name.replace("Gym - audience", "GYM AUD")
    name = name.replace("Auditorium", "AUD")
    name = name.replace("Gym", "GYM")
    name = name.replace("end_a", "EA")
    name = name.replace("end_b", "EB")
    name = " ".join(name.split())
    return sanitize_text(name)


def collect_floorplan_metadata(objects: list[MeshObject], model_name: str) -> tuple[FloorplanMetadata, list[MeshObject]]:
    story_areas: dict[str, float] = defaultdict(float)
    for mesh_object in objects:
        if mesh_object.surface_type != "Floor":
            continue
        story_areas[mesh_object.story] += triangle_area_sum(mesh_object.positions, mesh_object.triangles)

    if not story_areas:
        raise RuntimeError("The model did not contain any floor geometry for floorplan rendering.")

    selected_story = max(story_areas, key=story_areas.get)
    story_floor_objects = [
        mesh_object
        for mesh_object in objects
        if mesh_object.story == selected_story and mesh_object.surface_type == "Floor"
    ]
    focus_bbox = select_focus_bbox(story_floor_objects, objects)
    story_objects = [
        mesh_object
        for mesh_object in objects
        if mesh_object.story == selected_story and boxes_overlap(bbox_xz(mesh_object), focus_bbox, 2.0)
    ]
    focus_objects = [mesh_object for mesh_object in objects if boxes_overlap(bbox_xz(mesh_object), focus_bbox, 2.0)]

    spaces_unsorted: list[SpaceSummary] = []
    x_boundaries_raw: list[float] = []
    z_boundaries_raw: list[float] = []
    for mesh_object in story_floor_objects:
        if not boxes_overlap(bbox_xz(mesh_object), focus_bbox, 2.0):
            continue
        box = bbox_xz(mesh_object)
        x_boundaries_raw.extend([box[0], box[1]])
        z_boundaries_raw.extend([box[2], box[3]])
        spaces_unsorted.append(
            SpaceSummary(
                room_id="",
                short_name=shorten_space_name(mesh_object.space_name or mesh_object.name),
                full_name=mesh_object.space_name or mesh_object.name,
                area_m2=triangle_area_sum(mesh_object.positions, mesh_object.triangles),
                width_m=box[1] - box[0],
                depth_m=box[3] - box[2],
                center_xz=np.array([(box[0] + box[1]) / 2.0, (box[2] + box[3]) / 2.0], dtype=np.float64),
                bbox_xz=box,
            )
        )

    spaces_unsorted.sort(key=lambda item: (-item.center_xz[1], item.center_xz[0], item.short_name))
    spaces = [
        SpaceSummary(
            room_id=f"{index:02d}",
            short_name=space.short_name,
            full_name=space.full_name,
            area_m2=space.area_m2,
            width_m=space.width_m,
            depth_m=space.depth_m,
            center_xz=space.center_xz,
            bbox_xz=space.bbox_xz,
        )
        for index, space in enumerate(spaces_unsorted, start=1)
    ]

    opening_objects = [
        mesh_object
        for mesh_object in story_objects
        if mesh_object.surface_type in OPENING_SURFACE_TYPES
    ]
    opening_objects.sort(
        key=lambda item: (
            -float(item.positions[:, 2].mean()),
            float(item.positions[:, 0].mean()),
            item.surface_type,
            item.name,
        )
    )
    openings: list[OpeningSummary] = []
    for index, mesh_object in enumerate(opening_objects, start=1):
        endpoints = segment_endpoints(mesh_object.positions[:, [0, 2]])
        if endpoints is None:
            continue
        openings.append(
            OpeningSummary(
                opening_id=f"O{index:02d}",
                opening_type=sanitize_text(mesh_object.surface_type),
                span_m=float(np.linalg.norm(endpoints[1] - endpoints[0])),
                sill_m=float(mesh_object.positions[:, 1].min()),
                head_m=float(mesh_object.positions[:, 1].max()),
                center_xz=endpoints.mean(axis=0),
                wall_name=sanitize_text(mesh_object.name),
                space_name=sanitize_text(mesh_object.space_name or mesh_object.name),
            )
        )

    exterior_wall_thicknesses = [
        mesh_object.construction_thickness_m
        for mesh_object in story_objects
        if mesh_object.surface_type == "Wall"
        and mesh_object.outside_boundary in OUTDOOR_BOUNDARIES
    ]
    interior_wall_thicknesses = [
        mesh_object.construction_thickness_m
        for mesh_object in story_objects
        if mesh_object.surface_type == "Wall"
        and mesh_object.outside_boundary not in OUTDOOR_BOUNDARIES
    ]
    min_y = min(float(mesh_object.positions[:, 1].min()) for mesh_object in focus_objects)
    max_y = max(float(mesh_object.positions[:, 1].max()) for mesh_object in focus_objects)
    metadata = FloorplanMetadata(
        model_name=sanitize_text(model_name.replace("_", " ")),
        selected_story=sanitize_text(selected_story),
        focus_bbox=focus_bbox,
        overall_width_m=focus_bbox[1] - focus_bbox[0],
        overall_depth_m=focus_bbox[3] - focus_bbox[2],
        height_m=max_y - min_y,
        x_boundaries_m=cluster_values(x_boundaries_raw, tolerance=0.35),
        z_boundaries_m=cluster_values(z_boundaries_raw, tolerance=0.35),
        spaces=spaces,
        window_count=sum(1 for opening in openings if opening.opening_type in {sanitize_text(value) for value in WINDOW_SURFACE_TYPES}),
        door_count=sum(1 for opening in openings if opening.opening_type in {sanitize_text(value) for value in DOOR_SURFACE_TYPES}),
        exterior_wall_thickness_range_m=wall_thickness_range(exterior_wall_thicknesses),
        interior_wall_thickness_range_m=wall_thickness_range(interior_wall_thicknesses),
        openings=openings,
    )
    return metadata, story_objects


def write_floorplan_schedule_csv(output_path: Path, metadata: FloorplanMetadata) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["room_id", "short_name", "full_name", "width_m", "depth_m", "area_m2"])
        for space in metadata.spaces:
            writer.writerow(
                [
                    space.room_id,
                    space.short_name,
                    space.full_name,
                    f"{space.width_m:.3f}",
                    f"{space.depth_m:.3f}",
                    f"{space.area_m2:.3f}",
                ]
            )


def write_floorplan_openings_csv(output_path: Path, metadata: FloorplanMetadata) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "opening_id",
                "opening_type",
                "span_m",
                "sill_m",
                "head_m",
                "center_x_m",
                "center_z_m",
                "space_name",
                "wall_name",
            ]
        )
        for opening in metadata.openings:
            writer.writerow(
                [
                    opening.opening_id,
                    opening.opening_type,
                    f"{opening.span_m:.3f}",
                    f"{opening.sill_m:.3f}",
                    f"{opening.head_m:.3f}",
                    f"{opening.center_xz[0]:.3f}",
                    f"{opening.center_xz[1]:.3f}",
                    opening.space_name,
                    opening.wall_name,
                ]
            )


def write_space_type_loads_csv(output_path: Path, metadata: FloorplanMetadata) -> None:
    if metadata.energy_model is None:
        return

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "space_type_name",
                "area_m2",
                "people_per_m2",
                "lights_w_per_m2",
                "equipment_w_per_m2",
                "oa_per_person_m3_s",
                "oa_per_area_m3_s_m2",
            ]
        )
        for summary in metadata.energy_model.space_type_loads:
            writer.writerow(
                [
                    summary.space_type_name,
                    f"{summary.area_m2:.3f}",
                    f"{summary.people_per_m2:.5f}",
                    f"{summary.lights_w_per_m2:.5f}",
                    f"{summary.equipment_w_per_m2:.5f}",
                    f"{summary.oa_per_person_m3_s:.7f}",
                    f"{summary.oa_per_area_m3_s_m2:.7f}",
                ]
            )


def write_energy_model_summary(output_path: Path, metadata: FloorplanMetadata) -> None:
    if metadata.energy_model is None:
        return

    energy_model = metadata.energy_model
    lines = [
        f"MODEL NAME: {metadata.model_name}",
        f"STORIES: {energy_model.story_count:d}",
        f"THERMAL ZONES: {energy_model.thermal_zone_count:d}",
        f"TOTAL FLOOR AREA (M2): {energy_model.total_floor_area_m2:.3f}",
        f"AIR LOOP COUNT: {energy_model.air_loop_count:d}",
        f"AIR LOOPS: {' | '.join(compact_loop_name(name) for name in energy_model.air_loop_names)}",
        f"VAV REHEAT TERMINALS: {energy_model.vav_terminal_count:d}",
        f"ZONE EXHAUST FANS: {energy_model.zone_exhaust_fan_count:d}",
        f"SUPPLY FAN EFFICIENCY: {format_numeric_range(energy_model.fan_efficiency_range, decimals=3)}",
        f"HEATING SETPOINT RANGE (C): {format_numeric_range(energy_model.heating_setpoint_range_c, decimals=3)}",
        f"COOLING SETPOINT RANGE (C): {format_numeric_range(energy_model.cooling_setpoint_range_c, decimals=3)}",
        f"BOILERS: {energy_model.boiler_count:d} | FUEL: {energy_model.boiler_fuel} | EFFICIENCY: {format_numeric_range(energy_model.boiler_efficiency_range, decimals=3)}",
        f"CHILLERS: {energy_model.chiller_count:d} | COP: {format_numeric_range(energy_model.chiller_cop_range, decimals=3)}",
        f"COOLING TOWERS: {energy_model.cooling_tower_count:d}",
        f"SERVICE WATER LOOPS: {energy_model.service_water_loop_count:d}",
        f"WATER HEATERS: {energy_model.water_heater_count:d} | FUEL: {energy_model.water_heater_fuel} | EFFICIENCY: {format_numeric_range(energy_model.water_heater_efficiency_range, decimals=3)}",
        f"PRIMARY GLAZING: {energy_model.glazing_name}",
        f"GLAZING U FACTOR (W M-2 K-1): {energy_model.glazing_u_w_m2k:.3f}" if energy_model.glazing_u_w_m2k is not None else "GLAZING U FACTOR (W M-2 K-1): N A",
        f"GLAZING SHGC: {energy_model.glazing_shgc:.3f}" if energy_model.glazing_shgc is not None else "GLAZING SHGC: N A",
        f"GLAZING VT: {energy_model.glazing_vt:.3f}" if energy_model.glazing_vt is not None else "GLAZING VT: N A",
        "WEATHER INPUT: EPW FILE REQUIRED. WEATHER DATA IS NOT EMBEDDED IN THE OSM.",
        "",
        "SPACE TYPE LOADS:",
    ]
    for summary in energy_model.space_type_loads:
        lines.append(
            f"{compact_space_type_name(summary.space_type_name)} | AREA {summary.area_m2:.3f} M2 | PEOPLE {summary.people_per_m2:.5f} /M2 | LIGHTS {summary.lights_w_per_m2:.5f} W/M2 | EQUIP {summary.equipment_w_per_m2:.5f} W/M2 | OA PERSON {summary.oa_per_person_m3_s:.7f} M3/S-PERSON | OA AREA {summary.oa_per_area_m3_s_m2:.7f} M3/S-M2"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_floorplan_notes(output_path: Path, metadata: FloorplanMetadata) -> None:
    x_bays = [metadata.x_boundaries_m[index + 1] - metadata.x_boundaries_m[index] for index in range(len(metadata.x_boundaries_m) - 1)]
    z_bays = [metadata.z_boundaries_m[index + 1] - metadata.z_boundaries_m[index] for index in range(len(metadata.z_boundaries_m) - 1)]
    lines = [
        f"MODEL NAME: {metadata.model_name}",
        f"SELECTED STORY: {metadata.selected_story}",
        f"FOCUS BBOX X/Z (M): {metadata.focus_bbox[0]:.3f}, {metadata.focus_bbox[1]:.3f}, {metadata.focus_bbox[2]:.3f}, {metadata.focus_bbox[3]:.3f}",
        f"OVERALL FOOTPRINT (M): {metadata.overall_width_m:.3f} x {metadata.overall_depth_m:.3f}",
        f"OVERALL FOOTPRINT (FT): {meters_to_feet(metadata.overall_width_m):.3f} x {meters_to_feet(metadata.overall_depth_m):.3f}",
        f"APPROX BUILDING HEIGHT (M): {metadata.height_m:.3f}",
        f"APPROX BUILDING HEIGHT (FT): {meters_to_feet(metadata.height_m):.3f}",
        f"X BAY WIDTHS (M): {' | '.join(f'{value:.3f}' for value in x_bays)}",
        f"Z BAY DEPTHS (M): {' | '.join(f'{value:.3f}' for value in z_bays)}",
        f"EXTERIOR WALL THICKNESS (M): {format_thickness_range(metadata.exterior_wall_thickness_range_m)}",
        f"INTERIOR WALL THICKNESS (M): {format_thickness_range(metadata.interior_wall_thickness_range_m)}",
        f"MODELED WINDOWS ON SHEET: {metadata.window_count:d}",
        f"MODELED DOORS ON SHEET: {metadata.door_count:d}",
        "",
        "ROOM SCHEDULE:",
    ]
    for space in metadata.spaces:
        lines.append(
            f"{space.room_id} | {space.short_name} | {space.full_name} | {space.width_m:.3f} x {space.depth_m:.3f} M | {space.area_m2:.3f} M2"
        )
    if metadata.openings:
        lines.extend(["", "OPENING SCHEDULE:"])
        for opening in metadata.openings:
            lines.append(
                f"{opening.opening_id} | {opening.opening_type} | {opening.span_m:.3f} M | SILL {opening.sill_m:.3f} M | HEAD {opening.head_m:.3f} M | {opening.space_name}"
            )
    lines.extend(
        [
            "",
            "NOTES:",
            "- ROOM DIMENSIONS ARE DERIVED FROM FLOOR BOUNDING BOXES IN MODEL COORDINATES.",
            "- PAGE UP IS MODEL NORTH FOR THIS DRAWING.",
            "- WALL BANDS USE THE MODELED CONSTRUCTION THICKNESS WHEN AVAILABLE.",
            "- WINDOW SPANS ARE DRAWN FROM THE MODELED SUBSURFACE EDGES.",
            "- THE OPENING CSV PROVIDES EXACT SPAN AND SILL HEAD DATA FOR REBUILDING.",
            f"- THIS STORY CONTAINS {metadata.door_count:d} MODELED DOOR SUBSURFACES.",
            "- HEIGHT IS THE VERTICAL EXTENT OF THE FOCUSED MASS, NOT A CONSTRUCTION DETAIL.",
        ]
    )
    if metadata.energy_model is not None:
        lines.extend(["", "ANNUAL ENERGY MODEL INPUTS:"])
        lines.extend(f"- {line}" for line in build_simulation_panel_lines(metadata.energy_model))
        lines.extend(["", "DOMINANT SPACE TYPE LOADS:"])
        for summary in metadata.energy_model.space_type_loads[:5]:
            lines.append(
                f"- {compact_space_type_name(summary.space_type_name)} | AREA {summary.area_m2:.1f} M2 | P {summary.people_per_m2:.3f} /M2 | L {summary.lights_w_per_m2:.2f} W/M2 | E {summary.equipment_w_per_m2:.2f} W/M2"
            )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_wall_bands(story_objects: list[MeshObject]) -> list[WallBandSummary]:
    wall_groups: dict[tuple[tuple[int, int], tuple[int, int]], list[tuple[np.ndarray, MeshObject]]] = defaultdict(list)
    for mesh_object in story_objects:
        if mesh_object.surface_type != "Wall":
            continue
        endpoints = segment_endpoints(mesh_object.positions[:, [0, 2]])
        if endpoints is None:
            continue
        key = segment_key(mesh_object.positions[:, [0, 2]])
        if key is None:
            continue
        wall_groups[key].append((endpoints, mesh_object))

    merged: list[WallBandSummary] = []
    for entries in wall_groups.values():
        reference = entries[0][0]
        aligned: list[np.ndarray] = []
        for endpoints, _ in entries:
            candidate = endpoints
            if float(np.dot(candidate[1] - candidate[0], reference[1] - reference[0])) < 0.0:
                candidate = candidate[::-1]
            aligned.append(candidate)
        averaged = np.mean(np.stack(aligned, axis=0), axis=0)
        representative = entries[0][1]
        merged.append(
            WallBandSummary(
                endpoints_xz=averaged,
                outside_boundary=(
                    "Outdoors"
                    if any(item.outside_boundary in OUTDOOR_BOUNDARIES for _, item in entries)
                    else representative.outside_boundary
                ),
                thickness_m=max(
                    (
                        item.construction_thickness_m
                        for _, item in entries
                        if item.construction_thickness_m > 1e-4
                    ),
                    default=0.24 if representative.outside_boundary in OUTDOOR_BOUNDARIES else 0.12,
                ),
                source_name=representative.name,
            )
        )

    merged.sort(
        key=lambda item: (
            0 if item.outside_boundary in OUTDOOR_BOUNDARIES else 1,
            -float(item.endpoints_xz[:, 1].mean()),
            float(item.endpoints_xz[:, 0].mean()),
            item.source_name,
        )
    )
    return merged


def render_floorplan(
    objects: list[MeshObject],
    output_path: Path,
    model_name: str,
    energy_model: EnergyModelMetadata,
) -> FloorplanMetadata:
    metadata, story_objects = collect_floorplan_metadata(objects, model_name)
    metadata.energy_model = energy_model
    plan_points = np.concatenate([mesh_object.positions[:, [0, 2]] for mesh_object in story_objects], axis=0)
    wall_bands = merge_wall_bands(story_objects)
    opening_objects = [mesh_object for mesh_object in story_objects if mesh_object.surface_type in OPENING_SURFACE_TYPES]
    opening_objects.sort(
        key=lambda item: (
            -float(item.positions[:, 2].mean()),
            float(item.positions[:, 0].mean()),
            item.surface_type,
            item.name,
        )
    )

    ui_scale = 1.34

    def px(value: float) -> int:
        return int(round(value * ui_scale))

    def ts(value: int) -> int:
        return max(1, int(round(value * ui_scale)))

    def scale_rect(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(px(value) for value in rect)

    width = px(4280)
    height = px(3340)
    plan_panel = scale_rect((80, 80, 2790, 2380))
    sidebar = scale_rect((2880, 80, 4200, 2380))
    title_block = scale_rect((80, 2440, 4200, 3260))
    plan_width = plan_panel[2] - plan_panel[0]
    plan_height = plan_panel[3] - plan_panel[1]
    padding = px(180)
    min_x, min_z, scale = fit_plan(plan_points, plan_width, plan_height, padding)

    image = np.ones((height, width, 3), dtype=np.float32)
    image[:] = np.array([0.972, 0.968, 0.960], dtype=np.float32)

    sheet_border = np.array([0.16, 0.18, 0.20], dtype=np.float64)
    panel_fill = np.array([0.992, 0.990, 0.986], dtype=np.float64)
    sidebar_fill = np.array([0.985, 0.986, 0.988], dtype=np.float64)
    title_fill = np.array([0.980, 0.982, 0.985], dtype=np.float64)
    note_fill = np.array([0.988, 0.990, 0.992], dtype=np.float64)
    exterior_wall_fill = np.array([0.20, 0.20, 0.19], dtype=np.float64)
    exterior_wall_edge = np.array([0.08, 0.08, 0.07], dtype=np.float64)
    interior_wall_fill = np.array([0.46, 0.45, 0.43], dtype=np.float64)
    interior_wall_edge = np.array([0.22, 0.22, 0.21], dtype=np.float64)
    window_color = np.array([0.13, 0.44, 0.72], dtype=np.float64)
    door_color = np.array([0.76, 0.48, 0.18], dtype=np.float64)
    accent_color = np.array([0.13, 0.34, 0.56], dtype=np.float64)
    dim_color = np.array([0.26, 0.29, 0.33], dtype=np.float64)
    text_color = np.array([0.12, 0.12, 0.13], dtype=np.float64)
    muted_text = np.array([0.30, 0.31, 0.33], dtype=np.float64)

    stroke_rect(image, px(40), px(40), width - px(40), height - px(40), sheet_border, px(4))
    fill_rect(image, *plan_panel, panel_fill)
    fill_rect(image, *sidebar, sidebar_fill)
    fill_rect(image, *title_block, title_fill)
    stroke_rect(image, *plan_panel, sheet_border, px(3))
    stroke_rect(image, *sidebar, sheet_border, px(3))
    stroke_rect(image, *title_block, sheet_border, px(3))

    fill_rect(image, plan_panel[0] + px(18), plan_panel[1] + px(18), plan_panel[2] - px(18), plan_panel[1] + px(112), note_fill)
    stroke_rect(image, plan_panel[0] + px(18), plan_panel[1] + px(18), plan_panel[2] - px(18), plan_panel[1] + px(112), sheet_border, px(1))
    draw_text(image, plan_panel[0] + px(38), plan_panel[1] + px(36), "MODELED WALL THICKNESS AND OPENING SPANS", accent_color, ts(5))
    if metadata.door_count == 0:
        draw_text(image, plan_panel[0] + px(38), plan_panel[1] + px(70), "WINDOWS FOLLOW THE MODELED SPANS  NO DOOR GEOMETRY IN SOURCE OSM", muted_text, ts(4))
    else:
        draw_text(image, plan_panel[0] + px(38), plan_panel[1] + px(70), "WINDOWS AND DOORS FOLLOW THE MODELED SUBSURFACE SPANS", muted_text, ts(4))

    for mesh_object in story_objects:
        if mesh_object.surface_type != "Floor":
            continue
        base = hash_pastel(mesh_object.space_name or mesh_object.name)
        fill = mix(base, np.array([1.0, 1.0, 1.0], dtype=np.float64), 0.20)
        projected_vertices = project_plan(mesh_object.positions[:, [0, 2]], min_x, min_z, scale, plan_width, plan_height, padding)
        projected_vertices[:, 0] += plan_panel[0]
        projected_vertices[:, 1] += plan_panel[1]
        for triangle in mesh_object.triangles:
            fill_triangle(image, projected_vertices[triangle], fill)

    for mesh_object in story_objects:
        if mesh_object.surface_type != "Floor":
            continue
        projected_vertices = project_plan(mesh_object.positions[:, [0, 2]], min_x, min_z, scale, plan_width, plan_height, padding)
        projected_vertices[:, 0] += plan_panel[0]
        projected_vertices[:, 1] += plan_panel[1]
        edges = boundary_edges(mesh_object.triangles)
        for start_index, end_index in edges:
            draw_thick_line(
                image,
                projected_vertices[start_index],
                projected_vertices[end_index],
                mix(sheet_border, np.ones(3, dtype=np.float64), 0.56),
                px(2),
            )

    for wall_band in wall_bands:
        projected_endpoints = project_plan(wall_band.endpoints_xz, min_x, min_z, scale, plan_width, plan_height, padding)
        projected_endpoints[:, 0] += plan_panel[0]
        projected_endpoints[:, 1] += plan_panel[1]
        thickness_px = max(wall_band.thickness_m * scale, float(px(5) if wall_band.outside_boundary in OUTDOOR_BOUNDARIES else px(3)))
        polygon = wall_band_polygon(projected_endpoints[0], projected_endpoints[1], thickness_px)
        if polygon is None:
            continue
        fill_color = exterior_wall_fill if wall_band.outside_boundary in OUTDOOR_BOUNDARIES else interior_wall_fill
        edge_color = exterior_wall_edge if wall_band.outside_boundary in OUTDOOR_BOUNDARIES else interior_wall_edge
        fill_polygon(image, polygon, fill_color)
        stroke_polygon(image, polygon, edge_color, max(px(1), int(round(thickness_px * 0.16))))
        draw_thick_line(
            image,
            projected_endpoints[0],
            projected_endpoints[1],
            mix(edge_color, np.zeros(3, dtype=np.float64), 0.10),
            max(px(1), int(round(thickness_px * 0.10))),
        )

    for mesh_object in opening_objects:
        endpoints = segment_endpoints(mesh_object.positions[:, [0, 2]])
        if endpoints is None:
            continue
        projected_endpoints = project_plan(endpoints, min_x, min_z, scale, plan_width, plan_height, padding)
        projected_endpoints[:, 0] += plan_panel[0]
        projected_endpoints[:, 1] += plan_panel[1]
        host_thickness_m = mesh_object.construction_thickness_m if mesh_object.construction_thickness_m > 1e-4 else (
            0.24 if mesh_object.outside_boundary in OUTDOOR_BOUNDARIES else 0.12
        )
        opening_thickness_px = max(host_thickness_m * scale - px(2), float(px(3)))
        polygon = wall_band_polygon(projected_endpoints[0], projected_endpoints[1], opening_thickness_px)
        if polygon is None:
            continue
        opening_color = window_color if mesh_object.surface_type in WINDOW_SURFACE_TYPES else door_color
        opening_fill = mix(opening_color, np.ones(3, dtype=np.float64), 0.82)
        fill_polygon(image, polygon, opening_fill)
        stroke_polygon(image, polygon, opening_color, px(2))
        draw_thick_line(image, projected_endpoints[0], projected_endpoints[1], opening_color, px(2))

    bbox_points = np.array(
        [
            [metadata.focus_bbox[0], metadata.focus_bbox[2]],
            [metadata.focus_bbox[1], metadata.focus_bbox[3]],
        ],
        dtype=np.float64,
    )
    projected_bbox = project_plan(bbox_points, min_x, min_z, scale, plan_width, plan_height, padding)
    projected_bbox[:, 0] += plan_panel[0]
    projected_bbox[:, 1] += plan_panel[1]
    left_x = float(projected_bbox[:, 0].min())
    right_x = float(projected_bbox[:, 0].max())
    top_y = float(projected_bbox[:, 1].min())
    bottom_y = float(projected_bbox[:, 1].max())

    screen_x_bounds = []
    for value in metadata.x_boundaries_m:
        projected = project_plan(
            np.array([[value, metadata.focus_bbox[3]]], dtype=np.float64),
            min_x,
            min_z,
            scale,
            plan_width,
            plan_height,
            padding,
        )[0]
        screen_x_bounds.append(float(projected[0] + plan_panel[0]))
    screen_z_bounds = []
    for value in metadata.z_boundaries_m:
        projected = project_plan(
            np.array([[metadata.focus_bbox[0], value]], dtype=np.float64),
            min_x,
            min_z,
            scale,
            plan_width,
            plan_height,
            padding,
        )[0]
        screen_z_bounds.append(float(projected[1] + plan_panel[1]))

    draw_dimension_chain_horizontal(
        image,
        metadata.x_boundaries_m,
        screen_x_bounds,
        top_y,
        top_y - px(90),
        top_y - px(156),
        dim_color,
    )
    draw_dimension_chain_vertical(
        image,
        metadata.z_boundaries_m,
        screen_z_bounds,
        left_x,
        left_x - px(118),
        left_x - px(236),
        dim_color,
    )
    draw_scale_bar(image, plan_panel[0] + px(140), plan_panel[3] - px(150), scale, 20.0)
    draw_north_arrow(image, plan_panel[2] - px(180), plan_panel[3] - px(240), accent_color)

    room_box_fill = np.array([0.997, 0.997, 0.997], dtype=np.float64)
    room_box_border = np.array([0.53, 0.55, 0.57], dtype=np.float64)
    occupied_label_boxes: list[tuple[float, float, float, float]] = []
    for space in metadata.spaces:
        projected_center = project_plan(space.center_xz.reshape(1, 2), min_x, min_z, scale, plan_width, plan_height, padding)[0]
        projected_center[0] += plan_panel[0]
        projected_center[1] += plan_panel[1]
        projected_box = project_plan(
            np.array(
                [
                    [space.bbox_xz[0], space.bbox_xz[2]],
                    [space.bbox_xz[1], space.bbox_xz[3]],
                ],
                dtype=np.float64,
            ),
            min_x,
            min_z,
            scale,
            plan_width,
            plan_height,
            padding,
        )
        projected_box[:, 0] += plan_panel[0]
        projected_box[:, 1] += plan_panel[1]
        room_width_px = abs(float(projected_box[1, 0] - projected_box[0, 0]))
        room_height_px = abs(float(projected_box[1, 1] - projected_box[0, 1]))

        primary_line = f"{space.room_id} {space.short_name}"
        detail_line = f"{space.width_m:.1f} X {space.depth_m:.1f} M"
        label_lines = [primary_line]
        label_scale = ts(3) if room_width_px > px(320) else ts(2)
        if room_height_px > px(126) and room_width_px > px(200):
            label_lines.append(detail_line)

        label_width, label_height = measure_multiline_text(label_lines, label_scale)
        if label_width > room_width_px - px(28) or label_height > room_height_px - px(28):
            label_lines = [space.room_id]
            label_scale = ts(3) if room_width_px > px(120) else ts(2)
        label_box = label_box_bounds(projected_center[0], projected_center[1], label_lines, label_scale)
        draw_label_box(
            image,
            projected_center[0],
            projected_center[1],
            label_lines,
            scale=label_scale,
            text_color=text_color,
            fill_color=room_box_fill,
            border_color=room_box_border,
        )
        occupied_label_boxes.append(expand_box(label_box, float(px(6))))

    occupied_label_boxes.extend(
        [
            (
                plan_panel[0] + px(96),
                plan_panel[3] - px(230),
                plan_panel[0] + px(620),
                plan_panel[3] - px(36),
            ),
            (
                plan_panel[2] - px(280),
                plan_panel[3] - px(290),
                plan_panel[2] - px(72),
                plan_panel[3] - px(16),
            ),
        ]
    )

    plan_center = np.array(
        [
            (metadata.focus_bbox[0] + metadata.focus_bbox[1]) / 2.0,
            (metadata.focus_bbox[2] + metadata.focus_bbox[3]) / 2.0,
        ],
        dtype=np.float64,
    )
    plan_container = (
        float(plan_panel[0] + px(8)),
        float(plan_panel[1] + px(118)),
        float(plan_panel[2] - px(8)),
        float(plan_panel[3] - px(8)),
    )
    opening_label_scale = ts(2)
    for opening_summary, mesh_object in zip(metadata.openings, opening_objects):
        endpoints = segment_endpoints(mesh_object.positions[:, [0, 2]])
        if endpoints is None:
            continue
        opening_center = endpoints.mean(axis=0)
        tangent = normalize(endpoints[1] - endpoints[0])
        normal = np.array([-tangent[1], tangent[0]], dtype=np.float64)
        if float(np.dot(normal, opening_center - plan_center)) < 0.0:
            normal = -normal
        projected_center = project_plan(
            opening_center.reshape(1, 2),
            min_x,
            min_z,
            scale,
            plan_width,
            plan_height,
            padding,
        )[0]
        projected_center[0] += plan_panel[0]
        projected_center[1] += plan_panel[1]
        label_color = window_color if mesh_object.surface_type in WINDOW_SURFACE_TYPES else door_color
        label_lines = [opening_summary.opening_id]
        label_center, label_box = choose_label_box_position(
            projected_center,
            normal,
            tangent,
            label_lines,
            opening_label_scale,
            occupied_label_boxes,
            plan_container,
            base_distance=float(px(14)),
            radial_step=float(px(10)),
            tangent_step=float(px(16)),
        )
        draw_thick_line(image, projected_center, label_center, label_color, px(1))
        draw_label_box(
            image,
            label_center[0],
            label_center[1],
            label_lines,
            scale=opening_label_scale,
            text_color=label_color,
            fill_color=np.array([0.997, 0.997, 0.997], dtype=np.float64),
            border_color=mix(label_color, np.ones(3, dtype=np.float64), 0.45),
        )
        occupied_label_boxes.append(expand_box(label_box, float(px(4))))

    draw_text(image, sidebar[0] + px(34), sidebar[1] + px(32), "ANNOTATED FLOOR PLAN", accent_color, ts(8))
    draw_text(image, sidebar[0] + px(34), sidebar[1] + px(96), metadata.model_name, text_color, ts(5))
    draw_text(image, sidebar[0] + px(34), sidebar[1] + px(142), f"STORY {metadata.selected_story}", text_color, ts(5))

    draw_north_arrow(image, sidebar[0] + px(150), sidebar[1] + px(178), accent_color)
    draw_scale_bar(image, sidebar[0] + px(34), sidebar[1] + px(510), scale, 10.0)

    metrics_x = sidebar[0] + px(34)
    metrics_y = sidebar[1] + px(620)
    metric_lines = [
        f"FOOTPRINT {metadata.overall_width_m:.1f} X {metadata.overall_depth_m:.1f} M",
        f"HEIGHT {metadata.height_m:.1f} M  {meters_to_feet(metadata.height_m):.1f} FT",
        f"TOTAL AREA {energy_model.total_floor_area_m2:.0f} M2",
        f"STORIES {energy_model.story_count:d}  ZONES {energy_model.thermal_zone_count:d}",
        f"AIR LOOPS {energy_model.air_loop_count:d} CENTRAL VAV",
        f"ROOM COUNT {len(metadata.spaces):d}",
        f"WINDOWS {metadata.window_count:d}",
        f"DOORS {metadata.door_count:d}",
        f"EXT WALL THK {format_thickness_range(metadata.exterior_wall_thickness_range_m)}",
        f"INT WALL THK {format_thickness_range(metadata.interior_wall_thickness_range_m)}",
        "DIMENSIONS SHOWN IN METERS",
    ]
    for index, line in enumerate(metric_lines):
        draw_text(image, metrics_x, metrics_y + index * px(40), line, muted_text, ts(4))

    legend_y = sidebar[1] + px(1110)
    draw_text(image, sidebar[0] + px(34), legend_y, "LEGEND", accent_color, ts(5))
    sample_x = sidebar[0] + px(60)
    sample_y = legend_y + px(58)
    exterior_sample = wall_band_polygon(
        np.array([sample_x, sample_y], dtype=np.float64),
        np.array([sample_x + px(92), sample_y], dtype=np.float64),
        px(12),
    )
    interior_sample = wall_band_polygon(
        np.array([sample_x, sample_y + px(56)], dtype=np.float64),
        np.array([sample_x + px(92), sample_y + px(56)], dtype=np.float64),
        px(6),
    )
    window_sample = wall_band_polygon(
        np.array([sample_x + px(14), sample_y + px(112)], dtype=np.float64),
        np.array([sample_x + px(78), sample_y + px(112)], dtype=np.float64),
        px(10),
    )
    if exterior_sample is not None:
        fill_polygon(image, exterior_sample, exterior_wall_fill)
        stroke_polygon(image, exterior_sample, exterior_wall_edge, px(1))
    if interior_sample is not None:
        fill_polygon(image, interior_sample, interior_wall_fill)
        stroke_polygon(image, interior_sample, interior_wall_edge, px(1))
    if window_sample is not None:
        fill_polygon(image, window_sample, panel_fill)
        stroke_polygon(image, window_sample, window_color, px(2))
    draw_text(image, sample_x + px(128), legend_y + px(38), "EXTERIOR WALL BAND", text_color, ts(4))
    draw_text(image, sample_x + px(128), legend_y + px(94), "INTERIOR WALL BAND", text_color, ts(4))
    draw_text(image, sample_x + px(128), legend_y + px(150), "MODELED WINDOW SPAN", text_color, ts(4))
    if metadata.door_count == 0:
        draw_text(image, sample_x + px(128), legend_y + px(206), "NO DOOR SUBSURFACES IN SOURCE OSM", muted_text, ts(3))
    else:
        door_sample = wall_band_polygon(
            np.array([sample_x + px(14), sample_y + px(168)], dtype=np.float64),
            np.array([sample_x + px(78), sample_y + px(168)], dtype=np.float64),
            px(10),
        )
        if door_sample is not None:
            fill_polygon(image, door_sample, panel_fill)
            stroke_polygon(image, door_sample, door_color, px(2))
        draw_text(image, sample_x + px(128), legend_y + px(206), "MODELED DOOR SPAN", text_color, ts(4))

    room_key_y = sidebar[1] + px(1450)
    draw_text(image, sidebar[0] + px(34), room_key_y, "ROOM KEY", accent_color, ts(5))
    draw_text(image, sidebar[0] + px(34), room_key_y + px(46), "ROOM OPENING LOAD AND ENERGY SUMMARIES EXPORTED", muted_text, ts(3))
    left_col_x = sidebar[0] + px(34)
    right_col_x = sidebar[0] + px(610)
    row_step = px(48)
    split_index = math.ceil(len(metadata.spaces) / 2)
    for index, space in enumerate(metadata.spaces):
        column_x = left_col_x if index < split_index else right_col_x
        row_y = room_key_y + px(94) + row_step * (index if index < split_index else index - split_index)
        draw_text(image, column_x, row_y, f"{space.room_id} {space.short_name}", text_color, ts(4))

    x_bays = [metadata.x_boundaries_m[index + 1] - metadata.x_boundaries_m[index] for index in range(len(metadata.x_boundaries_m) - 1)]
    z_bays = [metadata.z_boundaries_m[index + 1] - metadata.z_boundaries_m[index] for index in range(len(metadata.z_boundaries_m) - 1)]
    drawing_panel = (
        title_block[0] + px(22),
        title_block[1] + px(22),
        title_block[0] + px(920),
        title_block[3] - px(22),
    )
    notes_panel = (
        title_block[0] + px(960),
        title_block[1] + px(22),
        title_block[0] + px(2420),
        title_block[3] - px(22),
    )
    simulation_panel = (
        title_block[0] + px(2460),
        title_block[1] + px(22),
        title_block[2] - px(26),
        title_block[3] - px(22),
    )
    for panel in (drawing_panel, notes_panel, simulation_panel):
        fill_rect(image, *panel, note_fill)
        stroke_rect(image, *panel, sheet_border, px(2))

    drawing_lines = [
        "COMSTOCK RECONSTRUCTION SHEET",
        f"SOURCE {metadata.model_name}",
        f"OVERALL {metadata.overall_width_m:.1f} X {metadata.overall_depth_m:.1f} X {metadata.height_m:.1f} M",
        f"TOTAL FLOOR AREA {energy_model.total_floor_area_m2:.0f} M2",
        f"STORIES {energy_model.story_count:d}  THERMAL ZONES {energy_model.thermal_zone_count:d}",
        f"AIR LOOP 1 {compact_loop_name(energy_model.air_loop_names[0])}" if len(energy_model.air_loop_names) > 0 else "AIR LOOP 1 N A",
        f"AIR LOOP 2 {compact_loop_name(energy_model.air_loop_names[1])}" if len(energy_model.air_loop_names) > 1 else "AIR LOOP 2 N A",
        f"AIR LOOP 3 {compact_loop_name(energy_model.air_loop_names[2])}" if len(energy_model.air_loop_names) > 2 else "AIR LOOP 3 N A",
        "EXPORTS FLOORPLAN SCHEDULE AND OPENINGS CSV",
        "EXPORTS SPACE TYPE LOADS CSV AND ENERGY TXT",
    ]
    note_lines = [
        f"X BAYS {'  '.join(f'{value:.1f}' for value in x_bays)}",
        f"Z BAYS {'  '.join(f'{value:.1f}' for value in z_bays)}",
        *build_reconstruction_note_lines(metadata),
    ]
    simulation_lines = build_simulation_panel_lines(energy_model)

    footer_line_gap = px(12)
    for panel, header, lines in (
        (drawing_panel, "DRAWING", drawing_lines),
        (notes_panel, "RECONSTRUCTION NOTES", note_lines),
        (simulation_panel, "SIMULATION INPUTS", simulation_lines),
    ):
        draw_text(image, panel[0] + px(28), panel[1] + px(22), header, accent_color, ts(5))
        draw_multiline_text(
            image,
            panel[0] + px(28),
            panel[1] + px(72),
            lines,
            text_color if header != "DRAWING" else muted_text,
            ts(4),
            line_gap=footer_line_gap,
        )

    write_png(image, output_path, gamma_correct=False)
    write_floorplan_schedule_csv(output_path.with_name("floorplan_schedule.csv"), metadata)
    write_floorplan_openings_csv(output_path.with_name("floorplan_openings.csv"), metadata)
    write_space_type_loads_csv(output_path.with_name("space_type_loads.csv"), metadata)
    write_energy_model_summary(output_path.with_name("energy_model_summary.txt"), metadata)
    write_floorplan_notes(output_path.with_name("floorplan_reconstruction.txt"), metadata)
    return metadata


def build_camera(camera: Camera, width: int, height: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float, float]:
    forward = normalize(camera.target - camera.eye)
    right = normalize(np.cross(forward, camera.up))
    true_up = normalize(np.cross(right, forward))
    focal_y = height / (2.0 * math.tan(math.radians(camera.fov_y_deg) / 2.0))
    focal_x = focal_y
    center_x = width / 2.0
    center_y = height / 2.0
    return forward, right, true_up, focal_x, focal_y, center_x, center_y


def project_perspective(points: np.ndarray, camera: Camera, width: int, height: int) -> tuple[np.ndarray, np.ndarray] | None:
    forward, right, true_up, focal_x, focal_y, center_x, center_y = build_camera(camera, width, height)
    relative = points - camera.eye
    camera_x = relative @ right
    camera_y = relative @ true_up
    camera_z = relative @ forward
    if float(camera_z.min()) <= 1.0:
        return None

    projected = np.empty((len(points), 2), dtype=np.float64)
    projected[:, 0] = center_x + focal_x * camera_x / camera_z
    projected[:, 1] = center_y - focal_y * camera_y / camera_z
    return projected, camera_z


def shade_triangle(mesh_object: MeshObject, vertices: np.ndarray, camera: Camera, sun_direction: np.ndarray) -> tuple[np.ndarray, float]:
    base_color = mesh_object.color.astype(np.float64)
    if mesh_object.surface_type == "GroundPlane":
        light = 0.92 + 0.08 * max(0.0, float(np.dot(np.array([0.0, 1.0, 0.0]), sun_direction)))
        return np.clip(base_color * light, 0.0, 1.0), 1.0
    if mesh_object.surface_type == "Shadow":
        return np.clip(base_color, 0.0, 1.0), mesh_object.alpha

    normal = normalize(np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0]))
    centroid = vertices.mean(axis=0)
    view_direction = normalize(camera.eye - centroid)
    if float(np.dot(normal, view_direction)) < 0.0:
        normal = -normal

    if mesh_object.surface_type == "FixedWindow":
        fresnel = (1.0 - max(0.0, float(np.dot(normal, view_direction)))) ** 2
        sky_tint = np.array([0.66, 0.82, 0.95], dtype=np.float64)
        shaded = base_color * 0.18 + sky_tint * (0.52 + 0.24 * fresnel)
        return np.clip(shaded, 0.0, 1.0), 0.55

    ambient = 0.34
    diffuse = 0.54 * max(0.0, float(np.dot(normal, sun_direction)))
    sky_bounce = 0.10 * max(0.0, float(normal[1]))
    shaded = base_color * (ambient + diffuse)
    shaded = mix(shaded, np.array([0.94, 0.96, 0.99], dtype=np.float64), sky_bounce)

    if mesh_object.surface_type == "RoofCeiling":
        shaded *= np.array([1.06, 0.99, 0.99], dtype=np.float64)
    elif mesh_object.surface_type == "Floor":
        shaded *= np.array([0.94, 0.94, 0.96], dtype=np.float64)
    elif mesh_object.surface_type == "Wall":
        shaded *= np.array([1.00, 0.99, 0.96], dtype=np.float64)

    return np.clip(shaded, 0.0, 1.0), 1.0


def rasterize_triangle(
    image: np.ndarray,
    depth_buffer: np.ndarray,
    object_buffer: np.ndarray,
    projected_triangle: ProjectedTriangle,
) -> None:
    height, width, _ = image.shape
    points = projected_triangle.points
    min_x = max(0, int(math.floor(float(points[:, 0].min()))))
    max_x = min(width - 1, int(math.ceil(float(points[:, 0].max()))))
    min_y = max(0, int(math.floor(float(points[:, 1].min()))))
    max_y = min(height - 1, int(math.ceil(float(points[:, 1].max()))))
    if min_x > max_x or min_y > max_y:
        return

    xs, ys = np.meshgrid(
        np.arange(min_x, max_x + 1, dtype=np.float64) + 0.5,
        np.arange(min_y, max_y + 1, dtype=np.float64) + 0.5,
    )
    area = edge_function(points[0], points[1], points[2, 0], points[2, 1])
    if abs(area) < 1e-8:
        return

    inv_area = 1.0 / area
    weight0 = edge_function(points[1], points[2], xs, ys) * inv_area
    weight1 = edge_function(points[2], points[0], xs, ys) * inv_area
    weight2 = 1.0 - weight0 - weight1
    inside = (weight0 >= -1e-7) & (weight1 >= -1e-7) & (weight2 >= -1e-7)
    if not np.any(inside):
        return

    local_depth = depth_buffer[min_y:max_y + 1, min_x:max_x + 1]
    depth_values = (
        weight0 * projected_triangle.depths[0]
        + weight1 * projected_triangle.depths[1]
        + weight2 * projected_triangle.depths[2]
    )
    tile = image[min_y:max_y + 1, min_x:max_x + 1]

    if projected_triangle.alpha >= 0.999:
        visible = inside & (depth_values < local_depth)
        if not np.any(visible):
            return
        tile[visible] = projected_triangle.color
        local_depth[visible] = depth_values[visible]
        object_tile = object_buffer[min_y:max_y + 1, min_x:max_x + 1]
        object_tile[visible] = projected_triangle.object_id
        return

    visible = inside & (depth_values <= local_depth + projected_triangle.depth_slack)
    if not np.any(visible):
        return
    tile[visible] = tile[visible] * (1.0 - projected_triangle.alpha) + projected_triangle.color * projected_triangle.alpha


def apply_outlines(image: np.ndarray, object_buffer: np.ndarray) -> None:
    edges = np.zeros(object_buffer.shape, dtype=bool)

    horizontal = object_buffer[:, 1:] != object_buffer[:, :-1]
    horizontal &= (object_buffer[:, 1:] >= 0) | (object_buffer[:, :-1] >= 0)
    edges[:, 1:] |= horizontal
    edges[:, :-1] |= horizontal

    vertical = object_buffer[1:, :] != object_buffer[:-1, :]
    vertical &= (object_buffer[1:, :] >= 0) | (object_buffer[:-1, :] >= 0)
    edges[1:, :] |= vertical
    edges[:-1, :] |= vertical

    dilated = edges.copy()
    dilated[1:, :] |= edges[:-1, :]
    dilated[:-1, :] |= edges[1:, :]
    dilated[:, 1:] |= edges[:, :-1]
    dilated[:, :-1] |= edges[:, 1:]

    image[dilated] *= 0.67


def add_fog(image: np.ndarray, depth_buffer: np.ndarray) -> None:
    finite = np.isfinite(depth_buffer)
    if not np.any(finite):
        return

    near_depth = float(depth_buffer[finite].min())
    far_depth = float(depth_buffer[finite].max())
    span = max(far_depth - near_depth, 1.0)
    fog_amount = np.zeros_like(depth_buffer)
    fog_amount[finite] = np.power((depth_buffer[finite] - near_depth) / span, 1.7) * 0.10
    sky = np.array([0.86, 0.91, 0.97], dtype=np.float64)
    image[finite] = image[finite] * (1.0 - fog_amount[finite, None]) + sky * fog_amount[finite, None]


def make_ground_plane(bounds_min: np.ndarray, bounds_max: np.ndarray) -> MeshObject:
    margin = max(bounds_max[0] - bounds_min[0], bounds_max[2] - bounds_min[2]) * 0.18
    ground_y = bounds_min[1]
    positions = np.array(
        [
            [bounds_min[0] - margin, ground_y, bounds_min[2] - margin],
            [bounds_max[0] + margin, ground_y, bounds_min[2] - margin],
            [bounds_max[0] + margin, ground_y, bounds_max[2] + margin],
            [bounds_min[0] - margin, ground_y, bounds_max[2] + margin],
        ],
        dtype=np.float64,
    )
    triangles = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    return MeshObject(
        object_id=-1,
        name="Ground Plane",
        surface_type="GroundPlane",
        outside_boundary="Outdoors",
        story="",
        space_name="",
        space_type_name="",
        color=np.array([0.84, 0.85, 0.82], dtype=np.float64),
        alpha=1.0,
        positions=positions,
        triangles=triangles,
    )


def shadow_triangle(vertices: np.ndarray, ground_y: float, shadow_direction: np.ndarray) -> np.ndarray | None:
    if shadow_direction[1] >= -1e-6:
        return None

    times = (ground_y - vertices[:, 1]) / shadow_direction[1]
    projected = vertices + shadow_direction[None, :] * times[:, None]
    if np.linalg.norm(np.cross(projected[1] - projected[0], projected[2] - projected[0])) < 1e-8:
        return None
    return projected


def create_view_triangles(
    objects: list[MeshObject],
    camera: Camera,
    width: int,
    height: int,
    sun_direction: np.ndarray,
) -> tuple[list[ProjectedTriangle], list[ProjectedTriangle]]:
    opaque: list[ProjectedTriangle] = []
    transparent: list[ProjectedTriangle] = []

    for mesh_object in objects:
        for triangle in mesh_object.triangles:
            vertices = mesh_object.positions[triangle]
            projected = project_perspective(vertices, camera, width, height)
            if projected is None:
                continue
            points, depths = projected
            color, alpha = shade_triangle(mesh_object, vertices, camera, sun_direction)

            depth_slack = 0.02 if mesh_object.surface_type == "GroundPlane" else 0.40
            record = ProjectedTriangle(
                points=points,
                depths=depths,
                color=color,
                alpha=alpha,
                object_id=mesh_object.object_id,
                depth_slack=depth_slack,
                mean_depth=float(depths.mean()),
            )
            if alpha >= 0.999:
                opaque.append(record)
            else:
                transparent.append(record)

    return opaque, transparent


def render_view(
    opaque_triangles: list[ProjectedTriangle],
    transparent_triangles: list[ProjectedTriangle],
    width: int,
    height: int,
    output_path: Path,
) -> None:
    top = np.array([0.79, 0.87, 0.96], dtype=np.float64)
    bottom = np.array([0.97, 0.98, 0.99], dtype=np.float64)
    image = np.empty((height, width, 3), dtype=np.float64)
    for row in range(height):
        fraction = row / max(height - 1, 1)
        image[row, :, :] = top * (1.0 - fraction) + bottom * fraction

    depth_buffer = np.full((height, width), np.inf, dtype=np.float64)
    object_buffer = np.full((height, width), -1, dtype=np.int32)

    for triangle in opaque_triangles:
        rasterize_triangle(image, depth_buffer, object_buffer, triangle)

    for triangle in sorted(transparent_triangles, key=lambda item: item.mean_depth, reverse=True):
        rasterize_triangle(image, depth_buffer, object_buffer, triangle)

    apply_outlines(image, object_buffer)
    add_fog(image, depth_buffer)
    write_png(image, output_path, gamma_correct=True)


def render_3d_views(objects: list[MeshObject], output_dir: Path, focus_bbox: tuple[float, float, float, float]) -> None:
    exterior_objects = [
        mesh_object
        for mesh_object in objects
        if mesh_object.surface_type in THREE_D_SURFACE_TYPES
        and (
            (mesh_object.surface_type in EXTERIOR_SURFACE_TYPES and mesh_object.outside_boundary in OUTDOOR_BOUNDARIES)
            or mesh_object.surface_type == "Floor"
        )
        and boxes_overlap(bbox_xz(mesh_object), focus_bbox, 4.0)
    ]
    if not exterior_objects:
        raise RuntimeError("The model did not contain exterior geometry for 3D rendering.")

    all_points = np.concatenate([mesh_object.positions for mesh_object in exterior_objects], axis=0)
    bounds_min = all_points.min(axis=0)
    bounds_max = all_points.max(axis=0)
    center = (bounds_min + bounds_max) / 2.0
    center[1] = bounds_min[1] + (bounds_max[1] - bounds_min[1]) * 0.28

    ground_plane = make_ground_plane(bounds_min, bounds_max)
    ground_y = float(bounds_min[1])
    sun_direction = normalize(np.array([-0.45, 1.00, 0.28], dtype=np.float64))
    shadow_direction = -sun_direction

    shadow_objects: list[MeshObject] = []
    next_shadow_id = max(mesh_object.object_id for mesh_object in exterior_objects) + 1
    for mesh_object in exterior_objects:
        if mesh_object.surface_type in {"FixedWindow", "Floor"}:
            continue
        shadow_positions: list[np.ndarray] = []
        shadow_triangles: list[np.ndarray] = []
        for triangle in mesh_object.triangles:
            projected = shadow_triangle(mesh_object.positions[triangle], ground_y, shadow_direction)
            if projected is None:
                continue
            base_index = len(shadow_positions)
            shadow_positions.extend(projected)
            shadow_triangles.append(np.array([base_index, base_index + 1, base_index + 2], dtype=np.int64))
        if not shadow_triangles:
            continue
        shadow_objects.append(
            MeshObject(
                object_id=next_shadow_id,
                name=f"{mesh_object.name} Shadow",
                surface_type="Shadow",
                outside_boundary="",
                story="",
                space_name="",
                space_type_name="",
                color=np.array([0.18, 0.20, 0.24], dtype=np.float64),
                alpha=0.16,
                positions=np.array(shadow_positions, dtype=np.float64),
                triangles=np.array(shadow_triangles, dtype=np.int64),
            )
        )
        next_shadow_id += 1

    width = 1800
    height = 1200
    plan_span = math.hypot(float(bounds_max[0] - bounds_min[0]), float(bounds_max[2] - bounds_min[2]))
    height_span = float(bounds_max[1] - bounds_min[1])
    radius = max(plan_span * 1.15, height_span * 2.6)
    target = center.copy()

    view_specs = [
        ("3d_view_1.png", 30.0, 10.0),
        ("3d_view_2.png", 150.0, 10.0),
        ("3d_view_3.png", 250.0, 18.0),
    ]

    scene_objects = [ground_plane, *exterior_objects]

    for filename, yaw_deg, pitch_deg in view_specs:
        yaw = math.radians(yaw_deg)
        pitch = math.radians(pitch_deg)
        eye = np.array(
            [
                target[0] + radius * math.cos(yaw) * math.cos(pitch),
                target[1] + radius * math.sin(pitch),
                target[2] + radius * math.sin(yaw) * math.cos(pitch),
            ],
            dtype=np.float64,
        )
        camera = Camera(
            eye=eye,
            target=target,
            up=np.array([0.0, 1.0, 0.0], dtype=np.float64),
            fov_y_deg=42.0,
        )
        opaque_triangles, transparent_triangles = create_view_triangles(scene_objects, camera, width, height, sun_direction)
        _, shadow_triangles = create_view_triangles(shadow_objects, camera, width, height, sun_direction)
        render_view(opaque_triangles, shadow_triangles + transparent_triangles, width, height, output_dir / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render floorplan and 3D PNGs from an OpenStudio OSM.")
    parser.add_argument("--osm", required=True, type=Path, help="Path to the .osm model to render.")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where floorplan and 3D renders will be written.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    model = load_model(args.osm)
    floorplan_objects = load_floorplan_objects(model)
    energy_model = collect_energy_model_metadata(model)

    with tempfile.TemporaryDirectory() as temp_dir_name:
        gltf_path = Path(temp_dir_name) / "model.gltf"
        export_gltf(model, gltf_path)
        render_objects = load_mesh_objects(gltf_path)

    floorplan_metadata = render_floorplan(floorplan_objects, output_dir / "floorplan.png", args.osm.stem, energy_model)
    render_3d_views(render_objects, output_dir, floorplan_metadata.focus_bbox)

    print(f"Rendered mesh-based outputs to {output_dir}")
    print(f"Selected story for floorplan: {floorplan_metadata.selected_story}")


if __name__ == "__main__":
    main()
