<!--
Leia CONTRIBUTING.md antes de enviar. Mantenha o PR pequeno o bastante para ser revisado e testado de forma objetiva.
-->

## Problema

<!-- O que estava errado, ausente ou difícil? Inclua issue quando existir. -->

## Solução

<!-- Explique a decisão técnica e por que esta abordagem foi escolhida. -->

## Escopo

<!-- Liste subsistemas/arquivos relevantes. Evite listar cada arquivo se o diff já deixa isso óbvio. -->

- Área afetada:
- Comportamento alterado:
- Compatibilidade esperada:

## Validação

Marque apenas o que você realmente executou.

- [ ] `git diff --check`
- [ ] `./build-pc.sh ntsc-final`
- [ ] O executável abriu sem crash
- [ ] O fluxo/nível afetado foi reproduzido em jogo
- [ ] Mudança visual comparada com screenshot ou referência
- [ ] Mudança de input testada com o dispositivo afetado
- [ ] Mudança de localização revisada em contexto, incluindo quebra de linha
- [ ] Outras regiões foram configuradas/compiladas quando a alteração as afeta

Ambiente testado:

```text
OS:
Toolchain:
ROMID/region:
Commit:
```

## Risco e rollback

<!-- O que pode regredir? Como identificar? O commit pode ser revertido isoladamente? -->

Risco:

Rollback:

## Checklist de integração

- [ ] Não inclui ROM, asset comercial extraído ou outro conteúdo proprietário.
- [ ] Não reformata código não relacionado.
- [ ] Mudanças em `src/` / `include/` são necessárias e foram justificadas.
- [ ] Dependências novas têm licença compatível e justificativa explícita.
- [ ] Documentação foi atualizada quando o comportamento público mudou.
- [ ] O PR não mistura correções ou features independentes sem necessidade.

## Evidência adicional

<!-- Screenshots, logs, medições, notas de compatibilidade ou follow-ups. -->