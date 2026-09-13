# Ascension — GoldenEye no PC

> **Comece por aqui.** Este manual foi escrito para quem nunca mexeu em código. Se você consegue abrir um terminal, copiar um comando e ler uma mensagem de erro, consegue começar.

Ascension é nossa linha independente de desenvolvimento do GoldenEye 007 original de Nintendo 64 para PC. O projeto nasceu do ecossistema de decompilação e ports do jogo e mantém os créditos, licenças e histórico herdados. O Ascension tem seu próprio roadmap, decisões e melhorias.

> **ROM:** este repositório não fornece ROM comercial do GoldenEye. Use somente material que você tenha direito de usar e nunca envie a ROM para o GitHub.

## Quero compilar e abrir o jogo no Windows

O caminho recomendado é **Windows + MSYS2 MINGW64**.

### 1. Abra o terminal certo

Instale o MSYS2 e abra **MSYS2 MINGW64**. Os comandos abaixo devem ser executados nele.

### 2. Instale as ferramentas

Copie, cole e pressione Enter:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain mingw-w64-x86_64-SDL2 mingw-w64-x86_64-zlib mingw-w64-x86_64-cmake mingw-w64-x86_64-python make git
```

### 3. Baixe NOSSO projeto

```sh
git clone https://github.com/MukaSanches/goldeneye-pc-port.git
cd goldeneye-pc-port
```

### 4. Coloque sua ROM

Crie a pasta `data`. Para a versão americana, coloque sua ROM legalmente obtida nela com exatamente este nome:

```text
data/ge007.ntsc-final.z64
```

**Não faça commit da ROM. Não envie a ROM ao GitHub.**

### 5. Compile

```sh
./build-pc.sh ntsc-final
```

Se terminar sem erro fatal, procure:

```text
build-pc/ge007.x86_64.exe
```

### 6. Abra

```sh
./build-pc/ge007.x86_64.exe
```

Se o jogo abriu, sua instalação básica está funcionando.

> Se a build funciona mas o jogo não passa da inicialização, talvez faltem os dados auxiliares gerados a partir da sua própria ROM. Veja [`docs/building.md`](docs/building.md), seção de PC asset sidecars.

---

# Quero alterar alguma coisa. Onde mexo?

Você **não precisa entender o projeto inteiro** antes da primeira alteração.

| Quero mexer em... | Comece aqui |
|---|---|
| teclado, mouse ou controle | `port/src/input.c` |
| configurações | `port/src/config.c` e `ge007.ini` |
| janela e vídeo | `port/src/video.c` |
| áudio | `port/src/audio.c` |
| renderização/OpenGL | `port/fast3d/` |
| integração do jogo com o PC | `port/src/` |
| código reconstruído do jogo | `src/` |
| definições e estruturas | `include/` |
| conversores de dados para PC | `tools_pc/` |
| documentação | `docs/` |
| compilação | `CMakeLists.txt` e `build-pc.sh` |

**Regra de ouro:** mude uma coisa pequena → compile → teste → só depois faça a próxima.

---

# Jeito seguro de modificar o jogo

Primeiro atualize a `main`:

```sh
git switch main
git pull
```

Crie uma branch para sua experiência:

```sh
git switch -c teste/minha-mudanca
```

Uma branch é uma linha de trabalho separada. Você pode experimentar nela sem transformar a `main` em bagunça.

Faça a alteração e compile:

```sh
./build-pc.sh ntsc-final
```

Abra o jogo:

```sh
./build-pc/ge007.x86_64.exe
```

Veja exatamente o que mudou:

```sh
git status
git diff
```

Se estiver correto, salve no histórico:

```sh
git add .
git commit -m "descreva o que voce mudou"
```

Agora sua mudança tem um ponto identificável e reversível.

---

# Fiz besteira. Como volto?

**Não apague o projeto inteiro.** O Git existe justamente para isso.

## Ainda não fiz commit

Primeiro confira:

```sh
git status
git diff
```

Para abandonar alterações locais dos arquivos rastreados:

```sh
git restore .
```

**Cuidado:** isso descarta alterações locais não salvas nesses arquivos.

## Fiz um commit ruim

Veja os últimos commits:

```sh
git log --oneline -10
```

Copie o código do commit ruim e faça:

```sh
git revert CODIGO_DO_COMMIT
```

Exemplo fictício:

```sh
git revert a1b2c3d
```

Preferimos `git revert` porque ele desfaz uma mudança criando outro commit, sem apagar o histórico.

## Minha branch virou uma bagunça

Volte para a principal:

```sh
git switch main
git pull
```

Sua branch experimental continua existindo, mas você voltou para uma base conhecida.

---

# Como descobrir o que quebrou

Quatro comandos básicos:

```sh
git status
git diff
git log --oneline -20
git show CODIGO_DO_COMMIT
```

Eles respondem, respectivamente:

1. **quais arquivos estão diferentes?**
2. **o que mudou dentro deles?**
3. **quais foram as últimas mudanças salvas?**
4. **o que um commit específico fez?**

---

# Como testar sem se enganar

Compilar não significa que a mudança está correta.

Depois de uma alteração:

1. compile sem erro;
2. abra o jogo;
3. passe pelos menus;
4. inicie uma missão;
5. teste exatamente o recurso alterado;
6. teste também recursos próximos;
7. se mexeu em configuração ou save, feche e abra novamente.

Se mexeu em **controles**, jogue de verdade. Se mexeu em **gráficos**, teste parado e em movimento, em mais de uma cena. Se mexeu em **áudio**, escute diferentes situações. Esses casos precisam de validação humana além de testes automáticos.

---

# Não compilou. O que faço?

Execute:

```sh
git status
./build-pc.sh ntsc-final
```

Procure a **primeira mensagem de erro real**. Muitas vezes a última linha é apenas consequência do primeiro erro.

Ao pedir ajuda, mande:

```sh
git status
git log --oneline -5
```

E também informe:

- o comando executado;
- a primeira mensagem de erro;
- algumas linhas antes/depois do erro;
- o que você alterou antes do problema aparecer.

Isso permite reproduzir e diagnosticar o problema.

---

# Compilou, mas o jogo não abre

Confira nesta ordem:

1. estou na pasta correta do projeto?
2. existe `data/`?
3. a ROM está com o nome esperado?
4. preparei os dados auxiliares exigidos pela build atual?
5. o terminal mostrou uma mensagem de erro?
6. minha alteração recente mexeu em `port/`, build, assets ou configuração?

Para o pipeline completo de dados/sidecars, consulte [`docs/building.md`](docs/building.md).

---

# Como atualizar

```sh
git switch main
git pull
./build-pc.sh ntsc-final
```

Evite baixar outra cópia e jogar arquivos manualmente por cima. Deixe o Git controlar as versões.

---

# Como enviar uma melhoria

O fluxo é:

```text
main atualizada
    ↓
