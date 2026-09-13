# Ascension roadmap

Este roadmap registra direção e critérios de maturidade. Não é calendário nem promessa de prazo. Um item só passa a concluído quando existe implementação, evidência de teste e documentação suficiente para outra pessoa reproduzir o resultado.

## V0.1 — Fundação

Objetivo: manter uma base de PC reproduzível e fácil de depurar.

Critérios de saída:

- build Windows/MSYS2 reproduzível;
- CI funcional no branch principal;
- documentação de build e diagnóstico coerente com o repositório;
- separação clara entre código, ROM e assets proprietários;
- rollback simples por commit.

## V0.2 — Brasil

Objetivo: tornar PT-BR uma localização de primeira classe sem perder o inglês como referência segura.

Critérios de saída:

- arquitetura de localização integrada ao branch principal;
- fallback para inglês definido e previsível;
- menus e textos prioritários cobertos;
- acentos, encoding, quebra de linha e layout validados;
- revisão humana dos textos;
- ausência de dependência em edição manual de assets comerciais.

## V0.3 — Modern Controls

Objetivo: oferecer controles de PC claros, configuráveis e consistentes.

Critérios de saída:

- presets Classic, Modern e Custom definidos;
- mouse com eixos e sensibilidade previsíveis;
- gamepad com deadzones e remapeamento onde suportado;
- configuração persistente;
- regressões de input testadas em jogo.

## V0.4 — PC Experience

Objetivo: reduzir a dependência de configuração externa e melhorar a experiência diária.

Critérios de saída:

- opções importantes descobríveis;
- fluxo de vídeo e fullscreen confiável;
- mensagens de erro úteis para problemas comuns;
- configuração documentada e reversível;
- defaults seguros.

## V0.5 — Classic / Enhanced

Objetivo: separar preservação de melhorias opcionais.

Critérios de saída:

- comportamento Classic claramente definido;
- melhorias Enhanced ativáveis sem substituir silenciosamente o baseline;
- configuração e documentação coerentes entre os modos;
- nenhuma opção experimental apresentada como comportamento original.

## V0.6 — Estabilidade

Objetivo: reduzir regressões e ampliar a confiança na campanha.

Critérios de saída:

- matriz de regressão por missão;
- crashes conhecidos reproduzidos e classificados;
- testes determinísticos/headless onde forem tecnicamente úteis;
- playtests humanos para áudio, renderização e sensação de controle;
- achados negativos documentados para evitar retrabalho.

## V0.7 — Presentation

Objetivo: modernizar apresentação sem descaracterizar o jogo.

Critérios de saída:

- comportamento widescreen e HUD documentado;
- FOV e opções visuais com faixas seguras;
- melhorias visuais opcionais quando alterarem a referência original;
- comparações visuais reproduzíveis para mudanças sensíveis.

## V0.8 — Modding

Objetivo: permitir extensão sem exigir patches invasivos no núcleo.

Critérios de saída:

- pesquisa de manifest/load model consolidada;
- formato de localização extensível;
- interfaces semânticas estáveis para ferramentas;
- documentação suficiente para um primeiro mod externo simples.

## V0.9 — Release candidate

Objetivo: congelar arquitetura suficiente para preparar 1.0.

Critérios de saída:

- instalação e build reproduzíveis a partir de documentação limpa;
- compatibilidade suportada explicitamente listada;
- campanha e fluxos principais cobertos pela matriz de regressão;
- pendências bloqueadoras zeradas ou formalmente adiadas;
- processo de release testado.

## V1.0 — Stable

`1.0.0` fica reservado para uma versão distribuível e documentada, com limites conhecidos claros, compatibilidade declarada, histórico de mudanças, instruções de instalação/build e política de rollback.

## Linhas permanentes

Alguns trabalhos não pertencem a uma única versão:

- manutenção de CI e dependências;
- documentação e diagnóstico;
- proveniência e licenças;
- acessibilidade;
- revisão de performance;
- limpeza de regressões;
- melhoria do site e material público.

A prioridade entre esses trabalhos deve seguir impacto, risco e capacidade de validação — não apenas tamanho da feature.