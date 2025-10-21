# TODO - Configuração roboCAR Backend

## Status Atual

✅ **Concluído:**
- [x] Estrutura do backend criada (FastAPI + WebSocket)
- [x] Docker + docker-compose configurados
- [x] Nginx configurado
- [x] Integração Supabase (código)
- [x] Arquivo .env criado com credenciais
- [x] Bucket `car-shapefiles` criado no Supabase
- [x] Documentação (README.md, DEPLOY.md, SUPABASE_SETUP.md)
- [x] Script de teste (test_supabase.py)

❌ **Pendente:**
- [ ] Criar tabela `consultas_car` no Supabase
- [ ] Testar conexão completa (rodar test_supabase.py)
- [ ] Fazer commit das configurações do Supabase
- [ ] Fazer push para GitHub
- [ ] Criar código do frontend (React hooks + componentes)
- [ ] Deploy na Hetzner via Portainer

---

## Tarefas Detalhadas

### 1. ⚠️ CRIAR TABELA `consultas_car` NO SUPABASE

**Usando MCP do Supabase (RECOMENDADO):**

```python
# Via Python com Supabase client
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Executar SQL
sql = """
CREATE TABLE IF NOT EXISTS consultas_car (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cliente_id UUID NOT NULL,
  numero_car TEXT NOT NULL,
  status_cadastro TEXT,
  tipo_imovel TEXT,
  municipio TEXT,
  area_total TEXT,
  data_atualizacao DATE,
  dados_demonstrativo JSONB,
  shapefile_url TEXT,
  shapefile_size INTEGER,
  status TEXT DEFAULT 'processando',
  erro_mensagem TEXT,
  consulta_iniciada_em TIMESTAMP DEFAULT NOW(),
  consulta_concluida_em TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consultas_car_cliente ON consultas_car(cliente_id);
CREATE INDEX IF NOT EXISTS idx_consultas_car_numero ON consultas_car(numero_car);
CREATE INDEX IF NOT EXISTS idx_consultas_car_status ON consultas_car(status);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_consultas_car_updated_at
BEFORE UPDATE ON consultas_car
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

# Executar via API REST (alternativa)
# Nota: Pode precisar usar supabase.postgrest.rpc() ou executar via SQL Editor
```

**Ou via SQL Editor manual:**
- URL: https://supabase.com/dashboard/project/fdjqphpsbpoumjsvaqit/sql
- Colar SQL do arquivo `supabase-setup.sql`
- Clicar em "Run"

---

### 2. ✅ VERIFICAR CONFIGURAÇÃO

**Rodar teste:**
```bash
python test_supabase.py
```

**Resultado esperado:**
```
[OK] Cliente Supabase criado com sucesso!
[OK] Tabela existe! Registros encontrados: 0
[OK] Insert realizado com sucesso!
[OK] Update realizado com sucesso!
[OK] Select realizado com sucesso!
[OK] Delete realizado com sucesso!
[OK] Bucket 'car-shapefiles' existe!
```

---

### 3. 📦 COMMIT E PUSH

```bash
# Stage arquivos novos
git add .env supabase-setup.sql SUPABASE_SETUP.md test_supabase.py TODO.md

# Commit
git commit -m "feat: configuração Supabase completa

- Credenciais configuradas em .env
- Script SQL para criar tabela consultas_car
- Bucket car-shapefiles criado
- Script de teste de conexão
- Documentação completa
"

# Push
git push origin master
```

---

### 4. 🎨 CRIAR FRONTEND (React/Next.js)

**Arquivos a criar:**

#### `hooks/useCarDownload.ts`
```typescript
import { useState, useRef, useCallback } from 'react';

export interface CarProgress {
  etapa: string;
  mensagem: string;
}

export function useCarDownload() {
  const [status, setStatus] = useState<'idle' | 'processing' | 'waiting_captcha' | 'completed' | 'error'>('idle');
  const [progress, setProgress] = useState<CarProgress | null>(null);
  const [captchaImage, setCaptchaImage] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const downloadCAR = useCallback((numeroCAR: string, clienteId: string) => {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/ws/car/${numeroCAR}`);

    ws.onopen = () => {
      ws.send(JSON.stringify({ cliente_id: clienteId }));
      setStatus('processing');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'progress') {
        setProgress({ etapa: data.etapa, mensagem: data.mensagem });
      } else if (data.type === 'captcha_required') {
        setCaptchaImage(data.image);
        setStatus('waiting_captcha');
      } else if (data.type === 'completed') {
        setResult(data);
        setStatus('completed');
      } else if (data.type === 'error') {
        setStatus('error');
      }
    };

    wsRef.current = ws;
  }, []);

  const resolveCaptcha = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ captcha_text: text }));
      setCaptchaImage(null);
      setStatus('processing');
    }
  }, []);

  return { downloadCAR, resolveCaptcha, status, progress, captchaImage, result };
}
```

#### `components/CaptchaModal.tsx`
```typescript
interface CaptchaModalProps {
  imageBase64: string | null;
  onResolve: (text: string) => void;
  onCancel: () => void;
}

