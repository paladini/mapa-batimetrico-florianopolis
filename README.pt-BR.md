*[🇺🇸 English](README.md) | 🇧🇷 Português*

# Mapa Batimétrico — Florianópolis (Ilha de Santa Catarina)

Isolinhas batimétricas vetoriais e linha de costa da região da Grande Florianópolis (Ilha de Santa Catarina, SC, Brasil). Dados abertos e gratuitos derivados de leituras de sonar crowdsourced, disponíveis em formato **GeoJSON**.

## Início rápido

Baixe os arquivos GeoJSON e abra em qualquer ferramenta GIS — QGIS, Google Earth, Leaflet, geopandas, R, ArcGIS, etc.

```bash
git clone https://github.com/paladini/mapa-batimetrico-florianopolis.git
cd mapa-batimetrico-florianopolis
ls data/vectorized/
# isobaths_z12.geojson  isobaths_z14.geojson  coastline_z12.geojson  coastline_z14.geojson  metadata.json
```

Ou baixe arquivos individuais diretamente pela [landing page](https://paladini.github.io/mapa-batimetrico-florianopolis/) ou via [GitHub Releases](https://github.com/paladini/mapa-batimetrico-florianopolis/releases) (para dados de alta resolução).

Para navegar pelos dados interativamente no browser:

```bash
python3 serve.py
# Abra http://localhost:8080/viewer.html
```

## Dados disponíveis

### Isolinhas batimétricas (curvas de profundidade)

| Arquivo | Features | Resolução | Tamanho | Download |
|---------|----------|-----------|---------|----------|
| `isobaths_z12.geojson` | 4.284 | ~34 m/px (visão geral) | 2,2 MB | repo |
| `isobaths_z14.geojson` | 33.469 | ~8,5 m/px (detalhe médio) | 19 MB | repo |
| `isobaths_z16.geojson` | 145.237 | ~2,1 m/px (alto detalhe) | 80 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |
| `isobaths_z18.geojson` | 1.272.324 | ~0,5 m/px (máximo detalhe) | 524 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |

### Linha de costa (contorno terra/água)

| Arquivo | Features | Resolução | Tamanho | Download |
|---------|----------|-----------|---------|----------|
| `coastline_z12.geojson` | 459 | ~34 m/px (visão geral) | 614 KB | repo |
| `coastline_z14.geojson` | 7.053 | ~8,5 m/px (detalhe médio) | 7,8 MB | repo |
| `coastline_z16.geojson` | 32.459 | ~2,1 m/px (alto detalhe) | 28 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |
| `coastline_z18.geojson` | 143.819 | ~0,5 m/px (máximo detalhe) | 91 MB | [Release](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) |

> **repo** = incluído no repositório (baixar com `git clone`). **Release** = baixar via [GitHub Releases](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0) (arquivos maiores).

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

## Site

O projeto tem uma landing page bilíngue que explica o dataset, mostra todos os downloads disponíveis, bandas de profundidade, cobertura, compatibilidade com ferramentas GIS e exemplos de código:

**[paladini.github.io/mapa-batimetrico-florianopolis](https://paladini.github.io/mapa-batimetrico-florianopolis/)**

## Download de dados em alta resolução (z16 + z18)

Os arquivos de visão geral e detalhe médio (z12 + z14) estão incluídos diretamente no repositório. Para **alto detalhe** (~2,1 m/px) e **máximo detalhe** (~0,5 m/px), baixe pela Release do GitHub:

**[Baixar z16 + z18 da Release v1.0.0](https://github.com/paladini/mapa-batimetrico-florianopolis/releases/tag/v1.0.0)**

Assets da Release:
- `isobaths_z16.geojson` (145.237 features, 80 MB)
- `isobaths_z18.geojson` (1.272.324 features, 524 MB)
- `coastline_z16.geojson` (32.459 features, 28 MB)
- `coastline_z18.geojson` (143.819 features, 91 MB)

## Estrutura

```
├── data/vectorized/            # Dados batimétricos (z12 + z14 no repo)
│   ├── isobaths_z12.geojson    # Isolinhas — visão geral
│   ├── isobaths_z14.geojson    # Isolinhas — detalhe médio
│   ├── coastline_z12.geojson   # Linha de costa — visão geral
│   ├── coastline_z14.geojson   # Linha de costa — detalhe médio
│   └── metadata.json           # Metadados do dataset
├── viewer.html                 # Visualizador interativo (Leaflet.js)
├── serve.py                    # Servidor HTTP local
├── index.html                  # Landing page (PT-BR)
├── index.en.html               # Landing page (EN)
├── README.md                   # Documentação em inglês
└── README.pt-BR.md             # Documentação em português
```

## Licença

Este dataset contém dados batimétricos derivados de leituras de sonar crowdsourced. As isolinhas vetoriais e linha de costa são transformações geométricas e não contêm imagens da fonte original.
