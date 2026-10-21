# Angélica Casa

Loja com interface Vue 3, API Python, SQLite e Checkout Pro do Mercado Pago. As credenciais de pagamento ficam no servidor; o navegador nunca recebe o access token. A confirmação do pedido depende da consulta autenticada do pagamento e de um webhook com assinatura verificada.

## Desenvolvimento local

Requisitos: Python 3.11+, Node.js 20.19+ e npm.

```bash
npm install
npm run dev
```

Em outro terminal:

```bash
python3 -m server.app
```

Abra <http://127.0.0.1:5173>. O Vite encaminha `/api` ao servidor Python em `127.0.0.1:8000`. O banco local é criado em `data/store.sqlite3`. Sem as configurações do Mercado Pago, a API não cria pedidos cobrados e o checkout informa que está indisponível.

Para criar o primeiro administrador local:

```bash
python3 -m server.manage create-admin admin@seudominio.com
```

## Publicação em VPS (Docker e HTTPS)

O Compose monta a aplicação e o Caddy. O Caddy gerencia HTTPS automaticamente; a porta 8000 da aplicação não fica exposta à internet.

1. Use um VPS com Docker, aponte o DNS do domínio para o IP público do servidor e libere TCP 80/443. O Caddy solicita e renova HTTPS automaticamente depois que o DNS estiver correto.
2. Envie o repositório ao VPS e execute os comandos na pasta do projeto.
3. Copie `.env.example` para `.env`, preencha o domínio e as credenciais reais, proteja o arquivo (`chmod 600 .env`) e nunca o envie ao Git. Mantenha `STORE_PICKUP_ENABLED=0`, a menos que a retirada esteja disponível e o endereço completo esteja definido.
4. No Mercado Pago, configure o webhook para `https://SEU_DOMINIO/api/payments/mercadopago/webhook` e copie o segredo gerado para `MP_WEBHOOK_SECRET`.
5. Inicie a publicação:

```bash
docker compose up --build -d
docker compose exec app python -m server.manage create-admin admin@seudominio.com
```

Use primeiro credenciais de teste do Mercado Pago (`TEST-...`) e simule aprovação, recusa e pagamento pendente. Depois de validar o webhook e o fluxo, substitua pelas credenciais de produção. O serviço só aceita pedidos quando há access token, segredo de webhook e URL pública HTTPS. A retirada só é oferecida quando explicitamente habilitada com endereço no servidor, e o backend exige o aceite das políticas.

Checkout Pro usa a API oficial de preferências e redireciona o comprador para o Mercado Pago. O retorno do navegador não aprova o pedido: a aprovação só ocorre após o servidor verificar a assinatura do webhook, consultar o pagamento no Mercado Pago e conferir referência, moeda e valor total.

Documentação oficial: [criar preferência](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/create-payment-preference), [webhooks e assinatura](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications).

## Imagens e catálogo

As 11 fotos recebidas foram associadas aos respectivos produtos, convertidas para WebP e incluídas localmente no projeto. A loja confirmou autorização comercial para o uso das imagens. Os preços, estoque, cores, descrições, medidas aceitas, embalagens e prazos do catálogo ainda precisam ser conferidos com os dados reais da loja.

Para importar fotos próprias ou autorizadas, instale o utilitário opcional:

```bash
python3 -m pip install -r requirements-images.txt
python3 -m scripts.import_product_images --product-id 1 \
  --main "$HOME/Downloads/persiana-aluminio.jpg" \
  --gallery "$HOME/Downloads/persiana-aluminio-detalhe.jpg"
```

O importador normaliza orientação, limita a dimensão, converte para WebP e atualiza a galeria local. Consulte os IDs no `public/assets/data/catalog.json`.

## Operação e dados

- O painel administrativo permite acompanhar pedidos, atualizar status, preço e estoque, ler mensagens de contato e consultar inscritos na newsletter.
- Cada pedido é calculado no servidor usando os preços e o estoque do SQLite. O checkout consulta opções de frete em tempo real na API do Melhor Envio quando as credenciais e os dados reais de embalagem estão configurados. Sem isso, só oferece retirada no ateliê.
- A exclusão da conta remove sessões, cadastro, mensagens e inscrição associadas. Os pedidos permanecem anonimizados para manter o histórico comercial. Revise a política de privacidade e retenção com orientação adequada à operação da loja.
- O controle de tentativas é local ao processo. Mantenha uma única instância da aplicação ou configure também limites no proxy antes de escalar horizontalmente.
- O SQLite é adequado para esta implantação de instância única. O volume `store-data` deve permanecer persistente. Para múltiplas instâncias, migre para banco gerenciado antes de escalar.

### Backup e restauração

Crie uma cópia consistente (armazenada no volume persistente):

```bash
docker compose exec -T app python -m scripts.backup_database
```

Restaure com a aplicação parada e o nome de uma cópia existente:

```bash
docker compose stop app
docker compose run --rm --entrypoint python app -m scripts.backup_database restore /data/backups/store-AAAAMMDDTHHMMSSZ.sqlite3
docker compose up -d
```

Copie backups para outro local seguro regularmente; backup guardado apenas no mesmo servidor não protege contra perda do servidor ou do volume.

## Preparação comercial ainda necessária

Antes de aceitar vendas, carregue fotos corretas e informações comerciais verificadas, configure os dados de envio e token OAuth do Melhor Envio, confirme as dimensões e pesos dos produtos já embalados, revise as políticas de troca/garantia/privacidade e faça compras de teste até validar os webhooks na conta Mercado Pago. O arquivo `.env.example` contém apenas valores de exemplo, não credenciais válidas.

### Melhor Envio

Crie um aplicativo no painel de integrações do Melhor Envio, autorize a conta e coloque o token OAuth em `ME_ACCESS_TOKEN`. O token usado neste projeto é configurado manualmente no servidor: renove-o e atualize `.env` antes de expirar (access token: 30 dias; refresh token: 45 dias). Informe o CEP remetente, peso e dimensões embaladas corretas, o User-Agent registrado e os dados cadastrais completos do remetente (`ME_FROM_*`). A largura e altura escolhidas pelo cliente são usadas como dimensões do produto na cotação; confirme que o modelo representa de verdade os pacotes enviados antes de vender. Mantenha `ME_SANDBOX=1` durante a homologação; altere para `0` somente com credenciais de produção. [Documentação de autenticação](https://docs.melhorenvio.com.br/docs/autenticacao-1).

O checkout recalcula a cotação no servidor antes de criar o pagamento, para não confiar em preço de frete enviado pelo navegador. Depois da aprovação, o painel administrativo conduz as etapas de preparar, comprar, gerar e imprimir a etiqueta. A compra exige saldo na carteira Melhor Envio, CPF/telefone do destinatário e chave NF-e de 44 dígitos. A ação de compra pede confirmação porque debita a carteira. O Melhor Envio orienta informar os pacotes devolvidos pela cotação ao inserir o frete no carrinho; para envios comerciais, também exige a chave da NF-e. [Inserção no carrinho](https://docs.melhorenvio.com.br/reference/inserir-fretes-no-carrinho) · [Compra](https://docs.melhorenvio.com.br/reference/compra-de-fretes-1) · [Geração](https://docs.melhorenvio.com.br/reference/geracao-de-etiquetas) · [Impressão](https://docs.melhorenvio.com.br/reference/impressao-de-etiquetas).

Se a comunicação cair durante compra ou geração, o pedido fica marcado como etapa iniciada. Confira o painel do Melhor Envio antes de qualquer repetição; isso evita cobrar ou gerar a etiqueta duas vezes. O link privado de impressão fica visível apenas no backoffice.
