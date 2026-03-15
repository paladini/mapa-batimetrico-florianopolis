*[🇺🇸 English](README.md) | 🇧🇷 Português*

# Mapa Batimétrico — Florianópolis (Ilha de Santa Catarina)

Isolinhas batimétricas vetoriais e linha de costa da região da Grande Florianópolis (Ilha de Santa Catarina, SC, Brasil). Dados abertos e gratuitos derivados de leituras de sonar crowdsourced, disponíveis em formato **GeoJSON**.

## Início rápido

Baixe os arquivos GeoJSON de `data/vectorized/` e abra em qualquer ferramenta GIS — QGIS, Google Earth, Leaflet, geopandas, R, ArcGIS, etc.

```bash
git clone https://github.com/paladini/mapa-batimetrico-florianopolis.git
cd mapa-batimetrico-florianopolis
ls data/vectorized/
# isobaths_z12.geojson  isobaths_z14.geojson  coastline_z12.geojson  coastline_z14.geojson  metadata.json
```

Ou navegue pelo visualizador interativo:

```bash
python3 serve.py
# Abra http://localhost:8080/viewer.html
```

## Dados disponíveis

### Isolinhas batimétricas (curvas de profundidade)

| Arquivo | Features | Resolução | Tamanho |
|---------|----------|-----------|---------|
| `isobaths_z12.geojson` | 4.284 | ~34 m/px (visão geral) | 2,2 MB |
| `isobaths_z14.geojson` | 33.469 | ~8,5 m/px (detalhe médio) | 19 MB |

### Linha de costa (contorno terra/água)

| Arquivo | Features | Resolução | Tamanho |
|---------|----------|-----------|---------|
| `coastline_z12.geojson` | 459 | ~34 m/px (visão geral) | 614 KB |
| `coastline_z14.geojson` | 7.053 | ~8,5 m/px (detalhe médio) | 7,8 MB |

Resoluções mais altas (até ~0,5 m/px) podem ser geradas localmente — veja [Gerando resoluções maiores](#gerando-resoluções-maiores).

## Bandas de profundidade

Cada isolinha separa duas bandas de profundidade adjacentes. São **9 bandas de profundidade relativa** (band 0 = mais raso, band 8 = mais fundo).

Cada feature GeoJSON tem estas propriedades:
- `band_shallow` — índice da banda mais rasa (0–7)
- `band_deep` — índice da banda mais funda (1–8)
- `depth_label` — rótulo legível (ex: `shallow`, `deep`, `very_deep`)
- `color` — cor hex para visualização

> **Nota**: As profundidades são relativas, não absolutas em metros. As bandas indicam onde ocorrem transições de profundidade, não valores exatos.

## Cobertura

```
Ilha de Santa Catarina (Florianópolis, SC, Brasil)
  Norte:  -27.35° (Ponta das Canas)
  Sul:    -27.85° (Naufragados)
  Leste:  -48.35° (costa oceânica)
  Oeste:  -48.65° (Baía Sul interior)
  CRS:    EPSG:4326 (WGS84)
```

## Exemplos de uso

### Python (geopandas)

```python
import geopandas as gpd

gdf = gpd.read_file('data/vectorized/isobaths_z14.geojson')

# Filtrar isolinhas mais fundas
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

Abrir → Camada → Adicionar Camada → Adicionar Camada Vetorial → selecionar qualquer arquivo `.geojson`.

### R

```r
library(sf)
isobaths <- st_read("data/vectorized/isobaths_z14.geojson")
plot(isobaths["band_deep"])
```

## Gerando resoluções maiores

Os dados incluídos cobrem zoom levels 12 e 14. Para maior detalhe (zoom 16 com ~2,1 m/px, zoom 18 com ~0,5 m/px), é possível gerar localmente:

```bash
pip install -r requirements.txt
python3 scripts/vectorize_tiles.py --zoom 16 18
```

Isso requer as imagens de tiles fonte (não incluídas neste repositório).

| Nível | Isolinhas | Costa | Resolução |
|-------|-----------|-------|-----------|
| Visão geral (z12) | 4.284 | 459 | ~34 m/px |
| Detalhe médio (z14) | 33.469 | 7.053 | ~8,5 m/px |
| Alto detalhe (z16)* | 145.237 | 32.459 | ~2,1 m/px |
| Máximo detalhe (z18)* | 1.272.324 | 143.819 | ~0,5 m/px |

*Gerar localmente com `vectorize_tiles.py`

## Estrutura

```
├── data/vectorized/            # Dados batimétricos (incluídos no repo)
│   ├── isobaths_z12.geojson    # Isolinhas — visão geral
│   ├── isobaths_z14.geojson    # Isolinhas — detalhe médio
│   ├── coastline_z12.geojson   # Linha de costa — visão geral
│   ├── coastline_z14.geojson   # Linha de costa — detalhe médio
│   └── metadata.json           # Metadados da vetorização
├── scripts/
│   ├── vectorize_tiles.py      # Gerar isolinhas a partir de tiles
│   └── export_data.py          # Exportar catálogo de tiles (CSV/JSON/SQLite)
├── viewer.html                 # Visualizador interativo (Leaflet.js)
├── serve.py                    # Servidor HTTP local
├── index.html                  # Landing page (PT-BR)
├── index.en.html               # Landing page (EN)
├── README.md                   # Documentação em inglês
└── README.pt-BR.md             # Documentação em português
```

## Licença

Este dataset contém dados batimétricos derivados de leituras de sonar crowdsourced. As isolinhas vetoriais e linha de costa são transformações geométricas e não contêm imagens da fonte original.
