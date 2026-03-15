"""
Exporta catálogo de tiles SonarChart da Grande Florianópolis em múltiplos formatos.

Varre o diretório tiles/ e gera um catálogo completo com metadados geográficos
para cada tile, exportando nos formatos:
  - CSV  (data/sonarchart_tiles.csv)
  - JSON (data/sonarchart_tiles.json + data/sonarchart_metadata.json)
  - SQLite (data/sonarchart.db)

Uso:
    python3 scripts/export_data.py
"""

import csv
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ==================== CONFIGURAÇÃO ====================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TILES_DIR = PROJECT_ROOT / "tiles"
DATA_DIR = PROJECT_ROOT / "data"

# Bounding box da região (mesmo usado no download)
BBOX = {
    "lat_min": -27.85,
    "lat_max": -27.35,
    "lon_min": -48.65,
    "lon_max": -48.35,
}

REGION_NAME = "Grande Florianópolis - Ilha de Santa Catarina"
REGION_STATE = "Santa Catarina, Brasil"
DATA_SOURCE = "Navionics SonarChart (via Garmin Marine Maps)"
COORDINATE_SYSTEM = "EPSG:4326 (WGS84)"
TILE_SYSTEM = "Slippy Map / TMS (same as OpenStreetMap)"
TILE_SIZE_PX = 256

# ==================== FUNÇÕES GEOGRÁFICAS ====================


