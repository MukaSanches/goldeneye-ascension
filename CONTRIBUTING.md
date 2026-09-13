# Contributing to Ascension

Obrigado por contribuir. Ascension é um port de preservação com uma camada própria de experiência para PC; isso exige cuidado com compatibilidade, proveniência e regressões.

Antes de começar, abra uma issue quando a mudança for grande, alterar comportamento do jogo, introduzir uma dependência ou afetar formato de dados. Correções pequenas e claramente locais podem ir direto para Pull Request.

## Princípios de engenharia

1. **Preserve a referência original.** Comportamento clássico é o baseline. Mudanças modernas precisam ter motivação clara e, quando fizer sentido, ser opcionais.
2. **Prefira a camada `port/`.** Código específico de PC deve permanecer fora da lógica reconstruída sempre que possível. Alterações em `src/` ou `include/` precisam ser pequenas, justificadas e documentadas.
3. **Não misture objetivos.** Uma correção de input não deve carregar junto refatoração de renderização, tradução e limpeza de estilo.
4. **Sem dependências gratuitas.** Nova biblioteca precisa resolver um problema concreto, ter licença compatível e ser justificável para todas as plataformas afetadas.
5. **Proveniência importa.** Não copie código, assets ou traduções externas sem verificar origem, licença e necessidade de atribuição.
6. **ROM e assets comerciais nunca entram no repositório.** Não anexe em issues, PRs, logs ou artefatos de CI.

## Antes de editar

```sh
git switch main
git pull --ff-only
git switch -c tipo/descricao-curta
```

Use nomes de branch simples, por exemplo:

- `fix/input-deadzone`
- `feat/ptbr-menu`
- `docs/build-windows`
- `refactor/video-init`

## Estilo

- Respeite `.clang-format` e `.editorconfig`.
- Mantenha o estilo do arquivo ao redor; não reformate código não relacionado.
- Comentários devem explicar restrições, decisões ou comportamento não óbvio.
- Evite comentários que apenas repetem o código.
- Commits devem explicar o motivo da mudança, não apenas listar arquivos.

## Validação mínima

Para mudança que afeta build ou runtime:

```sh
./build-pc.sh ntsc-final
git diff --check
```

Depois, execute o jogo e reproduza exatamente a área tocada pela mudança. Renderização, HUD, áudio, input e localização exigem verificação humana além da compilação.

Quando aplicável, registre também:

- sistema operacional e ambiente;
- região/ROMID usada no build;
- nível ou fluxo testado;
- configuração relevante;
- resultado esperado e observado;
- screenshots para mudanças visuais;
- limitações conhecidas.

## Mudanças em `src/` e `include/`

A camada de jogo reconstruída é parte sensível do projeto. Antes de alterá-la, confirme que o problema não pode ser resolvido em `port/`.

Uma alteração nesse núcleo deve ser:

- mínima;
- semanticamente clara;
- isolada de refatorações cosméticas;
- protegida por `#ifdef PORT` quando a mudança existir apenas para o port;
- acompanhada por nota em `docs/porting-notes.md` ou `docs/dev/` quando introduzir um novo padrão técnico.

## Região e build

Se `CMakeLists.txt` mudar macros de região, confirme que elas continuam coerentes com o build N64 correspondente. Não altere `Makefile`, `tools/`, `rsp/` ou `ld/` para resolver um problema exclusivamente de PC sem uma justificativa explícita.

## Pull Requests

Um PR bom responde cinco perguntas:

1. Qual problema existe?
2. Por que esta solução foi escolhida?
3. Quais arquivos e subsistemas foram afetados?
4. Como a mudança foi validada?
5. O que ainda pode dar errado?

Use o template do repositório. PRs grandes podem ser divididos em etapas menores quando isso reduzir risco e facilitar revisão.

## Commits

Prefira mensagens curtas e específicas:

```text
fix(input): clamp mouse sensitivity range
feat(locale): add pt-BR title menu entries
docs(build): clarify MSYS2 package setup
refactor(video): isolate fullscreen transition
```

Evite commits como `update`, `changes`, `fix stuff` ou grandes despejos sem contexto.

## Onde procurar contexto

- `docs/internals.md` — arquitetura do port.
- `docs/porting-notes.md` — padrões de problemas já conhecidos.
- `docs/dev/` — investigações e registros técnicos.
- `docs/PROVENANCE.md` — política de proveniência.
- `ROADMAP_ASCENSION.md` — direção do projeto.
- `docs/PROJECT_STATUS.md` — maturidade atual por área.

## Revisão

Revisão não mede apenas se o código compila. Ela também verifica escopo, regressões, clareza, manutenção futura, licença e aderência à direção Ascension.

Ao receber feedback, prefira novos commits pequenos durante a revisão. O histórico final pode ser reorganizado no merge quando isso melhorar a leitura.