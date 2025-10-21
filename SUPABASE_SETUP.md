# Configuração do Supabase para roboCAR

## 1. Criar Tabela `consultas_car`

### Via SQL Editor:

1. Acessar: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/sql
2. Copiar e colar o conteúdo do arquivo `supabase-setup.sql`
3. Clicar em **Run**

### Via CLI (Alternativa):

```bash
# Instalar Supabase CLI
npm install -g supabase

# Login
supabase login

# Link ao projeto
supabase link --project-ref fdjqphpsbpoumjsvaqit

# Executar SQL
supabase db execute -f supabase-setup.sql
```

---

## 2. Criar Storage Bucket `car-shapefiles`

### Via UI (Recomendado):

1. Acessar: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/storage/buckets
2. Clicar em **New bucket**
3. Configurar:
   - **Name**: `car-shapefiles`
   - **Public bucket**: ✅ Marcar (para gerar URLs públicas)
   - **File size limit**: 50 MB (ou conforme necessário)
   - **Allowed MIME types**: `application/zip` (opcional)
4. Clicar em **Create bucket**

### Verificar Bucket Criado:

```bash
# Listar buckets
curl https://fdjqphpsbpoumjsvaqit.supabase.co/storage/v1/bucket \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 3. Configurar Políticas de Storage (Opcional)

Se quiser controle de acesso mais fino:

```sql
-- Permitir upload apenas via service_role
CREATE POLICY "Service role can upload"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'car-shapefiles' AND auth.role() = 'service_role');

-- Permitir leitura pública
CREATE POLICY "Public can read"
ON storage.objects FOR SELECT
USING (bucket_id = 'car-shapefiles');
```

---

## 4. Testar Conexão

### Via Python:

```python
from supabase import create_client

SUPABASE_URL = "https://fdjqphpsbpoumjsvaqit.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Testar insert
result = supabase.table("consultas_car").insert({
    "cliente_id": "00000000-0000-0000-0000-000000000000",
    "numero_car": "TESTE-123",
    "status": "processando"
}).execute()

print("Teste de insert:", result)

# Testar select
result = supabase.table("consultas_car").select("*").limit(1).execute()
print("Teste de select:", result)
```

### Via cURL:

```bash
# Testar insert
curl -X POST https://fdjqphpsbpoumjsvaqit.supabase.co/rest/v1/consultas_car \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": "00000000-0000-0000-0000-000000000000",
    "numero_car": "TESTE-123",
    "status": "processando"
  }'

# Testar select
curl https://fdjqphpsbpoumjsvaqit.supabase.co/rest/v1/consultas_car?limit=1 \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 5. Verificar Setup Completo

Checklist:

- [ ] Tabela `consultas_car` criada
- [ ] Índices criados
- [ ] Trigger `updated_at` funcionando
- [ ] Bucket `car-shapefiles` criado
- [ ] Bucket configurado como público
- [ ] Teste de insert/select funcionando
- [ ] Arquivo `.env` configurado

---

## 6. URLs Importantes

- **Dashboard**: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit
- **SQL Editor**: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/sql
- **Storage**: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/storage/buckets
- **API Docs**: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/api
- **Table Editor**: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/editor

---

## Troubleshooting

### Erro: "permission denied for table consultas_car"

- Verificar se está usando o `service_role` key, não o `anon` key
- Verificar RLS (Row Level Security)

### Storage upload falha:

- Verificar se o bucket existe
- Verificar se é público
- Verificar políticas de acesso

### Tabela não aparece:

- Aguardar alguns segundos e refresh
- Verificar schema (deve ser `public`)
- Verificar no SQL Editor se foi criada