def tile_to_lat_lon(x, y, zoom):
    """Converte coordenadas de tile (canto noroeste) em lat/lon."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def tile_bounds(x, y, zoom):
    """Retorna os limites geográficos (bounding box) de uma tile."""
    lat_nw, lon_nw = tile_to_lat_lon(x, y, zoom)
    lat_se, lon_se = tile_to_lat_lon(x + 1, y + 1, zoom)
    return {
        "north": lat_nw,
        "south": lat_se,
        "west": lon_nw,
        "east": lon_se,
    }


def tile_center(x, y, zoom):
    """Retorna o centro geográfico de uma tile."""
    bounds = tile_bounds(x, y, zoom)
    return {
        "lat": (bounds["north"] + bounds["south"]) / 2,
        "lon": (bounds["west"] + bounds["east"]) / 2,
    }


def meters_per_pixel(lat, zoom):
    """Resolução aproximada em metros por pixel para dado lat/zoom."""
    return 156543.03 * math.cos(math.radians(lat)) / (2 ** zoom)


# ==================== SCANNER DE TILES ====================


def scan_tiles(tiles_dir):
    """Varre o diretório de tiles e retorna lista de metadados."""
    tiles = []

    if not tiles_dir.exists():
        print(f"[ERRO] Diretório de tiles não encontrado: {tiles_dir}")
        sys.exit(1)

    zoom_dirs = sorted(
        [d for d in tiles_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda d: int(d.name),
    )

    if not zoom_dirs:
        print(f"[ERRO] Nenhum zoom level encontrado em: {tiles_dir}")
        sys.exit(1)

    for zoom_dir in zoom_dirs:
        z = int(zoom_dir.name)
        x_dirs = sorted(
            [d for d in zoom_dir.iterdir() if d.is_dir() and d.name.isdigit()],
            key=lambda d: int(d.name),
        )

        for x_dir in x_dirs:
            x = int(x_dir.name)
            png_files = sorted(
                [f for f in x_dir.iterdir() if f.suffix == ".png"],
                key=lambda f: int(f.stem),
            )

            for png_file in png_files:
                y = int(png_file.stem)
                file_size = png_file.stat().st_size

                # Pula tiles vazias (< 100 bytes geralmente são placeholder)
                if file_size < 100:
                    continue

                bounds = tile_bounds(x, y, z)
                center = tile_center(x, y, z)
                resolution = meters_per_pixel(center["lat"], z)

                tiles.append({
                    "zoom": z,
                    "tile_x": x,
                    "tile_y": y,
                    "center_lat": round(center["lat"], 7),
                    "center_lon": round(center["lon"], 7),
                    "bound_north": round(bounds["north"], 7),
                    "bound_south": round(bounds["south"], 7),
                    "bound_west": round(bounds["west"], 7),
                    "bound_east": round(bounds["east"], 7),
                    "meters_per_pixel": round(resolution, 3),
                    "file_size_bytes": file_size,
                    "tile_path": f"tiles/{z}/{x}/{y}.png",
                })

    return tiles


# ==================== EXPORTADORES ====================


def build_metadata(tiles):
    """Constrói objeto de metadados global do dataset."""
    zoom_stats = {}
    total_size = 0

    for t in tiles:
        z = t["zoom"]
        if z not in zoom_stats:
            zoom_stats[z] = {"count": 0, "total_bytes": 0}
        zoom_stats[z]["count"] += 1
        zoom_stats[z]["total_bytes"] += t["file_size_bytes"]
        total_size += t["file_size_bytes"]

    zoom_summary = []
    for z in sorted(zoom_stats.keys()):
        s = zoom_stats[z]
        avg_size = s["total_bytes"] / s["count"] if s["count"] > 0 else 0
        # Resolution at center of bounding box
        center_lat = (BBOX["lat_min"] + BBOX["lat_max"]) / 2
        res = meters_per_pixel(center_lat, z)
        zoom_summary.append({
            "zoom_level": z,
            "tile_count": s["count"],
            "total_size_bytes": s["total_bytes"],
            "total_size_mb": round(s["total_bytes"] / 1024 / 1024, 2),
            "avg_tile_size_bytes": round(avg_size),
            "approx_meters_per_pixel": round(res, 3),
        })

    return {
        "dataset": "SonarChart Bathymetric Tiles - Grande Florianópolis",
        "description": (
            "Catálogo de tiles batimétricos SonarChart extraídos da "
            "Navionics/Garmin para a região da Grande Florianópolis "
            "(Ilha de Santa Catarina), SC, Brasil. Dados de profundidade "
            "crowdsourced gerados a partir de sonares de embarcações."
        ),
        "region": REGION_NAME,
        "state": REGION_STATE,
        "data_source": DATA_SOURCE,
        "coordinate_system": COORDINATE_SYSTEM,
        "tile_system": TILE_SYSTEM,
        "tile_size_pixels": TILE_SIZE_PX,
        "bounding_box": BBOX,
        "total_tiles": len(tiles),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "zoom_levels": zoom_summary,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "formats": {
            "csv": "sonarchart_tiles.csv",
            "json": "sonarchart_tiles.json",
            "json_metadata": "sonarchart_metadata.json",
            "sqlite": "sonarchart.db",
        },
        "schema": {
            "zoom": "Nível de zoom (12=visão geral, 18=máximo detalhe)",
            "tile_x": "Coordenada X do tile no sistema Slippy Map",
            "tile_y": "Coordenada Y do tile no sistema Slippy Map",
            "center_lat": "Latitude do centro do tile (WGS84)",
            "center_lon": "Longitude do centro do tile (WGS84)",
            "bound_north": "Latitude norte do tile",
            "bound_south": "Latitude sul do tile",
            "bound_west": "Longitude oeste do tile",
            "bound_east": "Longitude leste do tile",
            "meters_per_pixel": "Resolução aproximada em metros por pixel",
            "file_size_bytes": "Tamanho do arquivo PNG em bytes",
            "tile_path": "Caminho relativo do arquivo tile",
        },
    }


def export_csv(tiles, output_path):
    """Exporta tiles para CSV."""
    if not tiles:
        return

    fieldnames = [
        "zoom", "tile_x", "tile_y",
        "center_lat", "center_lon",
        "bound_north", "bound_south", "bound_west", "bound_east",
        "meters_per_pixel", "file_size_bytes", "tile_path",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tiles)

    print(f"  ✓ CSV:    {output_path} ({len(tiles)} registros)")


def export_json(tiles, metadata, data_dir):
    """Exporta tiles e metadados para JSON."""
    tiles_path = data_dir / "sonarchart_tiles.json"
    metadata_path = data_dir / "sonarchart_metadata.json"

    # Tiles JSON — organizado por zoom level para facilitar consultas
    organized = {
        "metadata": metadata,
        "tiles": {},
    }
    for t in tiles:
        z = str(t["zoom"])
        if z not in organized["tiles"]:
            organized["tiles"][z] = []
        organized["tiles"][z].append(t)

    with open(tiles_path, "w", encoding="utf-8") as f:
        json.dump(organized, f, ensure_ascii=False, indent=2)

    print(f"  ✓ JSON:   {tiles_path} ({len(tiles)} registros)")

    # Metadata JSON separado (leve, sem tiles)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"  ✓ JSON:   {metadata_path} (metadados)")


def export_sqlite(tiles, metadata, output_path):
    """Exporta tiles para banco de dados SQLite."""
    # Remove DB anterior se existir
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(str(output_path))
    cur = conn.cursor()

    # Tabela de metadados
    cur.execute("""
        CREATE TABLE metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    flat_meta = {
        "dataset": metadata["dataset"],
        "description": metadata["description"],
        "region": metadata["region"],
        "state": metadata["state"],
        "data_source": metadata["data_source"],
        "coordinate_system": metadata["coordinate_system"],
        "tile_system": metadata["tile_system"],
        "tile_size_pixels": str(metadata["tile_size_pixels"]),
        "bbox_lat_min": str(BBOX["lat_min"]),
        "bbox_lat_max": str(BBOX["lat_max"]),
        "bbox_lon_min": str(BBOX["lon_min"]),
        "bbox_lon_max": str(BBOX["lon_max"]),
        "total_tiles": str(metadata["total_tiles"]),
        "total_size_mb": str(metadata["total_size_mb"]),
        "exported_at": metadata["exported_at"],
    }
    cur.executemany(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        flat_meta.items(),
    )

    # Tabela de zoom levels
    cur.execute("""
        CREATE TABLE zoom_levels (
            zoom_level              INTEGER PRIMARY KEY,
            tile_count              INTEGER NOT NULL,
            total_size_bytes        INTEGER NOT NULL,
            total_size_mb           REAL    NOT NULL,
            avg_tile_size_bytes     INTEGER NOT NULL,
            approx_meters_per_pixel REAL    NOT NULL
        )
    """)

    for zs in metadata["zoom_levels"]:
        cur.execute(
            "INSERT INTO zoom_levels VALUES (?, ?, ?, ?, ?, ?)",
            (
                zs["zoom_level"],
                zs["tile_count"],
                zs["total_size_bytes"],
                zs["total_size_mb"],
                zs["avg_tile_size_bytes"],
                zs["approx_meters_per_pixel"],
            ),
        )

    # Tabela principal de tiles
    cur.execute("""
        CREATE TABLE tiles (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            zoom             INTEGER NOT NULL,
            tile_x           INTEGER NOT NULL,
            tile_y           INTEGER NOT NULL,
            center_lat       REAL    NOT NULL,
            center_lon       REAL    NOT NULL,
            bound_north      REAL    NOT NULL,
            bound_south      REAL    NOT NULL,
            bound_west       REAL    NOT NULL,
            bound_east       REAL    NOT NULL,
            meters_per_pixel REAL    NOT NULL,
            file_size_bytes  INTEGER NOT NULL,
            tile_path        TEXT    NOT NULL,
            UNIQUE(zoom, tile_x, tile_y)
        )
    """)

    cur.executemany(
        """INSERT INTO tiles (
            zoom, tile_x, tile_y,
            center_lat, center_lon,
            bound_north, bound_south, bound_west, bound_east,
            meters_per_pixel, file_size_bytes, tile_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                t["zoom"], t["tile_x"], t["tile_y"],
                t["center_lat"], t["center_lon"],
                t["bound_north"], t["bound_south"],
                t["bound_west"], t["bound_east"],
                t["meters_per_pixel"], t["file_size_bytes"],
                t["tile_path"],
            )
            for t in tiles
        ],
    )

    # Índices para consultas espaciais e por zoom
    cur.execute("CREATE INDEX idx_tiles_zoom ON tiles(zoom)")
    cur.execute("CREATE INDEX idx_tiles_coords ON tiles(zoom, tile_x, tile_y)")
    cur.execute("CREATE INDEX idx_tiles_center ON tiles(center_lat, center_lon)")
    cur.execute("CREATE INDEX idx_tiles_bounds ON tiles(bound_south, bound_north, bound_west, bound_east)")

    # View útil: resumo por zoom
    cur.execute("""
        CREATE VIEW tiles_summary AS
        SELECT
            zoom,
            COUNT(*)                         AS tile_count,
            SUM(file_size_bytes)             AS total_bytes,
            ROUND(SUM(file_size_bytes) / 1024.0 / 1024.0, 2) AS total_mb,
            ROUND(AVG(file_size_bytes))      AS avg_tile_bytes,
            MIN(center_lat)                  AS min_lat,
            MAX(center_lat)                  AS max_lat,
            MIN(center_lon)                  AS min_lon,
            MAX(center_lon)                  AS max_lon,
            ROUND(MIN(meters_per_pixel), 2)  AS resolution_m
        FROM tiles
        GROUP BY zoom
        ORDER BY zoom
    """)

    # View útil: tiles próximas a um ponto (exemplo com centro de Floripa)
    cur.execute("""
        CREATE VIEW example_nearby_tiles AS
        SELECT
            zoom, tile_x, tile_y,
            center_lat, center_lon,
            meters_per_pixel,
            file_size_bytes,
            tile_path
        FROM tiles
        WHERE zoom = 16
          AND center_lat BETWEEN -27.65 AND -27.55
          AND center_lon BETWEEN -48.55 AND -48.45
        ORDER BY center_lat DESC, center_lon ASC
    """)

    conn.commit()
    conn.close()

    db_size = output_path.stat().st_size
    print(f"  ✓ SQLite: {output_path} ({len(tiles)} registros, {db_size / 1024 / 1024:.1f} MB)")


# ==================== MAIN ====================


def main():
    print("=" * 62)
    print("  SonarChart Data Exporter - Grande Florianópolis")
    print("=" * 62)
    print(f"  Tiles dir: {TILES_DIR}")
    print(f"  Output:    {DATA_DIR}")
    print()

    # 1. Scan tiles
    print("[1/4] Varrendo diretório de tiles...")
    tiles = scan_tiles(TILES_DIR)
    print(f"      Encontradas {len(tiles)} tiles válidas")

    if not tiles:
        print("[ERRO] Nenhuma tile encontrada. Execute o download primeiro:")
        print("       python3 scripts/download_tiles.py")
        sys.exit(1)

    # Resumo por zoom
    zoom_counts = {}
    for t in tiles:
        z = t["zoom"]
        zoom_counts[z] = zoom_counts.get(z, 0) + 1
    for z in sorted(zoom_counts):
        print(f"      Zoom {z:2d}: {zoom_counts[z]:>6} tiles")
    print()

    # 2. Build metadata
    print("[2/4] Construindo metadados...")
    metadata = build_metadata(tiles)
    print(f"      Dataset: {metadata['total_tiles']} tiles, "
          f"{metadata['total_size_mb']} MB")
    print()

    # 3. Create output directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 4. Export
    print("[3/4] Exportando dados...")
    export_csv(tiles, DATA_DIR / "sonarchart_tiles.csv")
    export_json(tiles, metadata, DATA_DIR)
    export_sqlite(tiles, metadata, DATA_DIR / "sonarchart.db")
    print()

    # 5. Summary
    print("[4/4] Resumo dos arquivos gerados:")
    for f in sorted(DATA_DIR.iterdir()):
        size = f.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"
        print(f"      {f.name:30s} {size_str:>10s}")

    print()
    print("  Pronto! Os dados podem ser encontrados em:")
    print(f"    {DATA_DIR}/")
    print()
    print("  Exemplos de uso:")
    print()
    print("    # CSV — abrir no Excel / Google Sheets / pandas:")
    print("    import pandas as pd")
    print("    df = pd.read_csv('data/sonarchart_tiles.csv')")
    print("    df[df.zoom == 16].head()")
    print()
    print("    # JSON — usar em qualquer linguagem:")
    print("    import json")
    print("    with open('data/sonarchart_tiles.json') as f:")
    print("        data = json.load(f)")
    print("    print(data['metadata']['total_tiles'])")
    print()
    print("    # SQLite — consultas SQL diretas:")
    print("    sqlite3 data/sonarchart.db \\")
    print("      \"SELECT * FROM tiles WHERE zoom=16 LIMIT 5;\"")
    print()
    print("    # SQLite — tiles próximas a uma coordenada:")
    print("    sqlite3 data/sonarchart.db \\")
    print("      \"SELECT * FROM tiles")
    print("       WHERE zoom=16")
    print("         AND center_lat BETWEEN -27.60 AND -27.58")
    print("         AND center_lon BETWEEN -48.50 AND -48.48;\"")
    print()


if __name__ == "__main__":
    main()
