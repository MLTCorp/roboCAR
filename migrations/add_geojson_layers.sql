-- Migration: Add geojson_layers field to store processed GeoJSON data
-- This allows the frontend to directly consume map layers without client-side processing

ALTER TABLE duploa_consultas_car
ADD COLUMN IF NOT EXISTS geojson_layers JSONB;

COMMENT ON COLUMN duploa_consultas_car.geojson_layers IS
'Armazena as camadas GeoJSON extraídas do shapefile, organizadas por tipo.
Estrutura: {
  "area_imovel": {...GeoJSON...},
  "cobertura_solo": {...GeoJSON...},
  "reserva_legal": {...GeoJSON...},
  "app": {...GeoJSON...},
  "uso_restrito": {...GeoJSON...},
  ...
}';

-- Create index for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_geojson_layers_gin ON duploa_consultas_car USING gin(geojson_layers);

SELECT 'Migration completed: geojson_layers field added successfully!' as status;
