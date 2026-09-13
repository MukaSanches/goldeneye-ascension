# Ascension Learning Series

A **Ascension Learning Series** organiza o conhecimento do projeto em uma trilha editorial em PDF. A colecao cobre o filme de 1995, o jogo de Nintendo 64, fundamentos de gameplay, multiplayer, design, historia de desenvolvimento, build do port, configuracao, Git/GitHub, testes, localizacao PT-BR e o roadmap do Ascension.

Os PDFs sao gerados de forma reproduzivel a partir de `data/*.json` e `build_courses.py`. O pipeline nao incorpora ROM, assets extraidos do jogo ou fontes proprietarias.

## Catalogo

- [Catalogo geral da colecao](pdf/00_CATALOGO_ASCENSION_LEARNING_SERIES.pdf)

## Cursos

| # | Curso | Trilha |
|---:|---|---|
| 01 | [GoldenEye (1995): cinema, contexto e linguagem](pdf/01_goldeneye_1995_cinema_contexto.pdf) | Cinema |
| 02 | [James Bond e a transicao para os anos 1990](pdf/02_bond_e_os_anos_90.pdf) | Cinema / Historia |
| 03 | [Do filme ao jogo: anatomia de uma adaptacao interativa](pdf/03_do_filme_ao_jogo.pdf) | Design |
| 04 | [GoldenEye 007 no Nintendo 64: historia, desenvolvimento e legado](pdf/04_historia_goldeneye_007_n64.pdf) | Historia do jogo |
| 05 | [Como jogar GoldenEye 007: fundamentos do agente](pdf/05_como_jogar_fundamentos.pdf) | Gameplay |
| 06 | [Campanha, objetivos e dificuldade](pdf/06_campanha_objetivos_dificuldade.pdf) | Gameplay / Design |
| 07 | [Combate, mira e furtividade](pdf/07_combate_mira_furtividade.pdf) | Gameplay |
| 08 | [Multiplayer classico: regras, leitura e estrategia](pdf/08_multiplayer_classico.pdf) | Multiplayer |
| 09 | [Level design, IA e sensacao de infiltracao](pdf/09_level_design_ia.pdf) | Game Design |
| 10 | [Nintendo 64, controle e restricoes que viraram design](pdf/10_tecnologia_n64_design.pdf) | Tecnologia / Design |
| 11 | [Bastidores da Rare: equipe, metodo e experimentacao](pdf/11_bastidores_rare.pdf) | Historia do desenvolvimento |
| 12 | [Ascension: visao, identidade e principios](pdf/12_ascension_visao_identidade.pdf) | Projeto Ascension |
| 13 | [Ascension para iniciantes: instalar, compilar e executar](pdf/13_ascension_iniciante_instalar_compilar.pdf) | Projeto Ascension / Build |
| 14 | [MSYS2, MinGW64, CMake e pipeline de build](pdf/14_msys2_cmake_pipeline_build.pdf) | Engenharia |
| 15 | [ROM, assets e sidecars: entendendo o pipeline](pdf/15_rom_assets_sidecars_pipeline.pdf) | Engenharia / Dados |
| 16 | [Configuracoes do Ascension e ge007.ini](pdf/16_configuracoes_ge007_ini.pdf) | Configuracao |
| 17 | [Git e GitHub no Ascension: trabalhar sem perder o controle](pdf/17_git_github_ascension.pdf) | Colaboracao |
| 18 | [Testes, regressao e qualidade](pdf/18_testes_regressao_qualidade.pdf) | QA / Engenharia |
| 19 | [Localizacao PT-BR: engenharia, linguagem e QA](pdf/19_localizacao_ptbr_engenharia_texto.pdf) | Localizacao |
| 20 | [Roadmap, releases e comunidade ate 1.0](pdf/20_roadmap_releases_comunidade.pdf) | Projeto Ascension |

## Estrutura editorial

Cada curso possui seis paginas: capa, objetivos, dois blocos de conteudo, laboratorio e revisao com referencias. O objetivo nao e substituir documentacao tecnica: nos cursos de engenharia, o estado atual do codigo e dos documentos do repositorio continua sendo a fonte de verdade.

## Gerar localmente

```sh
python -m pip install reportlab==4.2.5
python docs/cursos/build_courses.py
```

Os arquivos sao escritos em `docs/cursos/pdf/`.

## Atualizacao

Edite `data/*.json` para revisar conteudo, objetivos, exercicios ou referencias. Edite `build_courses.py` apenas quando a identidade visual, a estrutura das paginas ou o mecanismo de geracao precisar mudar. O workflow `courses.yml` regenera a colecao quando esses arquivos sao alterados.

## Politica de conteudo

A serie e material educacional de um projeto de preservacao e engenharia. Ela nao distribui ROM comercial, assets proprietarios extraidos, imagens de jogo nao autorizadas ou fontes proprietarias. Marcas e personagens citados pertencem aos respectivos titulares.
