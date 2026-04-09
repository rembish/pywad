# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2026-04-09

### Fixed

- `BaseLump.seek()`: `SEEK_CUR` branch compared `_rposition + offset` against `offset` instead of `_size`, and never updated `_rposition` on the happy path — relative seeking was broken whenever `_rposition > 0`
- `BaseMapEntry.boundaries`: crashed with `IndexError`/`TypeError` when `things` or `vertices` were `None` or empty; now falls back to `(Point(0,0), Point(0,0))`
- `MapEntry.__new__`: silently returned `None` for unrecognised map name formats; now raises `ValueError`

## [0.0.1] - 2023

### Added

- WAD header parsing: magic (`IWAD`/`PWAD`), lump count, directory offset
- Directory reading: 16-byte entries (offset, size, 8-char name)
- `WadFile` context manager with lazy-loaded `directory` and `maps` properties
- Map marker detection for Doom 1 (`E#M#`) and Doom 2 (`MAP##`) formats
- `THINGS` lump parser — `Thing(x, y, direction, type, flags)` with Doom/Boom/MBF flag enum
- `VERTEXES` lump parser — `Vertex(x, y)`
- `LINEDEFS` lump parser — `LineDefinition(start_vertex, finish_vertex, flags, special_type, sector_tag, right_sidedef, left_sidedef)`
- `BaseLump` abstraction with `seek`, `tell`, `read`, `read_row`, `read_item`, `__iter__`, `__len__`, `__getitem__`
- `MapExporter` — renders map Things as ellipses onto a PIL `Image`
- `MapData` enum covering all standard map lumps: `THINGS`, `LINEDEFS`, `SIDEDEFS`, `VERTEXES`, `SEGS`, `SSECTORS`, `NODES`, `SECTORS`, `REJECT`, `BLOCKMAP`, `BEHAVIOR`
- BSD 2-Clause licence
