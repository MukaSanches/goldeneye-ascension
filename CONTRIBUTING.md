# Contribuindo

Obrigado pelo interesse em contribuir. Este é um projeto comunitário em desenvolvimento; issues e pull requests são bem-vindos, mas leia primeiro as regras abaixo. Elas existem para preservar a fidelidade ao jogo original e reduzir regressões.

## Regras fundamentais

1. **A decompilação não é alterada por conveniência do port.** Tudo em `src/` e `include/` é tratado como referência do jogo original e deve permanecer semanticamente fiel. `Makefile`, `tools/`, `rsp/` e `ld/` pertencem ao build de Nintendo 64 e não devem ser modificados para resolver problemas exclusivos do PC. Se o código do PC parecer exigir uma mudança de comportamento no jogo, pare e investigue primeiro se a correção pertence a `port/`.

2. **Exceção estreita para ABI/layout.** A transição de 32 para 64 bits força uma pequena classe de ajustes mecânicos e sem mudança de semântica em estruturas serializadas pela ROM — por exemplo, manter um endereço embutido como `u32` e convertê-lo para ponteiro real apenas no ponto de uso. Essas alterações são permitidas somente quando inevitáveis, devem ser protegidas por `#ifdef PORT`, não podem alterar comportamento e precisam ser documentadas. Consulte `docs/porting-notes.md` para os padrões já catalogados.

3. **As macros de região devem espelhar o Makefile.** `CMakeLists.txt` e seu conjunto `REGION_DEFS` precisam corresponder exatamente às macros por região definidas no `Makefile` do build de N64. Divergências podem causar caminhos de código diferentes e falhas de link difíceis de diagnosticar.

4. **Verifique antes de enviar.** Qualquer alteração que afete build ou execução precisa, no mínimo, de configuração + compilação limpa para `ntsc-final` e de uma execução sem crash de pelo menos uma fase. Um exemplo de teste rápido é:

   ```sh
   ./build-pc.sh ntsc-final
   ./build-pc/ge007.x86_64 -level_09
   ```

   No Windows, o executável terá extensão `.exe`.

## Estilo de código

- C/C++ segue `.clang-format` e `.editorconfig` na raiz do repositório. Também respeite o estilo já usado ao redor do trecho alterado.
- A camada de port usa C11 / C++17, SDL2 + OpenGL e deve evitar dependências novas sem necessidade real.
- Mantenha commits focados. Explique **por que** a mudança é necessária, não apenas **o que** foi alterado.
- Não misture correções funcionais, reorganizações grandes e mudanças de documentação no mesmo commit sem motivo claro.

## Fluxo recomendado

Antes de editar:

```sh
git switch main
git pull
git switch -c melhoria/minha-alteracao
```

Depois de alterar:

```sh
git status
git diff
./build-pc.sh ntsc-final
```

Se a mudança afetar comportamento, gráficos, áudio, input ou configuração, teste manualmente a área tocada no jogo antes de abrir o Pull Request.

## O que incluir no Pull Request

Explique de forma objetiva:

- qual problema existe;
- qual é a causa conhecida ou hipótese técnica;
- o que foi alterado;
- quais arquivos foram tocados;
- como a alteração foi testada;
- como outra pessoa pode reproduzir o teste;
- riscos, limitações ou validações que ainda faltam.

Se você não conseguiu validar alguma parte, diga isso claramente. “Compilou” e “funcionou em jogo” não significam a mesma coisa.

## Onde procurar antes de começar

- `README.md` — visão geral, início rápido e estado público do projeto.
- `docs/GUIA-INICIANTE.md` — entrada para quem ainda não conhece a estrutura do repositório.
- `docs/internals.md` — arquitetura e divisão dos subsistemas.
- `docs/porting-notes.md` — classes recorrentes de bugs do N64 para PC; consulte antes de investigar um crash conhecido.
- `docs/dev/` — registros técnicos, investigações, matrizes de teste e estado por área.
- `ROADMAP_ASCENSION.md` — direção planejada do Ascension.

## Alterações de alto risco

Mudanças em gameplay, renderer, input, áudio, assets, localização, build ou formatos de dados devem ser tratadas com mais cautela. Quando não houver evidência forte e testes suficientes, prefira abrir uma issue, registrar a análise ou preparar uma branch experimental em vez de integrar diretamente.

Nunca redistribua ROMs, assets proprietários extraídos ou material comercial protegido apenas para facilitar instalação ou teste.

## Créditos e origem

O Ascension deriva de uma longa cadeia de decompilação, pesquisa e portabilidade. Preserve autoria, histórico, avisos e licenças herdados. Código ou conhecimento importado de outro projeto deve ter origem e licença verificadas antes de ser incorporado.

Consulte `NOTICE`, `LICENSE`, `CITATION.cff` e `docs/PROVENANCE.md` quando a contribuição envolver código externo, documentação derivada ou redistribuição.