# Stream Manager

Uma aplicação full-stack para **gerenciamento de conteúdo de streaming** com Flask (backend) e React (frontend).

## 🎯 **O que é o Stream Manager?**

O Stream Manager é uma ferramenta completa para **catalogar, organizar e gerenciar** seu conteúdo de entretenimento disponível em diferentes plataformas de streaming.

### 🌟 **Principais Funcionalidades**

#### **📚 Catálogo de Conteúdo**
- **Filmes, Séries e Animes**: Cadastre e organize todo seu conteúdo
- **Informações Detalhadas**: Título, ano, gênero, poster e mais
- **Busca Inteligente**: Encontre rapidamente o que procura

#### **🎭 Plataformas de Streaming**
- **Netflix, Amazon Prime, Disney+, HBO Max** e outras
- **Disponibilidade**: Saiba onde cada conteúdo está disponível
- **Gerenciamento**: Adicione novas plataformas conforme necessário

#### **📊 Dashboard e Estatísticas**
- **Visão Geral**: Total de filmes, séries e animes
- **Por Plataforma**: Quantos títulos cada streaming possui
- **Filtros Avançados**: Por tipo, gênero e plataforma

#### **🔐 Sistema de Administração**
- **Acesso Público**: Qualquer um pode **visualizar** o catálogo
- **Operações Admin**: Apenas administradores podem **criar/editar/excluir**
- **Login Seguro**: Autenticação via JWT com modal integrado

## 🛠️ Desenvolvimento Local

### Backend (Flask)
```bash
cd streaming_manager
pip install -r requirements.txt
python src/init_data.py  # apenas na primeira execução para popular o DB com as plataformas de streaming
python src/main.py
```

### Frontend (React)
```bash
cd streaming-frontend
npm install
npm run dev
```

### 🔄 **Importante: Sincronização Frontend-Backend**

Existem **duas formas** de acessar a aplicação:

#### **Opção 1: Desenvolvimento Completo (Recomendado)**
1. **Rode o backend**: `cd streaming_manager && python src/main.py` 
2. **Rode o frontend**: `cd streaming-frontend && npm run dev`
3. **Acesse**: `http://localhost:5173` (Vite - com autenticação)
4. **API**: `http://localhost:5000` (Flask)

#### **Opção 2: Backend + Frontend Estático**
1. **Faça build do frontend**: `cd streaming-frontend && npm run build`
2. **Copie para static**: `Copy-Item "dist\*" "..\streaming_manager\src\static\" -Recurse -Force`
3. **Rode apenas o backend**: `cd streaming_manager && python src/main.py`
4. **Acesse**: `http://localhost:5000` (Flask servindo tudo)

## 📁 Estrutura do Projeto

```
streammanager/
├── streaming_manager/          # Backend Flask
│   ├── src/
│   │   ├── main.py            # Aplicação principal
│   │   ├── models/            # Modelos do banco
│   │   └── routes/            # Rotas da API
│   └── requirements.txt
├── streaming-frontend/         # Frontend React
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── vercel.json                # Configuração Vercel
```

### Banco de Dados
- **Desenvolvimento**: SQLite (local)
- **Produção**: PostgreSQL

## 🤝 **Contribuindo**

1. **Fork** o projeto
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request