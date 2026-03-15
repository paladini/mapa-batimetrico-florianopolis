*🇺🇸 English | [🇧🇷 Português](README.pt-BR.md)*

# Bathymetric Map — Florianópolis (Ilha de Santa Catarina)

Vector bathymetric isobaths and coastline for the Greater Florianópolis region (Ilha de Santa Catarina, SC, Brazil). Free, open data derived from crowdsourced sonar readings, available in **GeoJSON** format.

## Quick start

Download the GeoJSON files from `data/vectorized/` and open them in any GIS tool — QGIS, Google Earth, Leaflet, geopandas, R, ArcGIS, etc.

```bash
git clone https://github.com/paladini/mapa-batimetrico-florianopolis.git
cd mapa-batimetrico-florianopolis
ls data/vectorized/
# isobaths_z12.geojson  isobaths_z14.geojson  coastline_z12.geojson  coastline_z14.geojson  metadata.json
```

Or browse the interactive viewer:

```bash
python3 serve.py
# Open http://localhost:8080/viewer.html
```

## Available data

### Isobaths (bathymetric contour lines)

| File | Features | Resolution | Size |
|------|----------|------------|------|
| `isobaths_z12.geojson` | 4,284 | ~34 m/px (overview) | 2.2 MB |
| `isobaths_z14.geojson` | 33,469 | ~8.5 m/px (medium detail) | 19 MB |

### Coastline (land/water boundary)

| File | Features | Resolution | Size |
|------|----------|------------|------|
| `coastline_z12.geojson` | 459 | ~34 m/px (overview) | 614 KB |
| `coastline_z14.geojson` | 7,053 | ~8.5 m/px (medium detail) | 7.8 MB |

Higher resolutions (up to ~0.5 m/px) can be generated locally — see [Generating higher resolutions](#generating-higher-resolutions).

## Depth bands

Each isobath line separates two adjacent depth bands. There are **9 relative depth bands** (band 0 = shallowest, band 8 = deepest).

Each GeoJSON feature has these properties:
- `band_shallow` — shallower side band index (0–7)
- `band_deep` — deeper side band index (1–8)
- `depth_label` — human-readable label (e.g., `shallow`, `deep`, `very_deep`)
- `color` — hex color for visualization

> **Note**: Depths are relative, not absolute meters. The bands indicate where depth transitions occur, not exact depth values.

## Coverage

```
Ilha de Santa Catarina (Florianópolis, SC, Brazil)
  North:  -27.35° (Ponta das Canas)
  South:  -27.85° (Naufragados)
  East:   -48.35° (oceanic coast)
  West:   -48.65° (inner Baía Sul)
  CRS:    EPSG:4326 (WGS84)
```

## Usage examples

### Python (geopandas)

```python
import geopandas as gpd

gdf = gpd.read_file('data/vectorized/isobaths_z14.geojson')

# Filter deeper isobaths
deep = gdf[gdf.band_deep >= 6]
deep.plot(column='band_deep', cmap='Blues')
```

### JavaScript (Leaflet)

```javascript
fetch('data/vectorized/isobaths_z12.geojson')
  .then(r => r.json())
  .then(data => {
    L.geoJSON(data, {
      style: f => ({ color: f.properties.color, weight: 1 })
    }).addTo(map);
  });
```

### QGIS

Open → Layer → Add Layer → Add Vector Layer → select any `.geojson` file.

### R

```r
library(sf)
isobaths <- st_read("data/vectorized/isobaths_z14.geojson")
plot(isobaths["band_deep"])
```

## Generating higher resolutions

The included data covers zoom levels 12 and 14. For higher detail (zoom 16 at ~2.1 m/px, zoom 18 at ~0.5 m/px), you can generate locally:

```bash
pip install -r requirements.txt
python3 scripts/vectorize_tiles.py --zoom 16 18
```

This requires the source tile images (not included in this repository).

| Level | Isobaths | Coastline | Resolution |
|-------|----------|-----------|------------|
| Overview (z12) | 4,284 | 459 | ~34 m/px |
| Medium (z14) | 33,469 | 7,053 | ~8.5 m/px |
| High (z16)* | 145,237 | 32,459 | ~2.1 m/px |
| Maximum (z18)* | 1,272,324 | 143,819 | ~0.5 m/px |

*Generate locally with `vectorize_tiles.py`

## Structure

```
├── data/vectorized/            # Bathymetric data (included in repo)
│   ├── isobaths_z12.geojson    # Isobaths — overview
│   ├── isobaths_z14.geojson    # Isobaths — medium detail
│   ├── coastline_z12.geojson   # Coastline — overview
│   ├── coastline_z14.geojson   # Coastline — medium detail
│   └── metadata.json           # Vectorization metadata
├── scripts/
│   ├── vectorize_tiles.py      # Generate isobaths from tile images
│   └── export_data.py          # Export tile catalog (CSV/JSON/SQLite)
├── viewer.html                 # Interactive map viewer (Leaflet.js)
├── serve.py                    # Local HTTP server
├── index.html                  # Landing page (PT-BR)
├── index.en.html               # Landing page (EN)
├── README.md                   # English documentation
└── README.pt-BR.md             # Portuguese documentation
```

## License

This dataset contains derived bathymetric data from crowdsourced sonar readings. The vector isobaths and coastline are geometric transformations and do not contain original source imagery.
