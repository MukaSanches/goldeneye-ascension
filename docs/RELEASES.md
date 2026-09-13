# Release process

Este documento define quando uma versão Ascension pode ser tratada como release pública. O objetivo é impedir que um commit simplesmente compilado seja apresentado como versão pronta.

## Tipos de release

### Development build

Build de desenvolvimento para teste. Pode mudar rapidamente e não implica compatibilidade estável.

### Alpha

Fluxos principais já podem ser exercitados, mas ainda existem lacunas conhecidas de estabilidade, compatibilidade ou acabamento. Mudanças incompatíveis ainda são possíveis.

### Beta

Arquitetura e configuração estão próximas do formato pretendido para a versão estável. O foco passa a ser regressão, compatibilidade, documentação e correções.

### Release candidate

Candidato a release estável. Nenhuma feature ampla deve entrar sem justificativa excepcional. Mudanças devem ser majoritariamente correções, documentação ou bloqueadores de release.

### Stable

Versão com plataforma e limitações declaradas, documentação reproduzível, histórico de mudanças e critérios de regressão atendidos.

## Checklist mínimo

Antes de publicar uma versão numerada:

- definir o commit/tag exato;
- atualizar `CHANGELOG.md`;
- revisar `README.md`, `docs/PROJECT_STATUS.md` e instruções de build;
- executar CI no commit final;
- confirmar que os artefatos não contêm ROM nem assets comerciais;
- validar o caminho Windows/MSYS2 suportado;
- executar smoke test do binário produzido;
- testar manualmente áreas alteradas desde a versão anterior;
- listar limitações conhecidas;
- verificar `NOTICE`, `LICENSE` e proveniência de novas dependências/código;
- preparar notas de release sem prometer suporte não testado.

## Numeração

Antes de `1.0.0`, o projeto pode usar versões `0.x.y` enquanto interfaces e configuração ainda evoluem.

- `x` identifica um marco de desenvolvimento com mudança relevante de capacidade ou maturidade.
- `y` identifica correções e refinamentos compatíveis dentro do mesmo marco sempre que possível.

A partir de `1.0.0`, a intenção é usar versionamento semântico para superfícies declaradas estáveis.

## Tags

Tags de release devem ser anotadas e apontar para um commit que já passou pelos checks esperados. Evite mover uma tag publicada; se algo estiver errado, publique uma nova versão ou marque a anterior como problemática nas release notes.

## Artefatos

Qualquer pacote distribuível deve conter apenas material redistribuível pelo projeto. ROM e assets comerciais nunca devem ser empacotados.

Artefatos devem indicar:

- versão;
- plataforma;
- arquitetura;
- commit de origem;
- instruções mínimas de execução;
- dependências de runtime relevantes;
- hash de integridade quando aplicável.

## Notas de release

Release notes devem responder:

1. O que mudou para o usuário?
2. O que foi corrigido?
3. O que ainda é conhecido como limitação?
4. Qual plataforma foi realmente testada?
5. Existe mudança de configuração ou migração necessária?

Evite linguagem promocional que não possa ser sustentada por teste reproduzível.

## Rollback

Cada release deve permanecer associada a um commit identificável. Se uma regressão grave for descoberta, a prioridade é documentar o impacto, impedir novos downloads quando apropriado e publicar uma correção rastreável — não reescrever silenciosamente a versão existente.