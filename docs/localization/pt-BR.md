# Ascension — padrão de localização PT-BR

Este documento é a referência editorial da localização brasileira do Ascension.
O objetivo é permitir que um jogador brasileiro entenda todo o conteúdo jogável sem perder o tom de espionagem de GoldenEye.

## Princípios

1. Traduzir sentido e intenção, não palavra por palavra.
2. Preservar nomes próprios, organizações e marcas: James Bond, Natalya, Trevelyan, MI6, KGB, Janus, GoldenEye, Severnaya, Arkangelsk.
3. Usar português brasileiro natural, claro e contemporâneo, sem gíria moderna que descaracterize 1995/1997.
4. M deve soar formal, precisa e autoritária.
5. Q deve soar técnico, seco e levemente sarcástico.
6. Moneypenny deve manter ironia, elegância e flerte; não transformar suas falas em tradução literal.
7. Bond deve soar curto, seguro e espirituoso.
8. Trevelyan deve soar elegante, amargo e ameaçador.
9. Natalya deve soar inteligente, direta e humana.
10. Mensagens operacionais devem priorizar clareza imediata durante o jogo.

## Terminologia canônica

- Agent -> Agente
- Secret Agent -> Agente Secreto
- 00 Agent -> Agente 00
- Mission -> Missão
- Objective -> Objetivo
- Primary Objectives -> Objetivos Principais
- Mission Status -> Status da Missão
- Completed -> Concluído / Concluída conforme o substantivo
- Failed -> Falhou
- Abort/Aborted -> Abortar / Abortada
- Multiplayer -> Multijogador
- Cheat Options -> Opções de Trapaça
- Health -> Vida
- Armor -> Colete / Armadura somente quando o contexto exigir
- Aim -> Mira
- Auto Aim -> Mira Automática
- Accuracy -> Precisão
- Weapon -> Arma
- Ammo -> Munição
- Keycard -> Cartão de Acesso
- Safe key -> Chave do Cofre
- Security door -> Porta de Segurança
- Guard -> Guarda
- Soldier -> Soldado
- Scientist -> Cientista
- Civilian -> Civil

## Fases

Nomes geográficos reais permanecem no original. Nomes funcionais das fases são localizados para o jogador:

- Dam -> Barragem
- Facility -> Instalação
- Runway -> Pista
- Surface -> Superfície
- Bunker -> Bunker
- Silo -> Silo
- Frigate -> Fragata
- Statue -> Estátua
- Archives -> Arquivos
- Streets -> Ruas
- Depot -> Depósito
- Train -> Trem
- Jungle -> Selva
- Control -> Controle
- Caverns -> Cavernas
- Cradle -> Antena
- Aztec -> Asteca
- Egyptian -> Egípcia

## Qualidade

Uma string só é considerada concluída quando:

- existe uma decisão explícita PT-BR para o seu ID;
- acentos e cedilha são preservados;
- variáveis, quebras de linha e marcadores funcionais permanecem válidos;
- o texto cabe na interface ou possui quebra adequada;
- foi verificado no contexto em que aparece;
- nomes próprios mantidos em inglês contam como revisados, não como lacunas.

A localização não deve depender apenas de comparação pelo texto inglês. O identificador `bank << 10 | slot` é a identidade canônica, porque frases iguais podem exigir traduções diferentes em contextos diferentes.

## Regra de cobertura

Em modo PT-BR de desenvolvimento, qualquer string carregada por `langGet` sem entrada revisada deve ser registrada como lacuna. Uma versão marcada como completa deve ter zero lacunas em campanha, multiplayer, menus, relógio, armas, objetos, cheats, créditos e mensagens de sistema, além de uma auditoria separada de texturas/modelos que contenham palavras.
