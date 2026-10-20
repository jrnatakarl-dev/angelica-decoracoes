# Angélica Casa

Loja web com interface Vue 3 compilada pelo Vite, API em Python e banco de dados SQLite.

## Requisitos

- Python 3.11 ou superior
- Node.js 20.19 ou superior e npm
- Navegador moderno
- Conexão à internet na primeira instalação das dependências e para carregar fontes e imagens externas

## Executar localmente

Instale as dependências do front-end uma vez:

```bash
npm install
npm run dev
```

Em outro terminal, inicie a API e o banco:

```bash
python3 -m server.app
```

Abra <http://127.0.0.1:5173>. O Vite encaminha `/api` para o servidor Python em `127.0.0.1:8000`. A base `data/store.sqlite3` é criada automaticamente e recebe o catálogo inicial na primeira execução.

Para gerar e servir a versão de produção local:

```bash
npm run build
python3 -m server.app
```

O servidor Python publica os arquivos compilados de `dist/` e a API na mesma origem. Não abra `index.html` diretamente.

## Administrador

Crie uma conta administrativa pelo terminal. A senha é solicitada sem aparecer na tela e deve ter pelo menos 10 caracteres:

```bash
python3 -m server.manage create-admin admin@seudominio.com
```

Depois entre na área Painel da loja. Cadastros feitos na interface pública recebem somente o papel de cliente.

## Fotos dos produtos

Use fotos próprias ou arquivos fornecidos pelo fabricante com autorização de uso. Evite salvar imagens aleatórias de buscadores: além da licença, elas podem mostrar um modelo ou cor diferentes do que será vendido. Prefira JPEG ou PNG exportado da foto original; enquadramento vertical próximo de 4:5 funciona bem nos cards. A foto principal deve mostrar o produto instalado e as imagens extras devem mostrar detalhes ou outros ângulos.

Instale a dependência opcional de tratamento de imagens:

```bash
python3 -m pip install -r requirements-images.txt
```

O importador corrige a orientação EXIF, limita a imagem a 2000 px, converte para WebP otimizado, grava em `public/assets/images/products/` e atualiza a galeria do produto em `public/assets/data/catalog.json`. Passe uma imagem principal e, se quiser, até cinco fotos de detalhe:

```bash
python3 -m scripts.import_product_images --product-id 1 \
  --main "$HOME/Downloads/persiana-aluminio.jpg" \
  --gallery "$HOME/Downloads/persiana-aluminio-detalhe.jpg" "$HOME/Downloads/persiana-aluminio-lateral.jpg"
```

IDs do catálogo: 1 Horizontal de Alumínio; 2 Horizontal de Madeira Sintética; 3 Vertical de Tecido; 4 Double Vision; 5 Painel Europeu; 6 Rolô Blackout; 7 Rolô Tela Solar; 8 Rolô Translúcida; 9 Romana Blackout; 10 Romana Translúcida; 11 Persiana de Teto. Depois de importar, reinicie o servidor: ele sincroniza as referências de imagem com SQLite sem alterar preços nem estoque. Em desenvolvimento, reinicie também o Vite se o arquivo JSON não atualizar.

## API principal

- `GET /api/health` e `GET /api/catalog`
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me`
- `POST /api/orders`, `GET /api/orders`, `GET /api/orders/track/{numero}`
- `GET /api/admin/orders`, `PATCH /api/admin/orders/{numero}`
- `GET /api/admin/products`, `PATCH /api/admin/products/{id}`
- `POST /api/contact`, `POST /api/newsletter`

## Dados e publicação

SQLite persiste produtos, usuários, sessões, pedidos, contatos e inscrições. Configure `APP_DATA_DIR` para manter o banco fora da pasta publicada e `HOST`/`PORT` para ajustar a escuta. Faça cópias de segurança do arquivo SQLite e restrinja o acesso ao servidor e à pasta de dados.

O catálogo inicial em `public/assets/data/catalog.json` contém conteúdo de exemplo. Antes da publicação, substitua textos, imagens, preços, estoque e prazos por informações verificadas da loja. O cálculo de frete do checkout é uma estimativa, não uma cotação dos Correios ou de uma transportadora.

O pagamento ainda não é processado por um gateway: as opções de Pix, cartão e boleto são registradas como método escolhido, e pedidos começam como **Aguardando pagamento**. Antes de vender, conecte um provedor de pagamentos com confirmação de status por webhook e publique atrás de HTTPS. Em HTTPS, configure `APP_SECURE_COOKIE=1`. O servidor embutido é voltado a desenvolvimento; em produção, use um servidor WSGI/ASGI ou proxy adequado e limite tentativas de autenticação.
