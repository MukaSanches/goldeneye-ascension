# Support

Use este documento para decidir onde pedir ajuda sem transformar dúvidas de configuração em bugs difíceis de reproduzir.

## Antes de abrir uma issue

1. Atualize o repositório com `git pull --ff-only`.
2. Confirme que está usando o terminal e as dependências indicadas em `docs/building.md`.
3. Rode novamente o comando que falhou e copie o erro completo.
4. Procure por issues abertas com a mesma mensagem.
5. Consulte `docs/PROJECT_STATUS.md` para saber se a área ainda é experimental.

## Informação útil para diagnóstico

Sempre que possível, informe:

```text
OS:
Ambiente/toolchain:
Commit: git rev-parse --short HEAD
ROMID/região:
Comando executado:
Etapa que falhou:
```

Para crash em runtime, inclua `ge007.crash.log` ou uma stack trace quando disponível. Para problema visual, uma screenshot costuma ser mais útil que uma descrição longa.

## O que não enviar

Não publique ou anexe:

- ROM;
- dumps contendo conteúdo comercial do jogo;
- assets proprietários extraídos;
- arquivos cuja licença não permita redistribuição;
- credenciais, tokens ou caminhos que exponham dados pessoais desnecessários.

## Bug ou dúvida?

Abra um **bug report** quando você consegue descrever um comportamento reproduzível que parece incorreto no projeto.

Use uma discussão normal em issue somente quando a dúvida exigir análise do código ou documentação e não houver outro canal disponível. Para propostas de produto, use o template **Feature request**.

## Segurança

Vulnerabilidades não devem ser publicadas em issue. Siga `.github/SECURITY.md` e use GitHub Private Vulnerability Reporting.

## Limites de suporte

Ascension é desenvolvido com Windows/MSYS2 como caminho principal. Outras plataformas podem receber correções, mas o nível de validação pode ser diferente.

O projeto também não presta suporte para obtenção de ROM, distribuição de conteúdo comercial ou configuração de cópias adquiridas por meios não autorizados.