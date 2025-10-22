-- ============================================
-- Setup do Supabase para roboCAR
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

-- 1. Criar tabela duploa_consultas_car
CREATE TABLE IF NOT EXISTS duploa_consultas_car (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cliente_id UUID NOT NULL,
  numero_car TEXT NOT NULL,

  -- Dados básicos extraídos
  status_cadastro TEXT,
  tipo_imovel TEXT,
  municipio TEXT,
  area_total TEXT,
  data_atualizacao DATE,

  -- Dados completos do demonstrativo (JSON estruturado)
  dados_demonstrativo JSONB,

  -- Arquivo shapefile
  shapefile_url TEXT,
  shapefile_size INTEGER, -- Tamanho em bytes

  -- Status da consulta
  status TEXT DEFAULT 'processando' CHECK (status IN ('processando', 'concluido', 'erro')),
  erro_mensagem TEXT,
  consulta_iniciada_em TIMESTAMP DEFAULT NOW(),
  consulta_concluida_em TIMESTAMP,

  -- Metadados
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_duploa_consultas_car_cliente ON duploa_consultas_car(cliente_id);
CREATE INDEX IF NOT EXISTS idx_duploa_consultas_car_numero ON duploa_consultas_car(numero_car);
CREATE INDEX IF NOT EXISTS idx_duploa_consultas_car_status ON duploa_consultas_car(status);
CREATE INDEX IF NOT EXISTS idx_duploa_consultas_car_created_at ON duploa_consultas_car(created_at DESC);

-- 3. Criar trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_duploa_consultas_car_updated_at BEFORE UPDATE ON duploa_consultas_car
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Habilitar RLS (Row Level Security) - opcional
-- ALTER TABLE duploa_consultas_car ENABLE ROW LEVEL SECURITY;

-- 5. Política de acesso (exemplo - ajustar conforme necessário)
-- CREATE POLICY "Usuários podem ver suas próprias consultas"
-- ON duploa_consultas_car FOR SELECT
-- USING (auth.uid() = cliente_id);

-- CREATE POLICY "Service role pode fazer tudo"
-- ON duploa_consultas_car FOR ALL
-- USING (auth.role() = 'service_role');

-- ============================================
-- Verificação
-- ============================================
-- Verificar se a tabela foi criada
SELECT 'Tabela duploa_consultas_car criada com sucesso!' as status;

-- Ver estrutura da tabela
\d duploa_consultas_car;

-- ============================================
-- STORAGE BUCKET
-- ============================================
-- IMPORTANTE: O bucket de storage precisa ser criado via UI do Supabase
--
-- Passos:
-- 1. Ir em Storage no menu lateral
-- 2. Clicar em "New bucket"
-- 3. Nome: car-shapefiles
-- 4. Marcar como "Public bucket"
-- 5. Criar
-- ============================================
