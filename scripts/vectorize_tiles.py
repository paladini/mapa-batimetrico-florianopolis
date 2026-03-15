"""
Vetorização de tiles SonarChart em isolinhas batimétricas (GeoJSON).

Converte os tiles PNG em isolinhas vetoriais extraindo contornos entre as
bandas discretas de profundidade do SonarChart. Cada banda de azul
corresponde a uma faixa de profundidade relativa.

Saída:
    data/vectorized/isobaths_z{zoom}.geojson  — isolinhas por zoom level
    data/vectorized/coastline_z{zoom}.geojson  — contorno terra/água
    data/vectorized/metadata.json              — metadados da vetorização

Uso:
    python3 scripts/vectorize_tiles.py                  # todos os zooms
    python3 scripts/vectorize_tiles.py --zoom 12 14     # zooms específicos
    python3 scripts/vectorize_tiles.py --zoom 16 --simplify 0.00005
"""

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import LineString, mapping
from shapely.ops import linemerge, unary_union

# ==================== CONFIGURAÇÃO ====================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TILES_DIR = PROJECT_ROOT / "tiles"
OUTPUT_DIR = PROJECT_ROOT / "data" / "vectorized"

# Paleta de cores do SonarChart (R, G, B) → band index
# Band 0 = mais raso (azul claro), Band 8 = mais fundo (azul escuro)
# Ordem invertida: R alto = raso, R baixo = fundo
DEPTH_BANDS = [
    {"r": 192, "band": 0, "label": "very_shallow",  "color": "#c0e8f8"},
    {"r": 184, "band": 1, "label": "shallow",        "color": "#b8e0f8"},
    {"r": 176, "band": 2, "label": "shallow_mid",    "color": "#b0e0f8"},
    {"r": 168, "band": 3, "label": "mid_shallow",    "color": "#a8e0f8"},
    {"r": 160, "band": 4, "label": "mid",            "color": "#a0d8f8"},
    {"r": 152, "band": 5, "label": "mid_deep",       "color": "#98d8f8"},
    {"r": 136, "band": 6, "label": "deep_mid",       "color": "#88d0f8"},
    {"r": 112, "band": 7, "label": "deep",           "color": "#70c8f8"},
    {"r":  32, "band": 8, "label": "very_deep",      "color": "#20b0f8"},
]

# Cores especiais
LAND_YELLOW = (248, 232, 112)   # terra / praia
LAND_GRAY = (64, 64, 64)        # massa terrestre
NO_DATA = (248, 248, 248)       # sem dados / branco
CONTOUR_BLACK = (0, 0, 0)       # linhas de contorno existentes
MARKER_RED = (248, 48, 0)       # marcadores de profundidade

# Tolerância para matching de cores (distância euclidiana RGB)
COLOR_TOLERANCE = 20

# ==================== FUNÇÕES GEOGRÁFICAS ====================


