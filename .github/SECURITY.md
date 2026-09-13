# Security Policy

Ascension é um projeto local-first e não possui serviço de backend. A superfície de segurança relevante está concentrada no executável do port, no processamento de ROM/assets fornecidos pelo usuário, nas ferramentas de build/extração e nos workflows de CI.

## Como reportar

Não abra uma issue pública para uma vulnerabilidade ainda não corrigida.

Use o fluxo privado do GitHub em **Security → Report a vulnerability**:

https://github.com/MukaSanches/goldeneye-pc-port/security/advisories/new

Se o recurso privado não estiver disponível, entre em contato com o mantenedor pelo canal público indicado no perfil do GitHub e informe apenas que precisa tratar de um assunto de segurança. Não publique detalhes de exploração antes de receber um canal privado de resposta.

Inclua, quando possível:

- commit afetado (`git rev-parse HEAD`);
- sistema operacional e ambiente de build;
- região/ROMID usada;
- passos mínimos para reprodução;
- crash log ou stack trace;
- avaliação de impacto;
- qualquer mitigação temporária conhecida.

Nunca envie ROM, assets comerciais extraídos ou conteúdo proprietário como parte do relatório.

## Escopo

Em escopo:

- corrupção de memória ou execução indevida causada pela camada `port/`;
- parsing inseguro de arquivos controláveis pelo usuário;
- falhas nas ferramentas de preparação/build com impacto de segurança;
- problemas de supply chain ou dependências acionáveis pelo projeto;
- permissões ou comportamento inseguro em GitHub Actions.

Normalmente fora de escopo:

- defeitos puramente visuais ou de gameplay;
- ROM incorreta, ausente ou incompatível;
- bugs herdados sem alteração que não aumentem risco no port;
- problemas que exigem redistribuição de material que o projeto não fornece;
- engenharia social contra usuários ou mantenedores.

## Versões suportadas

Enquanto não houver uma release estável, a referência de correção é o topo de `main`. Branches históricas, forks e builds antigos podem não receber backport.

Quando releases estáveis forem publicadas, esta seção será atualizada com a janela de suporte correspondente.

## Divulgação coordenada

O projeto busca confirmar o relatório, preparar uma correção e publicar crédito técnico de forma responsável quando apropriado. Prazo de divulgação depende da severidade e da capacidade de reproduzir o problema; não existe SLA formal neste estágio.