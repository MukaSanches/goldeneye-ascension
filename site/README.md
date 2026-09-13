# Site oficial do Ascension

Este diretório contém o site estático oficial do projeto.

## Publicação recomendada no GitHub Pages

Configure o GitHub Pages para publicar a partir de uma GitHub Action ou de uma branch dedicada que use o conteúdo deste diretório como raiz do site.

O site não depende de framework, Node.js ou serviço externo: é HTML + CSS estático. Isso reduz manutenção e torna a publicação simples.

## Arquivos

- `index.html`: conteúdo e estrutura.
- `assets/style.css`: identidade visual e responsividade.

As imagens e o GIF são reutilizados da documentação existente do repositório, evitando duplicação de arquivos.

## Teste local

Na raiz do repositório:

```sh
python -m http.server 8000
```

Abra `http://localhost:8000/site/` no navegador.

## Atenção sobre GitHub Pages

Ao publicar somente a pasta `site/` como raiz isolada, caminhos `../docs/...` não existirão no artefato final. O fluxo de publicação deve incluir `site/` e as mídias referenciadas em `docs/`, ou copiar as mídias necessárias para o artefato de Pages.
