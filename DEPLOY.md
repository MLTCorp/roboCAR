# Deploy do roboCAR Backend na Hetzner

## Pré-requisitos

- VPS Hetzner com Docker e Docker Compose instalados
- Portainer configurado (opcional)
- Domínio apontando para o IP da VPS
- Conta Supabase configurada

---

## 1. Configurar Supabase

### Criar tabela `duploa_consultas_car`:

```sql
CREATE TABLE duploa_consultas_car (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cliente_id UUID NOT NULL,
  numero_car TEXT NOT NULL,

  -- Dados básicos
  status_cadastro TEXT,
  tipo_imovel TEXT,
  municipio TEXT,
  area_total TEXT,

  -- Dados completos (JSON)
  dados_demonstrativo JSONB,

  -- Arquivo
  shapefile_url TEXT,
  shapefile_size INTEGER,

  -- Status da consulta
  status TEXT DEFAULT 'processando',
  erro_mensagem TEXT,
  consulta_iniciada_em TIMESTAMP DEFAULT NOW(),
  consulta_concluida_em TIMESTAMP,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_duploa_consultas_car_cliente ON duploa_consultas_car(cliente_id);
CREATE INDEX idx_duploa_consultas_car_numero ON duploa_consultas_car(numero_car);
CREATE INDEX idx_duploa_consultas_car_status ON duploa_consultas_car(status);
```

### Criar bucket de storage `car-shapefiles`:

1. Ir em **Storage** no Supabase
2. Criar novo bucket: `car-shapefiles`
3. Configurar como **público**

---

## 2. Configurar Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```bash
# Copiar exemplo
cp backend/.env.example .env

# Editar variáveis
nano .env
```

Preencher com valores reais:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ALLOWED_ORIGINS=https://seu-app.vercel.app,https://www.seu-app.com
WEBSOCKET_TIMEOUT=900
LOG_LEVEL=INFO
HEADLESS=true
SLOW_MO=100
```

---

## 3. Deploy via Portainer

### Opção A: Via Git Clone

```bash
# SSH na VPS
ssh root@seu-ip-hetzner

# Clonar repositório
cd /opt/stacks
git clone https://github.com/seu-usuario/roboCAR.git
cd roboCAR

# Copiar e configurar .env
cp backend/.env.example .env
nano .env  # Preencher valores

# Buildar e subir
docker-compose up -d --build
```

### Opção B: Via Portainer UI

1. Acessar Portainer: `https://seu-ip:9443`
2. Ir em **Stacks** → **Add stack**
3. Nome: `robocar`
4. Build method: **Git Repository**
5. Repository URL: `https://github.com/seu-usuario/roboCAR`
6. Compose path: `docker-compose.yml`
7. **Environment variables**:
   - Adicionar todas as variáveis do `.env`
8. **Deploy the stack**

---

## 4. Configurar SSL com Let's Encrypt

```bash
# Instalar Certbot
apt install certbot

# Parar nginx temporariamente
docker-compose stop nginx

# Obter certificado
certbot certonly --standalone -d api.seudominio.com

# Restart nginx
docker-compose up -d nginx
```

### Renovação automática:

```bash
# Cron job
crontab -e

# Adicionar linha:
0 3 * * * certbot renew --quiet && docker-compose restart nginx
```

---

## 5. Atualizar nginx.conf

Editar `nginx/nginx.conf` e substituir:

```nginx
server_name api.meuparceiro.com.br;  # Trocar pelo seu domínio
ssl_certificate /etc/letsencrypt/live/api.meuparceiro.com.br/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.meuparceiro.com.br/privkey.pem;
```

---

## 6. Verificar Deploy

```bash
# Ver logs
docker-compose logs -f robocar-backend

# Verificar containers
docker-compose ps

# Testar health check
curl https://api.seudominio.com/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "supabase": "ok",
    "timestamp": "2025-01-..."
  }
}
```

---

## 7. Teste de WebSocket

Usar ferramenta como [Postman](https://www.postman.com/) ou [wscat](https://github.com/websockets/wscat):

```bash
# Instalar wscat
npm install -g wscat

# Conectar
wscat -c "wss://api.seudominio.com/ws/car/MS-5007901-C252AF6443F04FC3BDCFC7AFD3357053"

# Enviar config inicial
{"cliente_id": "uuid-do-cliente"}
```

---

## 8. Monitoramento

### Ver logs em tempo real:

```bash
docker-compose logs -f robocar-backend
```

### Ver uso de recursos:

```bash
docker stats
```

### Via Portainer:

1. **Containers** → `robocar-backend`
2. **Stats** (gráficos de CPU/RAM)
3. **Logs** (logs em tempo real)

---

## 9. Atualização

```bash
# Pull do código
cd /opt/stacks/roboCAR
git pull

# Rebuild e restart
docker-compose up -d --build

# Verificar
docker-compose logs -f
```

---

## 10. Troubleshooting

### Container não inicia:

```bash
# Ver logs
docker-compose logs robocar-backend

# Ver detalhes
docker inspect robocar-backend
```

### Erro de permissão:

```bash
# Dar permissão ao diretório
chmod -R 755 /opt/stacks/roboCAR
```

### Playwright não funciona:

```bash
# Entrar no container
docker exec -it robocar-backend bash

# Reinstalar browsers
playwright install chromium
playwright install-deps
```

### Supabase connection error:

- Verificar SUPABASE_URL e SUPABASE_SERVICE_KEY no `.env`
- Verificar firewall/rede
- Verificar se service key tem permissões corretas

---

## URLs Importantes

- **API**: `https://api.seudominio.com`
- **Health Check**: `https://api.seudominio.com/health`
- **WebSocket**: `wss://api.seudominio.com/ws/car/{numero_car}`
- **Portainer**: `https://seu-ip:9443`

---

## Segurança

- ✅ SSL/TLS configurado via Let's Encrypt
- ✅ Rate limiting no Nginx (10 req/s)
- ✅ CORS configurado para domínios específicos
- ✅ WebSocket timeout (15 min)
- ✅ Limpeza automática de arquivos temporários
- ✅ Health checks configurados

---

## Próximos Passos

1. [ ] Configurar autenticação JWT (opcional)
2. [ ] Integrar com monitoring (Sentry, DataDog, etc)
3. [ ] Configurar backups automáticos
4. [ ] Escalar workers (múltiplas réplicas)
