# Plano de execução — suporte a múltiplos usuários

## Objetivo

Transformar o Streaming Manager em uma aplicação multiusuário, com watchlists públicas por usuário, edição restrita ao proprietário autenticado e aprovação manual de novos cadastros pelo administrador.

## 1. Evoluir o banco de dados sem perder a watchlist atual

- Criar a entidade `User` com:
  - `username` único;
  - hash de senha;
  - papel (`admin` ou `user`);
  - status (`pending`, `active`, `inactive` ou `rejected`);
  - datas relevantes de criação e aprovação.
- Associar cada `Content` a um `owner_id`.
- Criar a conta administrativa inicial a partir das credenciais atuais configuradas por ambiente e vincular a ela todos os conteúdos já existentes. Isso mantém a watchlist atual pública em `/`.
- Adotar migrações versionadas para o SQLite. O uso atual de `create_all()` não atualiza tabelas existentes com segurança.
- Fazer backup do banco antes da migração.
- Após a primeira migração, todo login passa a consultar usuários e hashes de senha armazenados no banco. As credenciais de ambiente deixam de ser o mecanismo de autenticação normal.

## 2. Implementar autenticação e regras de acesso

- Cadastro com `username` imutável, de 3 a 30 caracteres, limitado a letras minúsculas, números e hífen.
- Reservar slugs de sistema, como `admin`, `login`, `register` e `api`.
- Exigir senha com no mínimo 8 caracteres.
- Criar novos cadastros com status `pending`; a tentativa de login deve informar que a aprovação está pendente.
- Contas `inactive` e `rejected` não podem entrar.
- Alterar o JWT para identificar o usuário por ID e papel, validando também o status atual da conta.
- Usuários ativos podem criar, editar, desativar e excluir exclusivamente conteúdos de sua própria watchlist.
- O administrador gerencia usuários e plataformas globais, mas apenas visualiza watchlists de terceiros; não edita seus conteúdos.

## 3. Adaptar catálogo e API para múltiplas watchlists

| Recurso | Regra |
| --- | --- |
| `/` | Watchlist principal do administrador, pública |
| `/{username}` | Watchlist pública de um usuário ativo |
| `/{username-do-admin}` | Redireciona para `/` |
| Plataformas | Globais e administradas somente pelo admin |
| Conteúdos | Independentes por usuário |
| Sugestões | Itens ativos de qualquer conta ativa |

- Criar endpoints para carregar catálogo por username, administrar o conteúdo do usuário autenticado e buscar sugestões de conteúdo.
- A busca de sugestões usará título e poderá considerar tipo e ano.
- Ao selecionar uma sugestão, preencher título, ano, tipo, gênero, pôster e streamings; o usuário ainda poderá editar os dados antes de salvar.
- Salvar sempre uma cópia independente. Uma alteração ou exclusão no catálogo de origem nunca afeta a cópia.
- Não sugerir conteúdos inativos, nem conteúdos de contas pendentes, rejeitadas ou inativas.
- Manter a lista de streamings compartilhada e sob gerenciamento exclusivo do administrador.

## 4. Criar as telas do frontend

- Introduzir roteamento React para `/`, `/:username`, `/admin`, cadastro e `Minha conta`.
- Transformar o modal de login administrativo atual em login comum.
- Na página inicial, incluir acessos claros para entrar, criar conta e acessar a própria watchlist.
- Exibir ações de edição apenas quando o usuário autenticado for dono do catálogo visualizado.
- Criar formulário de cadastro e mensagens específicas para conta pendente, rejeitada ou desativada.
- No modal de adicionar conteúdo, incluir sugestões enquanto a pessoa digita, sem mostrar de qual catálogo veio a sugestão.
- Criar a tela `Minha conta`, permitindo que o usuário altere a própria senha.

## 5. Criar painel administrativo privado

- Criar lista de usuários com busca por username.
- Disponibilizar filtros por status: pendente, ativo, inativo e rejeitado.
- Incluir ações para aprovar, rejeitar, ativar, desativar, excluir definitivamente e redefinir senha.
- Exibir links diretos para visualizar a watchlist pública de cada usuário.
- Permitir ao administrador definir uma nova senha para qualquer conta, sem necessidade de conhecer a senha atual.
- Permitir ao administrador alterar a própria senha pelo mesmo fluxo administrativo.
- Ao desativar uma conta, preservar seus dados, mas tornar sua URL pública indisponível.
- Ao excluir uma conta, remover definitivamente a conta e todos os seus conteúdos após confirmação explícita.

## 6. Segurança, testes e implantação

- Armazenar senhas com hash seguro e validar todos os dados também no backend.
- Aplicar autorização de proprietário em todas as rotas que modificam conteúdo.
- Remover credenciais padrão inseguras como meio permanente de acesso.
- Restringir CORS ao domínio real da produção.
- Testar a migração dos conteúdos atuais, o cadastro pendente, a aprovação, os bloqueios de status, permissões entre usuários, cópias independentes de conteúdo, redirecionamento da URL administrativa, redefinição de senha e exclusão em cascata.
- Executar lint e build do frontend, além de testes da API.
- Atualizar a documentação de implantação com variáveis de ambiente, backup, execução da migração e geração/cópia do build do frontend para o Flask.

## Fora do escopo desta entrega

- E-mail e notificações por e-mail.
- Recuperação automática de senha.
- Alteração de username.
- Status `assistido` e regras associadas.

O modelo será mantido preparado para receber futuramente o status `assistido` sem precisar refazer a arquitetura multiusuário.
