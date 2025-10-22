# Feature: Processamento Automático de Shapefiles para GeoJSON

## Visão Geral

O roboCAR agora processa automaticamente os arquivos Shapefile (.shp) baixados do CAR e os converte para GeoJSON, permitindo consumo direto no frontend com Leaflet.js sem necessidade de processamento adicional.

## Como Funciona

### 1. Download do CAR
Quando um CAR é consultado, o backend:
1. Baixa o arquivo ZIP do site do CAR
2. Extrai todas as subpastas dentro do ZIP (área do imóvel, cobertura do solo, reserva legal, APP, uso restrito, etc.)
3. Identifica todos os arquivos `.shp` em cada subpasta
4. Converte cada Shapefile para GeoJSON
5. Salva no banco de dados (campo `geojson_layers`)

### 2. Estrutura dos Dados no Banco

Tabela: `duploa_consultas_car`

Campo: `geojson_layers` (JSONB)

Estrutura:
```json
{
  "area_imovel": {
    "type": "FeatureCollection",
    "features": [...],
    "metadata": {
      "total_features": 1,
      "bounds": [-47.123, -15.456, -47.100, -15.430],
      "crs": "EPSG:4326"
    }
  },
  "cobertura_solo": {
    "type": "FeatureCollection",
    "features": [...],
    "metadata": {...}
  },
  "reserva_legal": {...},
  "app": {...},
  "uso_restrito": {...}
}
```

### 3. Consumo no Frontend

#### Exemplo com Leaflet.js

```javascript
// 1. Buscar dados do CAR
const response = await fetch(`/api/consultas/${consultaId}`);
const consulta = await response.json();

// 2. Criar mapa
const map = L.map('map').setView([-15.789, -47.891], 13);

// 3. Adicionar tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

// 4. Adicionar camadas GeoJSON
const geojsonLayers = consulta.geojson_layers;

// Área do Imóvel (verde)
if (geojsonLayers.area_imovel) {
  L.geoJSON(geojsonLayers.area_imovel, {
    style: { color: '#00ff00', weight: 2, fillOpacity: 0.3 }
  }).addTo(map);
}

// Reserva Legal (amarelo)
if (geojsonLayers.reserva_legal) {
  L.geoJSON(geojsonLayers.reserva_legal, {
    style: { color: '#ffff00', weight: 2, fillOpacity: 0.3 }
  }).addTo(map);
}

// APP - Área de Preservação Permanente (azul)
if (geojsonLayers.app) {
  L.geoJSON(geojsonLayers.app, {
    style: { color: '#0000ff', weight: 2, fillOpacity: 0.3 }
  }).addTo(map);
}

// Ajustar zoom para mostrar todas as camadas
const allLayers = Object.values(geojsonLayers);
if (allLayers.length > 0) {
  const group = L.featureGroup(
    allLayers.map(layer => L.geoJSON(layer))
  );
  map.fitBounds(group.getBounds());
}
```

#### Exemplo com React + Leaflet

```jsx
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';

function CarMap({ geojsonLayers }) {
  const layerStyles = {
    area_imovel: { color: '#00ff00', weight: 2, fillOpacity: 0.3 },
    reserva_legal: { color: '#ffff00', weight: 2, fillOpacity: 0.3 },
    app: { color: '#0000ff', weight: 2, fillOpacity: 0.3 },
    cobertura_solo: { color: '#ff8800', weight: 2, fillOpacity: 0.3 },
    uso_restrito: { color: '#ff0000', weight: 2, fillOpacity: 0.3 }
  };

  return (
    <MapContainer center={[-15.789, -47.891]} zoom={13}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />

      {Object.entries(geojsonLayers).map(([layerName, geojson]) => (
        <GeoJSON
          key={layerName}
          data={geojson}
          style={layerStyles[layerName]}
          onEachFeature={(feature, layer) => {
            layer.bindPopup(`<b>${layerName}</b>`);
          }}
        />
      ))}
    </MapContainer>
  );
}
```

## Dependências Adicionadas

```
geopandas==0.14.2
pyshp==2.3.1
```

### Instalação

```bash
cd backend
pip install -r requirements.txt
```

## Migração do Banco de Dados

A migração já foi aplicada, mas se precisar reaplicar:

```sql
-- migrations/add_geojson_layers.sql
ALTER TABLE duploa_consultas_car
ADD COLUMN IF NOT EXISTS geojson_layers JSONB;

CREATE INDEX IF NOT EXISTS idx_geojson_layers_gin
ON duploa_consultas_car USING gin(geojson_layers);
```

## Arquitetura

```
CAR Download
    ↓
Salvar ZIP
    ↓
shapefile_processor.py
    ↓ (extrai cada subpasta)
    ↓ (encontra .shp)
    ↓ (converte para GeoJSON)
    ↓
Salvar no Supabase (campo geojson_layers)
    ↓
Frontend consome diretamente
```

## Logs e Debug

O processamento gera logs detalhados:

```
[INFO] Iniciando processamento do shapefile: /tmp/car_123.zip
[INFO] Diretório temporário criado: /tmp/car_shapefile_xyz
[INFO] ZIP principal extraído com 5 arquivos
[INFO] Encontrado sub-ZIP: AREA_IMOVEL.zip
[INFO] Sub-ZIP extraído: AREA_IMOVEL.zip
[INFO] Shapefile encontrado: AREA_IMOVEL.shp
[INFO] Processando camada: area_imovel
[INFO] Camada area_imovel convertida com sucesso
[INFO] Processamento concluído: 3 camadas extraídas
[INFO] ✓ 3 camadas GeoJSON extraídas: ['area_imovel', 'reserva_legal', 'app']
```

## Possíveis Camadas

As seguintes camadas podem estar presentes (dependendo do CAR):

- `area_imovel` - Área total do imóvel
- `cobertura_solo` - Cobertura do solo
- `reserva_legal` - Reserva Legal
- `app` - Área de Preservação Permanente
- `uso_restrito` - Área de Uso Restrito
- `area_consolidada` - Área Rural Consolidada
- `vegetacao_nativa` - Remanescente de Vegetação Nativa

## Performance

- Processamento médio: 2-5 segundos por CAR
- Tamanho médio do GeoJSON: 50-200 KB por camada
- O campo é indexado com GIN para queries eficientes

## Vantagens

✅ **Frontend leve**: Não precisa processar Shapefiles no browser
✅ **Performance**: Dados prontos para consumo direto
✅ **Compatibilidade**: Formato padrão GeoJSON funciona com qualquer biblioteca de mapas
✅ **Flexibilidade**: Frontend pode escolher quais camadas exibir
✅ **Metadados**: Cada camada inclui bounds e CRS para facilitar zoom/posicionamento

## Troubleshooting

### Erro: "geopandas not found"
```bash
pip install geopandas==0.14.2
```

### Erro: "GDAL not installed"
No Windows, pode ser necessário instalar GDAL separadamente:
```bash
pip install GDAL-3.4.3-cp312-cp312-win_amd64.whl
```

### Camadas vazias ou faltando
Verifique os logs do backend para ver se os shapefiles foram encontrados corretamente. Alguns CARs podem não ter todas as camadas.