export function CaptchaModal({ imageBase64, onResolve, onCancel }: CaptchaModalProps) {
  const [text, setText] = useState('');

  if (!imageBase64) return null;

  return (
    <div className="modal">
      <h2>Resolver CAPTCHA</h2>
      <img src={`data:image/png;base64,${imageBase64}`} alt="CAPTCHA" />
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Digite o texto"
      />
      <button onClick={() => onResolve(text)}>Confirmar</button>
      <button onClick={onCancel}>Cancelar</button>
    </div>
  );
}
```

#### `.env.local` (Frontend)
```env
NEXT_PUBLIC_WS_URL=wss://api.seudominio.com
# ou para desenvolvimento:
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

### 5. 🚀 DEPLOY NA HETZNER

**Via Portainer:**

1. Acessar Portainer: `https://seu-ip:9443`
2. **Stacks** → **Add stack**
3. Nome: `robocar`
4. **Git Repository**:
   - Repository URL: `https://github.com/seu-usuario/roboCAR`
   - Branch: `master`
   - Compose path: `docker-compose.yml`
5. **Environment variables**:
   ```
   SUPABASE_URL=https://fdjqphpsbpoumjsvaqit.supabase.co
   SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ALLOWED_ORIGINS=https://seu-app.vercel.app
   WEBSOCKET_TIMEOUT=900
   LOG_LEVEL=INFO
   HEADLESS=true
   SLOW_MO=100
   ```
6. **Deploy the stack**

**Configurar SSL:**
```bash
ssh root@seu-ip

# Instalar Certbot
apt install certbot

# Parar nginx
docker-compose stop nginx

# Obter certificado
certbot certonly --standalone -d api.seudominio.com

# Restart nginx
docker-compose up -d nginx

# Renovação automática (cron)
crontab -e
# Adicionar: 0 3 * * * certbot renew --quiet && docker-compose restart nginx
```

**Verificar:**
```bash
curl https://api.seudominio.com/health
```

---

### 6. 🧪 TESTAR INTEGRAÇÃO COMPLETA

**Backend:**
```bash
# Teste local
docker-compose up --build

# Teste de WebSocket (wscat)
npm install -g wscat
wscat -c "ws://localhost:8000/ws/car/MS-5007901-C252AF6443F04FC3BDCFC7AFD3357053"
> {"cliente_id": "00000000-0000-0000-0000-000000000000"}
```

**Frontend + Backend:**
1. Rodar backend localmente
2. Rodar frontend localmente
3. Testar fluxo completo:
   - Digitar número CAR
   - Aguardar processamento
   - Resolver CAPTCHA no modal
   - Verificar conclusão
   - Baixar shapefile

---

## Credenciais do Projeto

**Supabase:**
- URL: `https://fdjqphpsbpoumjsvaqit.supabase.co`
- Project ID: `fdjqphpsbpoumjsvaqit`
- Service Key: (ver `.env`)
- Bucket: `car-shapefiles` (público)

**GitHub:**
- Repositório: `roboCAR`
- Branch: `master`

**Hetzner:**
- VPS: (a configurar)
- Portainer: (já instalado)
- Environment: `primary` (com n8n)

---

## Arquivos Importantes

```
roboCAR/
├── .env                    # Credenciais (NÃO commitado)
├── backend/
│   ├── app/
│   │   ├── main.py        # API WebSocket
│   │   ├── config.py      # Configurações
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── nginx/nginx.conf
├── supabase-setup.sql     # SQL para criar tabela
├── test_supabase.py       # Teste de conexão
├── DEPLOY.md             # Guia de deploy
├── SUPABASE_SETUP.md     # Guia Supabase
└── TODO.md               # Este arquivo
```

---

## Próximas Sessões

### Ao retornar ao Claude:

1. **Usar MCP do Supabase** para criar a tabela automaticamente
2. **Rodar `test_supabase.py`** para verificar
3. **Criar código do frontend** completo
4. **Fazer commit** de tudo
5. **Auxiliar no deploy** na Hetzner

---

## Comandos Úteis

```bash
# Testar Supabase
python test_supabase.py

# Rodar backend local
docker-compose up --build

# Ver logs
docker-compose logs -f robocar-backend

# Parar tudo
docker-compose down

# Git
git status
git add .
git commit -m "mensagem"
git push origin master
```

---

## Notas Importantes

- ⚠️ Arquivo `.env` **NÃO** deve ser commitado
- ✅ Bucket `car-shapefiles` já está criado
- ⚠️ Tabela `consultas_car` ainda precisa ser criada
- ✅ Código do backend está completo e testável
- ⚠️ Frontend ainda não foi criado

---

**Última atualização:** 2025-10-21
**Status:** Aguardando criação da tabela no Supabase
