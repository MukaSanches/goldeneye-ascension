# ASCENSION

<p align="center"><strong>GoldenEye 007 no PC, evoluído como um projeto aberto, documentado e acessível em português.</strong></p>

<p align="center">
  <img src="docs/img/attract-bunker1.png" width="32%" alt="GoldenEye rodando no PC — Bunker 1">
  <img src="docs/media/goldeneye-demo.gif" width="32%" alt="Demonstração do GoldenEye rodando no PC">
  <img src="docs/img/attract-dam.png" width="32%" alt="GoldenEye rodando no PC — Dam">
</p>

<p align="center"><em>Imagens e demonstração reais do motor do projeto. O GIF mostra trechos do jogo em execução.</em></p>

> **Novo aqui? Comece por esta página.** Ela foi escrita para permitir que uma pessoa sem experiência com este código consiga instalar, compilar, testar, alterar e desfazer alterações sem precisar entender o projeto inteiro.

## O que é o Ascension?

Ascension é nossa linha independente de desenvolvimento do port nativo de **GoldenEye 007 (Nintendo 64, 1997)** para computadores modernos. O projeto preserva a genealogia técnica, autoria, licenças e créditos do trabalho do qual deriva, mas possui direção, documentação e roadmap próprios.

O objetivo é simples: preservar a experiência clássica e construir, de forma opcional e reversível, uma experiência de PC mais moderna — localização, controles, configuração, acessibilidade, apresentação, estabilidade e ferramentas para a comunidade.

> **Importante:** nenhuma ROM comercial é distribuída aqui. Você deve fornecer sua própria cópia legalmente obtida quando o processo de build exigir.

## Estado atual

O projeto está em desenvolvimento. A base já inicializa, renderiza e permite jogar a campanha, mas ainda existem defeitos e áreas que precisam de validação. Uma compilação bem-sucedida não significa que cada missão, cena, áudio ou configuração esteja perfeita.

O desenvolvimento do Ascension segue quatro estados: **implementado**, **compilado**, **testado automaticamente** e **testado jogando**. Não tratamos esses termos como sinônimos.

## Começo rápido — Windows

### 1. Instale o MSYS2 e abra `MSYS2 MINGW64`

Instale as dependências:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 mingw-w64-x86_64-zlib mingw-w64-x86_64-cmake mingw-w64-x86_64-python make git
```

### 2. Baixe o Ascension

```sh
git clone https://github.com/MukaSanches/goldeneye-pc-port.git
cd goldeneye-pc-port
```

### 3. Prepare sua ROM

Crie `data/`. Para a ROM americana suportada, o caminho esperado é:

```text
data/ge007.ntsc-final.z64
```

Nunca faça commit ou upload da ROM.

### 4. Compile

```sh
./build-pc.sh ntsc-final
```

O executável será gerado em:

```text
build-pc/ge007.x86_64.exe
```

### 5. Execute

```sh
./build-pc/ge007.x86_64.exe
```

Se a build funcionar mas faltarem dados derivados da sua própria ROM, siga o guia completo em [`docs/building.md`](docs/building.md).

## Quero alterar o jogo: onde começo?

| Quero mudar | Primeiro lugar para olhar |
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

### Regra de ouro

**Mude uma coisa → compile → jogue/teste → confira `git diff` → faça um commit.**

## Faça experiências sem destruir a `main`

```sh
git switch main
git pull
git switch -c teste/minha-mudanca
```

Depois de editar:

```sh
./build-pc.sh ntsc-final
./build-pc/ge007.x86_64.exe
git status
git diff
```

Se estiver correto:

```sh
git add .
git commit -m "descreva claramente a mudanca"
```

## Fiz besteira

Antes de qualquer coisa:

```sh
git status
git diff
```

Se ainda não fez commit e realmente quer descartar as alterações rastreadas:

```sh
git restore .
```

Se já fez um commit ruim:

```sh
git log --oneline -10
git revert CODIGO_DO_COMMIT
```

Preferimos `git revert`: ele desfaz a mudança sem apagar o histórico.

## Não compilou

Rode:

```sh
git status
git log --oneline -5
./build-pc.sh ntsc-final
```

Procure a **primeira mensagem de erro**, não apenas a última. Ao pedir ajuda, envie o comando usado, a primeira mensagem de erro, algumas linhas ao redor dela, `git status`, os cinco últimos commits e o que você mudou antes do problema.

## Como testar direito

Depois de uma mudança, no mínimo: compile; abra o jogo; passe pelo menu; inicie uma missão; teste o recurso alterado; teste algo próximo; e reinicie quando a mudança envolver configuração ou save. Mudanças de input, gráficos e áudio precisam de teste humano em jogo.

## Mapa mental das pastas

```text
goldeneye-pc-port/
├── src/              jogo reconstruído
├── include/          estruturas e definições
├── port/             ponte entre GoldenEye e o computador
│   ├── src/          input, vídeo, áudio, config, arquivos...
│   └── fast3d/       renderização
├── tools_pc/         preparação/conversão de dados
├── scripts/          ferramentas auxiliares
├── assets/           estrutura de assets
├── data/             dados locais; ROM nunca entra no Git
├── docs/             documentação e pesquisa
├── CMakeLists.txt    regras de build
└── build-pc.sh       build do PC
```

Em uma frase: `src/` é o jogo; `port/` faz esse jogo conversar com o PC; `tools_pc/` prepara dados; `docs/` explica o conhecimento; `build-pc/` é o resultado gerado.

## Documentação

- [`docs/GUIA-INICIANTE.md`](docs/GUIA-INICIANTE.md) — manual de sobrevivência para quem nunca mexeu no projeto.
- [`docs/ASCENSION.md`](docs/ASCENSION.md) — identidade e princípios.
- [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md) — direção do desenvolvimento.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — como usar conhecimento externo corretamente.
- [`docs/building.md`](docs/building.md) — build e preparação de dados em profundidade.
- [`docs/internals.md`](docs/internals.md) — arquitetura interna.
- [`docs/porting-notes.md`](docs/porting-notes.md) — conhecimento técnico acumulado.
- [`docs/dev/`](docs/dev/) — investigações e registros de engenharia.

## Site

O código do novo site oficial em português está em [`site/`](site/). Ele foi criado especificamente para o Ascension, com apresentação visual própria, navegação responsiva, seção de demonstração, roadmap e guia de contribuição.

## Contribuindo

Crie uma branch, faça uma mudança pequena, compile e teste. Depois:

```sh
git add .
git commit -m "feat: descreve a melhoria"
git push -u origin SUA_BRANCH
```

Abra um Pull Request explicando: problema, solução, arquivos alterados, teste realizado, como reproduzir e riscos conhecidos.

## O que não fazer

- Não envie ROM ou assets comerciais extraídos.
- Não apague autoria, créditos ou licenças herdadas.
- Não copie código externo sem conferir licença e proveniência.
- Não chame algo de “100% funcionando” apenas porque compilou.
- Não misture dezenas de mudanças sem checkpoints.
- Não use `git push --force` na `main` para esconder um erro.

## Origem, créditos e licença

Ascension não começou do zero. Ele existe graças a anos de trabalho de engenharia reversa, decompilação e portabilidade feitos por outras pessoas. Independência significa que o Ascension possui direção própria; **não significa reivindicar autoria sobre trabalho herdado**.

Consulte [`NOTICE`](NOTICE), [`LICENSE`](LICENSE), [`CITATION.cff`](CITATION.cff) e [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

---

<p align="center"><strong>Preservar o clássico. Melhorar o que faz sentido. Documentar para que a próxima pessoa consiga continuar.</strong></p>
