# Montar a Gazeta do Povo Revista com um script

O `montar_revista.py` lê os HTMLs das 7 matérias, usa a revista anterior como modelo
e gera uma revista nova em `.docx`, pronta para subir no Google Docs.

## 1. Instalar (uma vez só)

No terminal do VS Code:

    pip install lxml beautifulsoup4 pillow

Opcional, só para calcular as páginas do índice: LibreOffice e `pdftotext` instalados.

## 2. Preparar a pasta

    revista/
      montar_revista.py
      modelo.docx            <- a revista da edição anterior
      htmls/
        materia1.html        <- editorial
        materia2.html        <- opinião
        materia3.html        <- opinião
        materia4.html        <- reportagem
        materia5.html        <- reportagem
        materia6.html        <- reportagem
        materia7.html        <- reportagem

A ordem importa: é a ordem em que as matérias aparecem na revista.
Se um arquivo estiver no tipo errado (por exemplo, reportagem no lugar de opinião),
o script avisa.

## 3. Rodar

    python montar_revista.py --html htmls --modelo modelo.docx --saida revista_205.docx

Para calcular os números do índice automaticamente:

    python montar_revista.py --html htmls --modelo modelo.docx --saida revista_205.docx --calcular-paginas

Ou, se você já sabe as páginas:

    python montar_revista.py --html htmls --modelo modelo.docx --saida revista_205.docx --paginas 4,10,19,24,38,53,61

## 4. Fotos

O script procura primeiro uma pasta de fotos (`--imagens fotos`). Se não achar, tenta
baixar do endereço que está no HTML. Nomes que ele procura na pasta:

    materia1.jpg ... materia7.jpg       foto principal de cada matéria
    materia2_autor.jpg  materia3_autor.jpg   foto do autor (colunas de opinião)
    materia7_img1.jpg  materia7_img2.jpg     fotos no meio do texto (na ordem em que aparecem)

Se alguma foto não for encontrada nem baixada, o script avisa e deixa a foto antiga do modelo.
Confira esses avisos antes de usar a revista.

## 5. O que ele joga fora

- Blocos "VEJA TAMBÉM" e "Leia mais".
- Parágrafos que são só convite ou link (por exemplo, "WhatsApp: entre no grupo...").
- Frases no fim do parágrafo como "Confira outros textos da série neste link."
- Links no meio das frases: a palavra fica, o link some.

Tudo que foi descartado aparece na tela, em linhas que começam com "descartado:".

## 6. Revisar antes de montar (opcional)

Toda vez que roda, o script salva um arquivo `revista_205_conteudo.json` com o texto lido.
Você pode abrir esse arquivo, corrigir um título ou apagar um parágrafo, e montar de novo
sem ler os HTMLs:

    python montar_revista.py --json revista_205_conteudo.json --modelo modelo.docx --saida revista_205.docx

## 7. O que continua à mão

- **"Para se aprofundar"**: essa lista, no fim da revista, fica como está no modelo.
- **Índice**: o texto é atualizado sempre. Os números só mudam com `--paginas` ou `--calcular-paginas`.
  A conta do LibreOffice é muito próxima da revista final, mas vale conferir no Google Docs.
- **Listas com marcadores** viram "•" simples (no modelo, as listas eram numeradas).
- Abra o resultado no Google Docs e passe o olho nas páginas de abertura de cada matéria.

## Como o script funciona, por partes

- `extrair_materia`: tenta descobrir o que é título, autor, legenda e texto em cada HTML.
  Para isso, procura as marcações do site (por exemplo, o bloco `postBodyContainer` é o texto).
- `eh_descartavel` e `tirar_chamada_final`: tentam descobrir o que é propaganda dentro do texto.
  Para isso, olham se o parágrafo começa com "Leia", "Veja", "Confira" ou se é quase só link.
- `achar_slots`: tenta descobrir onde cada matéria começa e termina no modelo.
  Para isso, usa os "Voltar ao índice" como marcos.
- `montar_materia`: troca título, legenda, foto e texto de uma matéria.
  Para isso, copia parágrafos de exemplo do próprio modelo, então a formatação se mantém.
- Fundo cinza das colunas de opinião: o script coloca o fundo em todos os parágrafos,
  assim ele cobre as páginas, não importa quanto texto tenha.
