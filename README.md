# ASCENSION

<p align="center">
  <strong>O clássico elevado no PC.</strong><br>
  Preservação • Português • Experiência moderna • Engenharia aberta
</p>

<p align="center">
  <a href="https://mukasanches.github.io/goldeneye-pc-port/"><strong>Site oficial</strong></a> ·
  <a href="ROADMAP_ASCENSION.md">Roadmap</a> ·
  <a href="docs/GUIA-INICIANTE.md">Começar do zero</a> ·
  <a href="https://github.com/MukaSanches/goldeneye-pc-port/issues">Desenvolvimento</a>
</p>

<p align="center">
  <img src="docs/img/attract-bunker1.png" width="32%" alt="GoldenEye rodando no PC — Bunker">
  <img src="docs/media/goldeneye-demo.gif" width="32%" alt="Demonstração do GoldenEye rodando no PC">
  <img src="docs/img/attract-dam.png" width="32%" alt="GoldenEye rodando no PC — Dam">
</p>

> **Ascension** é nossa linha independente de evolução do port nativo de **GoldenEye 007 (Nintendo 64, 1997)** para computadores modernos. Preservamos a genealogia técnica, autoria, licenças e créditos do trabalho do qual o projeto deriva, enquanto construímos direção, documentação e roadmap próprios.

## A missão

O Ascension parte de uma ideia simples: **preservar o clássico sem congelá-lo no tempo**. O comportamento original continua sendo a referência; melhorias modernas entram de forma consciente e, quando alteram a experiência, devem ser identificáveis e preferencialmente opcionais.

A direção do projeto inclui localização PT-BR, controles modernos, configuração, acessibilidade, apresentação, estabilidade, documentação e uma base cada vez melhor para contribuições da comunidade.

**Não distribuímos ROM comercial.** O usuário deve fornecer sua própria cópia legalmente obtida quando o processo de build exigir.

## Estado do projeto

O projeto está em desenvolvimento. A base já inicializa, renderiza e permite jogar, mas ainda existem defeitos e áreas que precisam de validação. Aqui, **implementado**, **compilado**, **testado automaticamente** e **testado jogando** são estados diferentes.

Isso é parte da identidade de engenharia do Ascension: ambição alta sem transformar plano em promessa ou build em prova de qualidade.

## Começo rápido — Windows

### 1. MSYS2 / MINGW64