def tile_to_lat_lon(x, y, zoom):
    """Converte coordenadas de tile (canto noroeste) em lat/lon."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def tile_bounds(x, y, zoom):
    """Retorna limites geográficos (N, S, W, E) de uma tile."""
    lat_nw, lon_nw = tile_to_lat_lon(x, y, zoom)
    lat_se, lon_se = tile_to_lat_lon(x + 1, y + 1, zoom)
    return lat_nw, lat_se, lon_nw, lon_se


def pixel_to_latlon(px, py, tile_x, tile_y, zoom, tile_size=256):
    """Converte coordenada de pixel dentro de um tile em lat/lon."""
    north, south, west, east = tile_bounds(tile_x, tile_y, zoom)
    lon = west + (px / tile_size) * (east - west)
    lat = north + (py / tile_size) * (south - north)
    return lat, lon


# ==================== CLASSIFICAÇÃO DE PIXELS ====================


def classify_pixel(r, g, b):
    """Classifica um pixel pela cor, retornando o tipo e band index."""
    # Sem dados (branco)
    if r > 240 and g > 240 and b > 240:
        return "nodata", -1

    # Terra (cinza)
    if abs(r - 64) < 15 and abs(g - 64) < 15 and abs(b - 64) < 15:
        return "land_gray", -1

    # Terra / praia (amarelo)
    if r > 220 and g > 200 and b < 150 and b > 70:
        return "land_yellow", -1

    # Contorno preto
    if r < 15 and g < 15 and b < 15:
        return "contour", -1

    # Marcador vermelho
    if r > 200 and g < 80 and b < 50:
        return "marker", -1

    # Bandas de azul (água) — encontrar a mais próxima
    if b > 180 and g > r:
        best_band = -1
        best_dist = float("inf")
        for band_info in DEPTH_BANDS:
            dist = abs(r - band_info["r"])
            if dist < best_dist:
                best_dist = dist
                best_band = band_info["band"]
        if best_dist < 40:
            return "water", best_band

    return "unknown", -1


def build_band_map(img_array):
    """Constrói mapa de bandas de profundidade para todos os pixels de uma tile.

    Retorna array (256, 256) com valores:
        -2 = terra/nodata
        -1 = contour/marker/unknown
         0..8 = banda de profundidade (0=raso, 8=fundo)
    """
    h, w = img_array.shape[:2]
    band_map = np.full((h, w), -2, dtype=np.int8)

    r = img_array[:, :, 0].astype(np.int16)
    g = img_array[:, :, 1].astype(np.int16)
    b = img_array[:, :, 2].astype(np.int16)

    # Contornos pretos
    black_mask = (r < 15) & (g < 15) & (b < 15)
    band_map[black_mask] = -1

    # Marcadores vermelhos
    red_mask = (r > 200) & (g < 80) & (b < 50)
    band_map[red_mask] = -1

    # Água (azul) — classificar por banda
    water_mask = (b > 180) & (g > r) & (~black_mask) & (~red_mask)

    # Para pixels de água, encontrar a banda mais próxima pelo canal R
    water_r = r[water_mask]
    for band_info in DEPTH_BANDS:
        band_r = band_info["r"]
        band_idx = band_info["band"]
        # Pixels cujo R é mais próximo desta banda
        distances = np.abs(water_r - band_r)
        # Marcar os que estão próximos (será refinado abaixo)
        close = distances < 40
        # Precisamos trabalhar com os pixels de água originais
        water_indices = np.where(water_mask)
        # Para cada pixel de água, verificar se esta banda é a mais próxima
        water_r_vals = r[water_mask]

    # Abordagem mais eficiente: para cada pixel de água, encontrar banda mais próxima
    band_r_values = np.array([b["r"] for b in DEPTH_BANDS])
    water_r_flat = r[water_mask]
    # Broadcast: distance de cada pixel para cada banda
    dists = np.abs(water_r_flat[:, None] - band_r_values[None, :])
    nearest = np.argmin(dists, axis=1)
    min_dists = dists[np.arange(len(nearest)), nearest]

    # Só classificar se distância < 40
    valid = min_dists < 40
    water_ys, water_xs = np.where(water_mask)
    band_map[water_ys[valid], water_xs[valid]] = nearest[valid].astype(np.int8)

    return band_map


# ==================== EXTRAÇÃO DE CONTORNOS ====================


def extract_isobaths_from_tile(img_array, tile_x, tile_y, zoom, simplify_tolerance):
    """Extrai isolinhas batimétricas de uma tile.

    Retorna lista de features GeoJSON (LineString).
    """
    band_map = build_band_map(img_array)
    features = []
    h, w = band_map.shape

    # Para cada par de bandas adjacentes, encontrar o contorno entre elas
    for band_idx in range(len(DEPTH_BANDS) - 1):
        shallow_band = band_idx
        deep_band = band_idx + 1

        # Máscara: pixels que são da banda shallow ou mais rasa
        mask = np.zeros((h, w), dtype=np.uint8)
        mask[band_map <= shallow_band] = 255
        # Incluir terra como "mais raso que tudo"
        mask[band_map == -2] = 255

        # Encontrar contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)

        for contour in contours:
            # Filtrar contornos muito pequenos (ruído)
            arc_length = cv2.arcLength(contour, closed=False)
            if arc_length < 8:
                continue

            # Converter pixels em coordenadas geográficas
            coords = []
            for point in contour:
                px, py = point[0]
                lat, lon = pixel_to_latlon(px, py, tile_x, tile_y, zoom)
                coords.append((lon, lat))

            if len(coords) < 2:
                continue

            # Criar LineString e simplificar
            try:
                line = LineString(coords)
                if simplify_tolerance > 0:
                    line = line.simplify(simplify_tolerance, preserve_topology=True)
                if line.is_empty or line.length == 0:
                    continue

                features.append({
                    "type": "Feature",
                    "properties": {
                        "band_shallow": shallow_band,
                        "band_deep": deep_band,
                        "depth_label": DEPTH_BANDS[deep_band]["label"],
                        "color": DEPTH_BANDS[deep_band]["color"],
                    },
                    "geometry": mapping(line),
                })
            except Exception:
                continue

    return features


def extract_coastline_from_tile(img_array, tile_x, tile_y, zoom, simplify_tolerance):
    """Extrai contorno terra/água de uma tile.

    Retorna lista de features GeoJSON (LineString).
    """
    band_map = build_band_map(img_array)
    features = []
    h, w = band_map.shape

    # Terra = band_map == -2 (e que não seja nodata branco)
    r = img_array[:, :, 0]
    g = img_array[:, :, 1]
    b = img_array[:, :, 2]

    # Máscara de terra (cinza + amarelo)
    land_mask = np.zeros((h, w), dtype=np.uint8)
    gray_mask = (np.abs(r.astype(int) - 64) < 15) & (np.abs(g.astype(int) - 64) < 15)
    yellow_mask = (r > 220) & (g > 200) & (b < 150) & (b > 70)
    land_mask[gray_mask | yellow_mask] = 255

    if land_mask.sum() == 0:
        return features

    contours, _ = cv2.findContours(land_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)

    for contour in contours:
        arc_length = cv2.arcLength(contour, closed=False)
        if arc_length < 15:
            continue

        coords = []
        for point in contour:
            px, py = point[0]
            lat, lon = pixel_to_latlon(px, py, tile_x, tile_y, zoom)
            coords.append((lon, lat))

        if len(coords) < 2:
            continue

        try:
            line = LineString(coords)
            if simplify_tolerance > 0:
                line = line.simplify(simplify_tolerance, preserve_topology=True)
            if line.is_empty or line.length == 0:
                continue

            features.append({
                "type": "Feature",
                "properties": {"type": "coastline"},
                "geometry": mapping(line),
            })
        except Exception:
            continue

    return features


# ==================== PROCESSAMENTO POR ZOOM ====================


def get_tiles_for_zoom(zoom):
    """Retorna lista de (tile_x, tile_y, file_path) para um zoom level."""
    zoom_dir = TILES_DIR / str(zoom)
    if not zoom_dir.exists():
        return []

    tiles = []
    for x_dir in sorted(zoom_dir.iterdir()):
        if not x_dir.is_dir() or not x_dir.name.isdigit():
            continue
        x = int(x_dir.name)
        for png_file in sorted(x_dir.iterdir()):
            if png_file.suffix != ".png":
                continue
            if png_file.stat().st_size < 100:
                continue
            y = int(png_file.stem)
            tiles.append((x, y, str(png_file)))

    return tiles


def process_zoom_level(zoom, simplify_tolerance, progress_interval=200):
    """Processa todas as tiles de um zoom level e retorna features."""
    tiles = get_tiles_for_zoom(zoom)
    if not tiles:
        print(f"  [SKIP] Nenhuma tile encontrada para zoom {zoom}")
        return [], []

    total = len(tiles)
    isobath_features = []
    coastline_features = []
    processed = 0
    skipped = 0
    start_time = time.time()

    for tile_x, tile_y, file_path in tiles:
        try:
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                skipped += 1
                continue

            # OpenCV loads as BGRA, convert to RGBA for our classification
            if img.shape[2] == 4:
                img_rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            else:
                img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                # Add alpha channel
                alpha = np.full((img_rgba.shape[0], img_rgba.shape[1], 1), 255, dtype=np.uint8)
                img_rgba = np.concatenate([img_rgba, alpha], axis=2)

            # Extrair isolinhas
            iso_feats = extract_isobaths_from_tile(
                img_rgba, tile_x, tile_y, zoom, simplify_tolerance
            )
            isobath_features.extend(iso_feats)

            # Extrair coastline
            coast_feats = extract_coastline_from_tile(
                img_rgba, tile_x, tile_y, zoom, simplify_tolerance
            )
            coastline_features.extend(coast_feats)

        except Exception as e:
            skipped += 1
            if skipped <= 5:
                print(f"  [ERR] z={zoom} x={tile_x} y={tile_y}: {e}")

        processed += 1
        if processed % progress_interval == 0 or processed == total:
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            print(
                f"  [{processed:>6}/{total}] "
                f"{processed / total * 100:5.1f}% | "
                f"isobaths={len(isobath_features)} "
                f"coast={len(coastline_features)} | "
                f"ETA: {eta:.0f}s"
            )

    elapsed = time.time() - start_time
    print(
        f"  Done zoom {zoom}: {len(isobath_features)} isobaths, "
        f"{len(coastline_features)} coastline, "
        f"{skipped} skipped, {elapsed:.1f}s"
    )

    return isobath_features, coastline_features


# ==================== SAÍDA GEOJSON ====================


def write_geojson(features, output_path, properties=None):
    """Escreve features como GeoJSON."""
    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    if properties:
        geojson["properties"] = properties

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    size = output_path.stat().st_size
    if size > 1024 * 1024:
        size_str = f"{size / 1024 / 1024:.1f} MB"
    elif size > 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size} B"

    print(f"  ✓ {output_path.name}: {len(features)} features, {size_str}")


# ==================== MAIN ====================


def main():
    parser = argparse.ArgumentParser(
        description="Vetoriza tiles SonarChart em isolinhas batimétricas (GeoJSON)"
    )
    parser.add_argument(
        "--zoom", type=int, nargs="+", default=[12, 14, 16, 18],
        help="Zoom levels a processar (default: 12 14 16 18)"
    )
    parser.add_argument(
        "--simplify", type=float, default=0.0,
        help="Tolerância Douglas-Peucker para simplificação (graus). "
             "0 = auto (baseado no zoom). Ex: 0.00005"
    )
    parser.add_argument(
        "--output", type=str, default=str(OUTPUT_DIR),
        help=f"Diretório de saída (default: {OUTPUT_DIR})"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    # Tolerância de simplificação auto por zoom
    auto_simplify = {
        12: 0.0005,
        14: 0.00015,
        16: 0.00004,
        18: 0.00001,
    }

    print("=" * 62)
    print("  SonarChart Isobath Vectorizer")
    print("=" * 62)
    print(f"  Tiles dir: {TILES_DIR}")
    print(f"  Output:    {output_dir}")
    print(f"  Zoom levels: {args.zoom}")
    print()

    all_metadata = {
        "tool": "vectorize_tiles.py",
        "description": "Isolinhas batimétricas extraídas dos tiles SonarChart",
        "source": "Navionics SonarChart (via Garmin Marine Maps)",
        "region": "Grande Florianópolis - Ilha de Santa Catarina",
        "coordinate_system": "EPSG:4326 (WGS84)",
        "depth_bands": [
            {"band": b["band"], "label": b["label"], "color": b["color"]}
            for b in DEPTH_BANDS
        ],
        "note": "Profundidades são relativas (band 0=mais raso, band 8=mais fundo), não absolutas em metros.",
        "zoom_levels": {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    total_start = time.time()

    for zoom in sorted(args.zoom):
        print(f"[Zoom {zoom}] Processando...")

        simplify = args.simplify if args.simplify > 0 else auto_simplify.get(zoom, 0.00005)
        print(f"  Simplify tolerance: {simplify}")

        # Ajustar intervalo de progresso pelo volume
        tiles = get_tiles_for_zoom(zoom)
        n_tiles = len(tiles)
        if n_tiles == 0:
            print(f"  [SKIP] Nenhuma tile")
            continue

        print(f"  Tiles: {n_tiles}")
        progress_interval = max(1, n_tiles // 20)

        isobath_features, coastline_features = process_zoom_level(
            zoom, simplify, progress_interval
        )

        # Escrever GeoJSON
        if isobath_features:
            iso_path = output_dir / f"isobaths_z{zoom}.geojson"
            write_geojson(
                isobath_features, iso_path,
                properties={
                    "zoom": zoom,
                    "type": "isobaths",
                    "simplify_tolerance": simplify,
                },
            )

        if coastline_features:
            coast_path = output_dir / f"coastline_z{zoom}.geojson"
            write_geojson(
                coastline_features, coast_path,
                properties={
                    "zoom": zoom,
                    "type": "coastline",
                    "simplify_tolerance": simplify,
                },
            )

        all_metadata["zoom_levels"][str(zoom)] = {
            "tiles_processed": n_tiles,
            "isobath_features": len(isobath_features),
            "coastline_features": len(coastline_features),
            "simplify_tolerance": simplify,
        }

        print()

    # Escrever metadados
    meta_path = output_dir / "metadata.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, ensure_ascii=False, indent=2)
    print(f"  ✓ metadata.json")

    total_elapsed = time.time() - total_start
    print()
    print(f"Concluído em {total_elapsed:.1f}s")

    # Resumo dos arquivos
    print()
    print("Arquivos gerados:")
    if output_dir.exists():
        for f in sorted(output_dir.iterdir()):
            size = f.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"  {f.name:35s} {size_str:>10s}")


if __name__ == "__main__":
    main()
