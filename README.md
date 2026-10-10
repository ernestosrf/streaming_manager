# Streaming Manager

Uma aplicação full-stack para **gerenciamento de conteúdo de streaming** com Flask (backend) e React (frontend), agora com **watchlists públicas por usuário**.

## O que é o Streaming Manager?

O Streaming Manager cataloga filmes, séries e animes disponíveis em diferentes plataformas. Cada pessoa aprovada tem a própria watchlist pública. A lista principal do administrador continua em `/`.

### Funcionalidades

- Watchlist pública do administrador em `/`
- Watchlist pública de cada usuário ativo em `/{username}`
- Cadastro com aprovação manual do administrador
- Edição apenas pelo dono da lista
- Sugestões de conteúdo a partir de outras watchlists ativas (cópia independente)
- Painel administrativo para contas, senhas e plataformas globais

## Desenvolvimento local

### Backend (Flask)

```bash
cd streaming_manager
pip install -r requirements.txt
```

Configure `streaming_manager/.env` a partir de `.env.example`. **Antes da primeira migração**, preencha `ADMIN_USERNAME` e `ADMIN_PASSWORD` (mínimo 8 caracteres). Esses valores criam a conta administrativa e vinculam a watchlist atual a ela. Sem isso, a migração é interrompida de propósito e o banco original é preservado.

```bash
python migrate.py          # backup do SQLite (se existir) + migrações
python src/init_data.py    # apenas se ainda não houver plataformas
python src/main.py
```

### Frontend (React)

```bash
cd streaming-frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`. A API roda em `http://localhost:5000`.

### Backend + frontend estático

```bash
cd streaming-frontend
npm run build
# PowerShell
Copy-Item "dist\*" "..\streaming_manager\src\static\" -Recurse -Force
cd ..\streaming_manager
python src/main.py
```

Acesse `http://localhost:5000`.

## Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `FLASK_SECRET_KEY` | Chave da sessão Flask |
| `JWT_SECRET_KEY` | Assinatura dos tokens JWT |
| `ADMIN_USERNAME` | Username do administrador **inicial** (somente a primeira migração) |
| `ADMIN_PASSWORD` | Senha do administrador **inicial** (mínimo 8 caracteres; somente a primeira migração) |
| `CORS_ORIGINS` | Origens permitidas, separadas por vírgula. Em produção, use o domínio real |
| `DATABASE_URL` | Postgres em produção. Vazio = SQLite em `src/database/app.db` |

Depois da primeira migração, o login consulta usuários e hashes no banco. As credenciais de ambiente deixam de ser o mecanismo normal de autenticação.

Não use senhas padrão inseguras. Defina chaves e a senha inicial no ambiente de produção.

## Backup e migração

1. **SQLite local:** `python migrate.py` copia `src/database/app.db` para `src/database/backups/` e aplica as migrações.
2. **Postgres:** faça `pg_dump` antes e execute `python migrate.py` (o backup automático de arquivo é ignorado).
3. A migração cria a tabela `users`, adiciona `owner_id` aos conteúdos, cria o admin a partir de `ADMIN_USERNAME`/`ADMIN_PASSWORD` e vincula os títulos existentes a essa conta.

Alternativa com Flask CLI, a partir de `streaming_manager`:

```bash
# PowerShell
$env:FLASK_APP = "src.main:app"
flask db upgrade
```

## Testes, lint e build

```bash
cd streaming_manager
pytest
```

```bash
cd streaming-frontend
npm run lint
npm run build
```

Após o build, copie `streaming-frontend/dist/*` para `streaming_manager/src/static/` se o Flask for servir o frontend.

## Rotas principais

| Rota | Descrição |
| --- | --- |
| `/` | Watchlist pública do administrador |
| `/{username}` | Watchlist pública de um usuário ativo |
| `/{username-do-admin}` | Redireciona para `/` |
| `/login` | Login |
| `/register` | Cadastro (conta fica pendente) |
| `/account` | Alterar a própria senha |
| `/admin` | Painel privado do administrador |

## Estrutura

```
streammanager/
├── streaming_manager/          # Backend Flask
│   ├── migrate.py
│   ├── migrations/
│   ├── tests/
│   └── src/
└── streaming-frontend/         # Frontend React
```
