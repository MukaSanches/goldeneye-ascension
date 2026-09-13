<p align="center"><img src="docs/assets/ascension-logo.svg" width="860" alt="Ascension"></p>
<p align="center"><strong>O clássico. Elevado.</strong><br>Preservação · Português · Experiência moderna · Engenharia aberta</p>
<p align="center"><a href="https://mukasanches.github.io/goldeneye-pc-port/"><strong>Site oficial</strong></a> · <a href="ROADMAP_ASCENSION.md">Roadmap</a> · <a href="docs/GUIA-INICIANTE.md">Guia para iniciantes</a> · <a href="https://github.com/MukaSanches/goldeneye-pc-port/issues">Desenvolvimento</a></p>

<p align="center"><img src="docs/img/attract-bunker1.png" width="31%" alt="Bunker"><img src="docs/media/goldeneye-demo.gif" width="36%" alt="GoldenEye em execução"><img src="docs/img/attract-dam.png" width="31%" alt="Dam"></p>

## Ascension

**Ascension** é uma linha independente de evolução do port nativo de **GoldenEye 007 (Nintendo 64, 1997)** para computadores modernos. O projeto preserva a genealogia técnica, autoria, créditos e licenças da base da qual deriva, enquanto desenvolve identidade, documentação, experiência e roadmap próprios.

A direção é simples: **preservar o clássico sem congelá-lo no tempo**. Melhorias modernas devem ser conscientes, rastreáveis e, quando mudarem a experiência original, preferencialmente opcionais.

> **Não distribuímos ROM comercial.** Para compilar, o usuário fornece sua própria cópia legalmente obtida quando exigida pelo processo.

## O que diferencia a direção Ascension

| Pilar | Direção |
|---|---|
| **Classic** | comportamento original como referência |
| **Brasil** | localização PT-BR e documentação acessível |
| **Modern Controls** | mouse, teclado, controle, presets e remapeamento |
| **PC Experience** | configuração, acessibilidade, vídeo, HUD e qualidade de vida |
| **Engineering** | commits pequenos, reversíveis e estados de teste explícitos |
| **Community** | documentação e futura base de modding/ferramentas |

**Implementado**, **compilado**, **testado automaticamente** e **testado jogando** são estados diferentes. O Ascension não transforma roadmap em promessa nem build em prova de qualidade.

## Começo rápido — Windows

Abra o **MSYS2 MINGW64** e instale as dependências:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 mingw-w64-x86_64-zlib mingw-w64-x86_64-cmake mingw-w64-x86_64-python make git
```

Clone e entre no projeto:

```sh
git clone https://github.com/MukaSanches/goldeneye-pc-port.git
cd goldeneye-pc-port
```

Para a ROM americana suportada, o caminho esperado é:

```text
data/ge007.ntsc-final.z64
```

Compile e execute:

```sh
./build-pc.sh ntsc-final
./build-pc/ge007.x86_64.exe
```

Consulte [`docs/building.md`](docs/building.md) para preparação e diagnóstico. Nunca faça commit ou upload da ROM.

## Mapa técnico

| Objetivo | Primeiro lugar para investigar |
|---|---|
| Teclado, mouse e controle | `port/src/input.c` |
| Configurações | `port/src/config.c` e `ge007.ini` |
| Janela e vídeo | `port/src/video.c` |
| Áudio | `port/src/audio.c` |
| Renderização | `port/fast3d/` |
| Integração PC | `port/src/` |
| Lógica reconstruída | `src/` |
| Estruturas | `include/` |
| Ferramentas de dados | `tools_pc/` |
| Site e documentação | `docs/` |

## Método Ascension

**Entenda → mude pouco → compile → teste → confira o diff → documente → commit.**

Gráficos, áudio e sensação de controle exigem teste humano. Para experimentar com segurança:

```sh
git switch main
git pull
git switch -c melhoria/minha-ideia
# altere, compile e teste
git status
git diff
```

Para desfazer uma mudança já publicada, prefira `git revert <commit>`. O histórico deve explicar a evolução, não escondê-la.

## Roadmap

| Marco | Direção |
|---|---|
| **V0.1 — Fundação** | build reproduzível e execução no PC |
| **V0.2 — Brasil** | localização PT-BR e experiência em português |
| **V0.3 — Modern Controls** | presets, remapeamento e refinamento de input |
| **V0.4 — PC Experience** | configuração e qualidade de vida |
| **V0.5 — Classic / Enhanced** | preservação e melhorias claramente separadas |
| **V0.6 — Estabilidade** | regressões, compatibilidade e polimento |
| **V0.7 — Modern Presentation** | vídeo, HUD e refinamentos visuais |
| **V0.8 — Modding** | interfaces e ferramentas para comunidade |
| **V0.9+** | experiências avançadas sobre uma base madura |

Veja [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md).

## Site oficial

A experiência pública do Ascension vive em [`docs/index.html`](docs/index.html), com identidade visual própria, demonstração, roadmap e instruções. Os arquivos de marca estão em [`docs/assets/`](docs/assets/).

**[Abrir o site Ascension](https://mukasanches.github.io/goldeneye-pc-port/)**

## Documentação

- [`docs/GUIA-INICIANTE.md`](docs/GUIA-INICIANTE.md) — entrada para novos contribuidores.
- [`docs/ASCENSION.md`](docs/ASCENSION.md) — identidade e princípios.
- [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md) — direção de produto e engenharia.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — proveniência e uso responsável de conhecimento externo.
- [`docs/building.md`](docs/building.md) — build e preparação de dados.
- [`docs/internals.md`](docs/internals.md) — arquitetura interna.
- [`docs/porting-notes.md`](docs/porting-notes.md) — conhecimento técnico acumulado.
- [`docs/dev/`](docs/dev/) — investigações e registros de engenharia.

## Contribua

Uma boa contribuição precisa ser compreensível, testável e revisável. Em Pull Requests, descreva **problema**, **solução**, **arquivos alterados**, **teste**, **reprodução** e **riscos conhecidos**.

Não envie ROM ou assets comerciais extraídos. Não apague autoria ou licenças herdadas. Não reutilize código externo sem verificar licença e proveniência.

## Origem, créditos e licença

Ascension existe sobre anos de decompilação, engenharia reversa, pesquisa e portabilidade da comunidade. Direção própria não significa reivindicar autoria sobre trabalho herdado. GoldenEye e marcas relacionadas pertencem aos respectivos titulares.

Consulte [`NOTICE`](NOTICE), [`LICENSE`](LICENSE), [`CITATION.cff`](CITATION.cff) e [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

---
<p align="center"><img src="docs/assets/ascension-mark.svg" width="72" alt="Símbolo Ascension"><br><strong>ASCENSION</strong><br>Preservar o clássico. Elevar a experiência. Abrir o conhecimento.</p>