branch nova
    ↓
alteração pequena
    ↓
compilar
    ↓
testar
    ↓
revisar git diff
    ↓
commit
    ↓
push
    ↓
Pull Request
```

Comece:

```sh
git switch main
git pull
git switch -c melhoria/nome-da-melhoria
```

Depois de alterar e testar:

```sh
git add .
git commit -m "feat: descreve a melhoria"
git push -u origin melhoria/nome-da-melhoria
```

No Pull Request, explique o problema, a solução, os arquivos alterados, como testou e os riscos conhecidos.

---

# Coisas que você NÃO deve fazer

- não envie ROM para o GitHub;
- não envie assets comerciais extraídos só para facilitar instalação;
- não altere vinte coisas antes de testar;
- não diga “100% funcionando” apenas porque compilou;
- não apague créditos ou histórico herdado;
- não copie código externo sem verificar origem e licença;
- não use `git push --force` na `main` para consertar um erro;
- não rode comandos destrutivos de Git sem entender o que será apagado.

---

# O que é a `main`?

`main` é a linha principal do Ascension.

Nossa regra é manter mudanças rastreáveis e reversíveis. Isso permite experimentar sem perder a capacidade de descobrir exatamente qual alteração causou um problema.

---

# Pastas explicadas como se fosse um mapa

```text
goldeneye-pc-port/
│
├── src/              o jogo reconstruído
├── include/          definições usadas pelo código
├── port/             ponte entre o GoldenEye e o PC
│   ├── src/          input, vídeo, áudio, config, arquivos etc.
│   └── fast3d/       parte importante da renderização
├── tools_pc/         conversores/preparadores para PC
├── scripts/          automações auxiliares
├── assets/           estrutura de assets do projeto
├── data/             dados locais de execução; ROM nunca vai para o Git
├── docs/             manuais e pesquisa técnica
├── CMakeLists.txt    regras da compilação CMake
└── build-pc.sh       comando principal para construir a versão PC
```

Em linguagem simples:

- `src/` = **o jogo**;
- `port/` = **a ponte para o computador**;
- `tools_pc/` = **ferramentas de preparação**;
- `docs/` = **manual e conhecimento**;
- `build-pc/` = **resultado gerado pela compilação**.

---

# Sou completamente iniciante. O que aprendo primeiro?

Nesta ordem:

1. `git status`;
2. `git diff`;
3. compilar com `./build-pc.sh ntsc-final`;
4. abrir e testar o jogo;
5. criar uma branch;
6. fazer um commit;
7. usar `git revert`;
8. depois estudar o subsistema que quer alterar.

Não tente aprender Git, C, C++, CMake, SDL, OpenGL, engenharia reversa e Nintendo 64 ao mesmo tempo.

---

# Documentação para quando você quiser aprofundar

- [`docs/ASCENSION.md`](docs/ASCENSION.md) — princípios do Ascension.
- [`ROADMAP_ASCENSION.md`](ROADMAP_ASCENSION.md) — direção futura.
- [`docs/PROVENANCE.md`](docs/PROVENANCE.md) — regras para conhecimento/código externo.
- [`docs/building.md`](docs/building.md) — compilação e preparação de dados em nível técnico.
- [`docs/internals.md`](docs/internals.md) — funcionamento interno.
- [`docs/porting-notes.md`](docs/porting-notes.md) — problemas técnicos e conhecimento acumulado.
- [`docs/dev/`](docs/dev/) — registros de desenvolvimento, testes e investigações.

Você não precisa ler tudo. **Primeiro faça o jogo compilar. Depois escolha uma mudança pequena.**

---

# Origem, créditos e licença

Ascension não começou do zero. O código tem uma história importante no ecossistema de decompilação e ports de GoldenEye 007. O histórico Git, autores, créditos, notices e licenças aplicáveis devem continuar preservados.

Independência significa tomar nossas próprias decisões de engenharia; não significa reivindicar como nosso o trabalho criado por outras pessoas.

Antes de redistribuir ou importar código externo, leia [`NOTICE`](NOTICE), [`LICENSE`](LICENSE), [`CITATION.cff`](CITATION.cff) e [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

## Regra final

**Mudou uma coisa → compile → teste → confira `git diff` → faça um commit.**

Se quebrar, encontre a mudança responsável e reverta somente ela. É assim que o Ascension cresce sem virar uma bagunça.