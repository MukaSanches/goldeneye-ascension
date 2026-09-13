# Guia de sobrevivência do Ascension

Este documento existe para uma situação simples: você abriu o código e não sabe o que fazer.

## Antes de tocar em qualquer arquivo

```sh
git switch main
git pull
git status
```

Se `git status` mostrar alterações que você não reconhece, pare e descubra o que são antes de continuar.

## Quero testar uma ideia

```sh
git switch -c teste/minha-ideia
```

Faça uma mudança pequena. Compile:

```sh
./build-pc.sh ntsc-final
```

Abra o jogo e teste a área alterada.

## Quero saber o que mudei

```sh
git status
git diff
```

`status` mostra os arquivos. `diff` mostra as linhas.

## Quero salvar um ponto seguro

```sh
git add .
git commit -m "descreva o que funciona neste ponto"
```

## Quero desfazer um commit

```sh
git log --oneline -10
git revert CODIGO_DO_COMMIT
```

## Quero abandonar uma alteração ainda não commitada

Confira primeiro `git diff`. Se realmente quiser apagar essas alterações rastreadas:

```sh
git restore .
```

## Onde procurar

- input: `port/src/input.c`
- vídeo: `port/src/video.c`
- áudio: `port/src/audio.c`
- configuração: `port/src/config.c`
- renderer: `port/fast3d/`
- jogo: `src/`
- build: `CMakeLists.txt` e `build-pc.sh`

## Como pedir ajuda de um jeito útil

Sempre forneça:

```sh
git status
git log --oneline -5
```

E copie a primeira mensagem de erro relevante, o comando executado e o que foi alterado antes dela.

## Regra principal

Nunca faça vinte alterações antes do primeiro teste. Mudanças pequenas são mais fáceis de entender, revisar e reverter.
