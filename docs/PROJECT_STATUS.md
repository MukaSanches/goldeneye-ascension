# Project status

Este documento descreve maturidade, não porcentagem de conclusão. Uma área pode estar implementada e ainda não estar pronta para ser tratada como estável.

## Escala usada

| Estado | Significado |
|---|---|
| **Reference** | comportamento usado como baseline para comparação |
| **Active** | em desenvolvimento e usado no fluxo principal |
| **Experimental** | disponível para validação, sujeito a mudanças |
| **Planned** | direção aceita, ainda sem implementação integrada suficiente |
| **Blocked** | depende de trabalho anterior ou de evidência técnica ausente |

## Estado por área

| Área | Estado | Observação |
|---|---|---|
| Build Windows/MSYS2 | **Active** | caminho principal de desenvolvimento e teste |
| CI | **Active** | validação e builds automatizados no GitHub Actions |
| Build Linux | **Experimental** | útil para portabilidade e compilação, com menos validação de runtime |
| Comportamento clássico | **Reference** | baseline para regressões e decisões de compatibilidade |
| Localização PT-BR | **Active** | primeira localização Ascension; integração e cobertura evoluem por etapas |
| Controles modernos | **Planned** | presets, remapeamento e refinamento entram após estabilização da base |
| PC settings / UX | **Active** | melhorias devem permanecer configuráveis e rastreáveis |
| Presentation / HUD | **Planned** | mudanças visuais precisam de comparação e playtest |
| Acessibilidade | **Planned** | priorizar opções úteis e verificáveis |
| Modding / creator tools | **Planned** | depende de interfaces mais estáveis |
| Release 1.0 | **Blocked** | exige critérios de compatibilidade, regressão e processo de release consolidados |

## O que “funciona” significa aqui

Evite resumir uma mudança apenas como “funciona”. Registre o nível de evidência:

1. **Compila** — o toolchain aceitou a mudança.
2. **Executa** — o binário inicializou sem crash imediato.
3. **Reproduz** — o fluxo afetado foi testado de forma definida.
4. **Não regrediu** — comparações relevantes não mostraram regressão conhecida.
5. **Foi jogado** — comportamento sensível a input, áudio, renderização ou UX foi validado por uma pessoa.
6. **Está documentado** — outra pessoa consegue repetir o teste.

Quanto maior o impacto da mudança, mais níveis dessa escala devem ser cobertos antes de tratá-la como pronta.

## Branch principal

`main` é a referência de integração pública. Branches de desenvolvimento podem conter experimentos ou trabalho em recuperação, mas não substituem o estado documentado do branch principal.

## Compatibilidade

A compatibilidade suportada deve ser afirmada apenas quando houver evidência repetível. O fato de uma plataforma compilar não implica automaticamente suporte completo de runtime.

## Atualização deste documento

Atualize esta página quando uma área mudar de maturidade de forma significativa, quando uma plataforma ganhar ou perder suporte, ou quando uma feature passar a fazer parte do fluxo padrão.