Instale as dependências:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 mingw-w64-x86_64-zlib mingw-w64-x86_64-cmake mingw-w64-x86_64-python make git
```

### 2. Clone

```sh
git clone https://github.com/MukaSanches/goldeneye-pc-port.git
cd goldeneye-pc-port
```

### 3. Prepare sua ROM

Para a ROM americana suportada, o caminho esperado é:

```text
data/ge007.ntsc-final.z64
```

Nunca faça commit ou upload da ROM.

### 4. Compile

```sh
./build-pc.sh ntsc-final
```

### 5. Execute

```sh
./build-pc/ge007.x86_64.exe
```

Para detalhes de preparação e diagnóstico, consulte [`docs/building.md`](docs/building.md).

## Onde mexer

| Objetivo | Primeiro lugar para investigar |
|---|---|
| Teclado, mouse e controle | `port/src/input.c` |
| Configurações | `port/src/config.c` e `ge007.ini` |
| Janela e vídeo | `port/src/video.c` |
| Áudio | `port/src/audio.c` |
| Renderização | `port/fast3d/` |
| Integração com o PC | `port/src/` |
| Lógica reconstruída do jogo | `src/` |
| Estruturas e definições | `include/` |
| Ferramentas de dados | `tools_pc/` |
| Documentação | `docs/` |
| Build | `CMakeLists.txt` e `build-pc.sh` |

## Método Ascension

**Entenda → mude pouco → compile → teste → confira o diff → documente → faça commit.**

Mudanças de input, gráficos e áudio precisam de teste humano em jogo. Uma correção que passa em teste automatizado ainda pode produzir uma regressão visual, temporal ou de sensação de controle.

## Trabalhe de forma reversível

```sh
git switch main
git pull
git switch -c melhoria/minha-ideia
```

Depois:

```sh
./build-pc.sh ntsc-final
./build-pc/ge007.x86_64.exe
git status
git diff
```

Se estiver correto:

```sh
git add .
git commit -m "feat: descreve claramente a melhoria"
```

Para desfazer um commit já publicado, prefira:

```sh
git revert CODIGO_DO_COMMIT
```

O histórico deve explicar a evolução, não escondê-la.

## Arquitetura em uma tela

```text
goldeneye-pc-port/
├── src/              lógica reconstruída do jogo
├── include/          estruturas e definições
├── port/             integração com computadores modernos
│   ├── src/          input, vídeo, áudio, configuração, arquivos...
│   └── fast3d/       renderização
├── tools_pc/         preparação e conversão de dados
├── scripts/          ferramentas auxiliares
├── assets/           estrutura de assets
├── data/             dados locais; ROM nunca entra no Git
├── docs/             site, documentação e pesquisa
├── CMakeLists.txt    regras de build
└── build-pc.sh       build do PC
```

Em uma frase: `src/` é o jogo; `port/` faz esse jogo conversar com o PC; `tools_pc/` prepara dados; `docs/` concentra conhecimento e apresentação; `build-pc/` é resultado gerado localmente.

## Roadmap Ascension

A evolução está organizada por camadas para reduzir regressões e deixar claro o que pertence à preservação e o que pertence à modernização.

| Marco | Direção |
|---|---|
| **V0.1 — Fundação** | build reproduzível e execução no PC |
| **V0.2 — Brasil** | localização PT-BR e experiência em português |
| **V0.3 — Controles modernos** | presets, remapeamento e refinamento de input |
| **V0.4 — Experiência PC** | configuração e qualidade de vida |
| **V0.5 — Classic / Enhanced** | separação explícita entre preservação e melhorias |
| **V0.6 — Estabilidade** | regressões, compatibilidade e polimento |
| **V0.7 — Apresentação moderna** | vídeo, HUD e refinamentos visuais compatíveis |
| **V0.8 — Modding** | interfaces e ferramentas para comunidade |
| **V0.9+** | experiências avançadas somente após uma base madura |

Leia [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md) para a direção detalhada.

## Site oficial

O GitHub Pages do fork foi reposicionado como **site oficial do Ascension**, em português, com identidade visual própria, apresentação do projeto, demonstração real, roadmap, guia de build, comunidade e metadados para compartilhamento e mecanismos de busca.

**[Acessar o site Ascension](https://mukasanches.github.io/goldeneye-pc-port/)**

A fonte publicada está em `docs/index.md` + `docs/assets/`, porque este repositório usa `main / docs` como origem do GitHub Pages.

## Documentação

- [`docs/GUIA-INICIANTE.md`](docs/GUIA-INICIANTE.md) — entrada para quem nunca mexeu no projeto.
- [`docs/ASCENSION.md`](docs/ASCENSION.md) — identidade e princípios.
- [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md) — direção de produto e engenharia.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — uso responsável de conhecimento externo.
- [`docs/building.md`](docs/building.md) — build e preparação de dados.
- [`docs/internals.md`](docs/internals.md) — arquitetura interna.
- [`docs/porting-notes.md`](docs/porting-notes.md) — conhecimento técnico acumulado.
- [`docs/dev/`](docs/dev/) — investigações e registros de engenharia.

A documentação herdada está sendo migrada para português com cuidado para não traduzir nomes de funções, símbolos, paths, comandos e outros identificadores técnicos que precisam permanecer exatos.

## Contribua

Uma boa contribuição não precisa ser enorme. Ela precisa ser compreensível, testável e revisável.

Ao abrir um Pull Request, explique: **problema**, **solução**, **arquivos alterados**, **teste realizado**, **como reproduzir** e **riscos conhecidos**.

Não envie ROM ou assets comerciais extraídos. Não apague autoria ou licenças herdadas. Não reutilize código externo sem verificar licença e proveniência. Não descreva algo como “100% funcionando” apenas porque compilou.

## Origem, créditos e licença

Ascension não começou do zero. Ele existe graças a anos de decompilação, engenharia reversa, pesquisa e portabilidade realizados pela comunidade. Ter direção própria não significa reivindicar autoria sobre trabalho herdado.

Consulte [`NOTICE`](NOTICE), [`LICENSE`](LICENSE), [`CITATION.cff`](CITATION.cff) e [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

---

<p align="center">
  <strong>ASCENSION</strong><br>
  Preservar o clássico. Elevar a experiência. Abrir o conhecimento.
</p>
