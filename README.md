# roboCAR - Automação de Consulta CAR

Sistema automatizado para consulta de dados do Cadastro Ambiental Rural (CAR) com API WebSocket e integração Supabase.

## 🏗️ Arquitetura

```
Frontend (Vercel)  ←→  Backend API (Hetzner Docker)  ←→  Supabase
    React/Next.js         FastAPI + WebSocket             Database + Storage
```

### Componentes:

1. **Backend API** (Este repositório)
   - FastAPI + WebSocket
   - Playwright para automação
   - Integração Supabase
   - Docker ready

2. **Frontend** (Separado)
   - React/Next.js na Vercel
   - Modal para resolução de CAPTCHA
   - WebSocket client

3. **Supabase**
   - Tabela `consultas_car`
   - Storage para shapefiles

---

## 📁 Estrutura do Projeto

```
roboCAR/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI + WebSocket
│   │   ├── car_downloader.py    # Lógica de automação
│   │   ├── config.py            # Configurações
│   │   ├── models.py            # Modelos Pydantic
│   │   └── supabase_client.py   # Cliente Supabase
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── nginx/
│   └── nginx.conf               # Proxy reverso + SSL
├── docker-compose.yml
├── DEPLOY.md                    # Instruções de deploy
└── README.md                    # Este arquivo
```

---

## 🚀 Quick Start (Local)

### 1. Clonar repositório

```bash
git clone https://github.com/seu-usuario/roboCAR.git
cd roboCAR
```

### 2. Configurar variáveis de ambiente

```bash
cp backend/.env.example backend/.env
nano backend/.env  # Preencher com credenciais reais
```

### 3. Rodar com Docker

```bash
docker-compose up --build
```

### 4. Testar

```bash
# Health check
curl http://localhost:8000/health

# WebSocket (usar Postman ou wscat)
wscat -c "ws://localhost:8000/ws/car/MS-5007901-..."
```

---

## 📡 API Endpoints

### WebSocket: `/ws/car/{numero_car}`

**Conectar:**
```javascript
const ws = new WebSocket('wss://api.seudominio.com/ws/car/MS-5007901-...');

ws.onopen = () => {
  // Enviar config inicial
  ws.send(JSON.stringify({
    cliente_id: "uuid-do-cliente"
  }));
};
```

**Mensagens:**

1. **Progresso**
```json
{
  "type": "progress",
  "etapa": "busca",
  "mensagem": "Acessando site do CAR..."
}
```

2. **CAPTCHA necessário**
```json
{
  "type": "captcha_required",
  "image": "data:image/png;base64,iVBORw0KG..."
}
```

**Cliente responde:**
```json
{
  "captcha_text": "ABC123"
}
```

3. **Conclusão**
```json
{
  "type": "completed",
  "consulta_id": "uuid",
  "numero_car": "MS-...",
  "shapefile_url": "https://...",
  "dados_extraidos": { ... }
}
```

4. **Erro**
```json
{
  "type": "error",
  "message": "Descrição do erro"
}
```

### REST: `/health`

```bash
GET /health
```

Resposta:
```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "supabase": "ok"
  }
}
```

---

## 📊 Dados Extraídos

### Estrutura JSON completa (26 campos):

- **Situação do Cadastro**
- **Dados do Imóvel Rural**
  - Área, módulos fiscais, município
  - Coordenadas geográficas (lat/long)
  - Datas de inscrição e retificação
- **Cobertura do Solo**
  - Vegetação nativa, área consolidada, servidão
- **Reserva Legal**
  - Informação documental e georreferenciada
- **APP (Áreas de Preservação Permanente)**
  - Total, área consolidada, área com vegetação
- **Uso Restrito**
- **Regularidade Ambiental**
  - Passivo/excedente, áreas a recompor
- **Shapefile** (arquivo ZIP)

---

## 🐳 Deploy em Produção

Ver documentação completa: **[DEPLOY.md](./DEPLOY.md)**

### Resumo:

1. Configure Supabase (tabela + storage)
2. Configure variáveis de ambiente
3. Deploy via Portainer ou docker-compose
4. Configure SSL com Let's Encrypt
5. Teste WebSocket

---

## 🔒 Segurança

- ✅ SSL/TLS (Let's Encrypt)
- ✅ CORS configurado
- ✅ Rate limiting (10 req/s)
- ✅ WebSocket timeout (15 min)
- ✅ Limpeza automática de arquivos temporários
- ✅ Health checks

---

## 🛠️ Tecnologias

- **Backend**: Python 3.11, FastAPI, Playwright
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage
- **Proxy**: Nginx
- **Container**: Docker

---

## 📝 Versões

- **v1.0.0**: Script standalone funcional
- **v2.0.0**: API WebSocket + Supabase + Docker ← **ATUAL**

---

## 📖 Documentação Adicional

- [Instruções de Deploy](./DEPLOY.md)
- [Arquitetura Completa](./docs/arquitetura.md) (em breve)

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é privado e proprietário.

---

## 👨‍💻 Autor

Desenvolvido para **Meu Parceiro Agro**
