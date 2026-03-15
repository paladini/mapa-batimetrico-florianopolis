*🇺🇸 English | [🇧🇷 Português](README.pt-BR.md)*

# Bathymetric Map — Florianópolis (Ilha de Santa Catarina)

Vector bathymetric isobaths and coastline for the Greater Florianópolis region (Ilha de Santa Catarina, SC, Brazil). Free, open data derived from crowdsourced sonar readings, available in **GeoJSON** format.

## Quick start

Download the GeoJSON files and open them in any GIS tool — QGIS, Google Earth, Leaflet, geopandas, R, ArcGIS, etc.

```bash
git clone https://github.com/paladini/mapa-batimetrico-florianopolis.git
cd mapa-batimetrico-florianopolis
ls data/vectorized/
# isobaths_z12.geojson  isobaths_z14.geojson  coastline_z12.geojson  coastline_z14.geojson  metadata.json
```

Or download individual files directly from the [landing page](https://paladini.github.io/mapa-batimetrico-florianopolis/) or from [GitHub Releases](https://github.com/paladini/mapa-batimetrico-florianopolis/releases) (for high-res data).

## Available data

### Isobaths (bathymetric contour lines)

| File | Features | Resolution | Size | Download |
|------|----------|------------|------|----------|
| `isobaths_z12.geojson` | 4,284 | ~34 m/px (overview) | 2.2 MB | repo |
| `isobaths_z14.geojson` | 33,469 | ~8.5 m/px (medium detail) | 19 MB | repo |
| `isobaths_z16.geojson` | 145,237 | ~2.1 m/px (high detail) | 80 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |
| `isobaths_z18.geojson` | 1,272,324 | ~0.5 m/px (maximum detail) | 524 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |

### Coastline (land/water boundary)

| File | Features | Resolution | Size | Download |
|------|----------|------------|------|----------|
| `coastline_z12.geojson` | 459 | ~34 m/px (overview) | 614 KB | repo |
| `coastline_z14.geojson` | 7,053 | ~8.5 m/px (medium detail) | 7.8 MB | repo |
| `coastline_z16.geojson` | 32,459 | ~2.1 m/px (high detail) | 28 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |
| `coastline_z18.geojson` | 143,819 | ~0.5 m/px (maximum detail) | 91 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |

> **repo** = included in the repository (download with `git clone`). **Release** = download from [GitHub Releases](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) (larger files).

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

## Structure

```
├── data/vectorized/            # Bathymetric data (z12 + z14 in repo)
│   ├── isobaths_z12.geojson    # Isobaths — overview
│   ├── isobaths_z14.geojson    # Isobaths — medium detail
│   ├── coastline_z12.geojson   # Coastline — overview
│   ├── coastline_z14.geojson   # Coastline — medium detail
│   └── metadata.json           # Dataset metadata
├── index.html                  # Landing page (PT-BR)
├── index.en.html               # Landing page (EN)
├── README.md                   # English documentation
└── README.pt-BR.md             # Portuguese documentation
```

High and maximum resolution files (z16 + z18) are available as [GitHub Release assets](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0).

## License

This dataset contains derived bathymetric data from crowdsourced sonar readings. The vector isobaths and coastline are geometric transformations and do not contain original source imagery.
