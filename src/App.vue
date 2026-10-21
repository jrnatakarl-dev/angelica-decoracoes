<script>
import { inject, onMounted } from 'vue';
import { storeKey } from './storeKey.js';
import StoreHeader from './components/StoreHeader.vue';
import StoreFooter from './components/StoreFooter.vue';
import SearchOverlay from './components/SearchOverlay.vue';
import ProductModal from './components/ProductModal.vue';
import CartDrawer from './components/CartDrawer.vue';

export default {
  name: 'App',
  components: { StoreHeader, StoreFooter, SearchOverlay, ProductModal, CartDrawer },
  setup() {
    const store = inject(storeKey);
    onMounted(() => store.init());
    return store;
  },
};
</script>

<template>
  <div class="bg-paper font-sans text-ink antialiased" v-cloak @keydown.escape.window="closeOverlays()" @hashchange.window="readHash()">
    <StoreHeader />
<!-- HOME -->
  <main v-show="view==='home'" v-cloak>
    <section id="inicio" class="mx-auto grid max-w-[1440px] gap-5 px-3 py-3 sm:px-5 lg:grid-cols-[.88fr_1.12fr] lg:gap-8 lg:px-8 lg:py-8">
      <div class="flex min-h-[410px] flex-col justify-center bg-sand px-7 py-10 sm:px-12 lg:min-h-[610px] lg:px-16">
        <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay sm:text-xs">A luz muda tudo</p>
        <h1 class="mt-5 max-w-xl font-serif text-5xl leading-[1.05] sm:text-6xl xl:text-7xl">A casa sente quando a luz encontra o seu lugar.</h1>
          <p class="mt-6 max-w-md text-sm leading-7 text-ink/65 sm:text-base">Escolha o modelo, informe as medidas e personalize a cor e a instalação. Consulte as opções de entrega do Melhor Envio pelo seu CEP.</p>
        <div class="mt-8 flex flex-wrap gap-3">
          <a href="#loja" class="bg-clay px-6 py-3.5 text-xs font-bold uppercase tracking-[.12em] text-white transition hover:bg-ink">Encontre a sua</a>
          <a href="#guia" class="border border-ink/25 px-6 py-3.5 text-xs font-bold uppercase tracking-[.12em] transition hover:border-clay hover:text-clay">Como medir</a>
        </div>
        <div class="mt-12 flex items-center gap-4 border-t border-ink/15 pt-5">
          <div class="flex -space-x-2">
            <span class="grid h-8 w-8 place-items-center rounded-full border-2 border-sand bg-olive text-xs text-white">A</span>
            <span class="grid h-8 w-8 place-items-center rounded-full border-2 border-sand bg-clay text-xs text-white">M</span>
            <span class="grid h-8 w-8 place-items-center rounded-full border-2 border-sand bg-ink text-xs text-white">C</span>
          </div>
          <p class="text-xs leading-5 text-ink/65"><b class="text-ink">Feita para a sua janela</b><br>Escolha medidas, cor e instalação.</p>
        </div>
      </div>
      <div class="relative min-h-[390px] overflow-hidden bg-[#d8d2c5] lg:min-h-[610px]">
        <img class="absolute inset-0 h-full w-full object-cover" src="https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1600&q=85" alt="Sala com luz natural e janelas amplas">
        <div class="absolute inset-0 bg-gradient-to-t from-ink/35 via-transparent to-transparent"></div>
        <div class="absolute bottom-5 left-5 max-w-xs border border-white/60 bg-paper/90 p-4 backdrop-blur-sm sm:bottom-8 sm:left-8 sm:p-5">
          <span class="text-[9px] font-bold uppercase tracking-[.2em] text-clay">Coleção essencial</span>
          <p class="mt-1 font-serif text-2xl">Menos excesso. Mais casa.</p>
        </div>
        <span class="absolute right-5 top-5 rounded-full bg-paper/90 px-4 py-2 text-[9px] font-bold uppercase tracking-[.18em]">Sob medida</span>
      </div>
    </section>

    <section class="border-y border-ink/10 bg-white/50">
      <div class="mx-auto grid max-w-7xl grid-cols-2 gap-y-5 px-5 py-6 sm:grid-cols-4 lg:px-8">
        <div class="flex items-center gap-3"><span class="font-serif text-2xl text-clay">01</span><p class="text-[10px] uppercase leading-4 tracking-[.12em]">Feito na<br>sua medida</p></div>
        <div class="flex items-center gap-3"><span class="font-serif text-2xl text-clay">02</span><p class="text-[10px] uppercase leading-4 tracking-[.12em]">Pedido salvo<br>com segurança</p></div>
        <div class="flex items-center gap-3"><span class="font-serif text-2xl text-clay">03</span><p class="text-[10px] uppercase leading-4 tracking-[.12em]">Opções reais de<br>frete por CEP</p></div>
        <div class="flex items-center gap-3"><span class="font-serif text-2xl text-clay">04</span><p class="text-[10px] uppercase leading-4 tracking-[.12em]">Histórico de<br>pedidos online</p></div>
      </div>
    </section>

    <section id="colecoes" class="mx-auto max-w-7xl px-4 py-16 sm:px-8 sm:py-24">
      <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Explore por estilo</p>
          <h2 class="mt-3 font-serif text-4xl sm:text-5xl">Vista cada janela.</h2>
        </div>
        <a href="#loja" class="border-b border-ink pb-1 text-xs font-bold uppercase tracking-wider">Ver todas as peças ↗</a>
      </div>
      <div class="grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4">
        <template v-for="c in categories" :key="c.id">
          <button @click="setCategory(c.id)" class="group text-left">
            <div class="relative aspect-[.78] overflow-hidden bg-sand">
              <img :src="c.image" :alt="c.name" @error="fallbackImage($event)" class="h-full w-full object-cover transition duration-700 group-hover:scale-105">
              <div class="absolute inset-0 bg-gradient-to-t from-ink/65 via-transparent to-transparent"></div>
              <div class="absolute bottom-4 left-4 text-white sm:bottom-6 sm:left-6">
                <p class="font-serif text-xl sm:text-2xl" v-text="c.name"></p>
                <span class="mt-1 inline-block text-[9px] uppercase tracking-[.16em] text-white/75" v-text="c.note"></span>
              </div>
              <span class="absolute right-3 top-3 grid h-8 w-8 place-items-center rounded-full bg-paper/90 transition group-hover:bg-clay group-hover:text-white">↗</span>
            </div>
          </button>
        </template>
      </div>
    </section>

    <section id="loja" class="bg-white py-16 sm:py-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-8">
        <div class="mb-9 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Catálogo completo</p>
            <h2 class="mt-3 font-serif text-4xl sm:text-5xl" v-text="shopTitle"></h2>
            <p class="mt-3 max-w-xl text-sm text-ink/60">Onze modelos. Personalize cor, instalação e medidas — o preço é por m², ao vivo.</p>
            <p class="mt-2 max-w-xl text-xs text-ink/50">As fotos marcadas como ilustrativas mostram ambientes de referência; confirme a cor e o acabamento com nossa equipe.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <select v-model="filterLight" class="border border-ink/20 bg-white px-3 py-3 text-xs outline-none">
              <option value="">Controle de luz</option>
              <option value="blackout">Blackout</option>
              <option value="solar">Tela solar</option>
              <option value="translucida">Translúcida</option>
              <option value="ajustavel">Ajustável</option>
            </select>
            <select v-model="sort" class="border border-ink/20 bg-white px-3 py-3 text-xs outline-none">
              <option value="featured">Em destaque</option>
              <option value="low">Menor preço</option>
              <option value="high">Maior preço</option>
            </select>
            <button v-show="hasFilters" @click="clearFilters()" class="border border-ink/20 px-3 text-xs">Limpar</button>
          </div>
        </div>
        <div class="mb-8 flex flex-wrap gap-2">
          <button @click="category='';favoritesOnly=false" class="border px-3 py-2 text-[10px] font-bold uppercase tracking-wider" :class="!category&&!favoritesOnly?'border-clay bg-clay text-white':'border-ink/15'">Todas</button>
          <template v-for="c in categories" :key="'f'+c.id">
            <button @click="category=c.id;favoritesOnly=false" class="border px-3 py-2 text-[10px] font-bold uppercase tracking-wider" :class="category===c.id?'border-clay bg-clay text-white':'border-ink/15'" v-text="c.name"></button>
          </template>
        </div>
        <p v-if="catalogStatus==='loading'" class="mb-6 border border-ink/10 bg-paper p-4 text-sm text-ink/65">Carregando produtos…</p>
        <p v-else-if="catalogStatus==='fallback'" role="status" class="mb-6 border border-amber-700/25 bg-amber-50 p-4 text-sm text-amber-950">Exibindo o catálogo salvo neste site. Sacola, preços atualizados, pedidos e pagamentos dependem da conexão com o servidor da loja.</p>
        <p v-else-if="catalogStatus==='error'" role="alert" class="mb-6 border border-red-700/25 bg-red-50 p-4 text-sm text-red-950">Não foi possível carregar os produtos. Atualize a página ou tente novamente mais tarde.</p>
        <div class="grid grid-cols-1 gap-x-5 gap-y-9 min-[520px]:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <template v-for="p in visibleProducts" :key="p.id">
            <article class="group">
              <div class="relative aspect-[.82] overflow-hidden bg-paper">
                <img :src="p.image" :alt="p.name" loading="lazy" @error="fallbackImage($event)" class="h-full w-full object-cover transition duration-700 group-hover:scale-[1.035]">
                <span v-if="p.image.startsWith('http')" class="absolute bottom-3 right-3 bg-paper/90 px-2 py-1 text-[8px] font-bold uppercase tracking-wider">Imagem ilustrativa</span>
                <span v-show="p.tag" class="absolute left-3 top-3 bg-paper px-3 py-1.5 text-[9px] font-bold uppercase tracking-[.15em]" v-text="p.tag"></span>
                <span v-show="p.stock<=3" class="absolute left-3 bottom-3 bg-ink px-3 py-1.5 text-[9px] font-bold uppercase tracking-[.15em] text-white">Últimas unidades</span>
                <button @click="toggleFavorite(p.id)" class="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-paper/90 text-xl transition hover:bg-clay hover:text-white" :aria-label="favorites.includes(p.id)?'Remover favorito':'Adicionar favorito'" v-text="favorites.includes(p.id)?'♥':'♡'"></button>
                <div class="absolute bottom-3 left-3 right-3 flex gap-2 opacity-0 transition group-hover:opacity-100 max-sm:opacity-100">
                  <button @click="openProduct(p)" class="flex-1 bg-paper/95 py-3 text-[10px] font-bold uppercase tracking-[.15em]">Personalizar</button>
                  <button @click="toggleCompare(p.id)" class="bg-ink px-3 py-3 text-[10px] font-bold uppercase tracking-wider text-white" v-text="compare.includes(p.id)?'−':'＋'"></button>
                </div>
              </div>
              <div class="pt-4">
                <p class="text-[9px] uppercase tracking-[.18em] text-ink/45" v-text="p.kind"></p>
                <div class="mt-1 flex items-start justify-between gap-2">
                  <h3 class="font-serif text-xl" v-text="p.name"></h3>
                  <div class="whitespace-nowrap text-right">
                    <span class="block text-sm font-semibold" v-text="money(p.price)+'/m²'"></span>
                    <span class="text-[9px] text-ink/45">a partir de</span>
                  </div>
                </div>
                <p class="mt-2 line-clamp-2 text-xs leading-5 text-ink/60" v-text="p.description"></p>
                <button @click="openProduct(p)" class="mt-4 w-full border border-ink/20 py-3 text-[10px] font-bold uppercase tracking-[.16em] transition hover:border-clay hover:bg-clay hover:text-white sm:hidden">Escolher medidas</button>
              </div>
            </article>
          </template>
        </div>
        <div v-show="!visibleProducts.length" class="py-16 text-center text-sm text-ink/60">Não encontramos produtos com esse filtro.</div>
      </div>
    </section>

    <section v-show="recent.length" class="mx-auto max-w-7xl px-4 pb-16 sm:px-8">
      <h2 class="font-serif text-3xl">Vistos recentemente</h2>
      <div class="mt-6 flex gap-4 overflow-x-auto pb-2">
        <template v-for="id in recent" :key="'r'+id">
          <button @click="openProduct(byId(id))" class="w-40 shrink-0 text-left">
            <img :src="byId(id)?.image" class="aspect-[.82] w-full object-cover bg-sand" :alt="byId(id)?.name">
            <p class="mt-2 font-serif text-sm" v-text="byId(id)?.name"></p>
          </button>
        </template>
      </div>
    </section>

    <section id="guia" class="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-8 sm:py-24 lg:grid-cols-2 lg:items-center">
      <div class="relative min-h-[400px] overflow-hidden bg-sand">
        <img class="absolute inset-0 h-full w-full object-cover" src="https://images.unsplash.com/photo-1616486029423-aaa4789e8c9a?auto=format&fit=crop&w=1200&q=80" loading="lazy" alt="Ambiente com janela ampla">
        <div class="absolute bottom-5 left-5 max-w-[230px] bg-paper p-5">
          <span class="text-[9px] font-bold uppercase tracking-[.2em] text-clay">Guia simples</span>
          <p class="mt-2 font-serif text-2xl">Trena, janela e alguns minutos.</p>
        </div>
      </div>
      <div>
        <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Antes de escolher</p>
        <h2 class="mt-3 font-serif text-4xl leading-tight sm:text-5xl">A medida certa começa com calma.</h2>
        <p class="mt-5 max-w-lg text-sm leading-7 text-ink/65">Meça a largura em três pontos e use a menor medida. Faça o mesmo na altura. Para instalação fora do vão, some 5 a 10 cm de cada lado.</p>
        <div class="mt-8 space-y-4 border-t border-ink/15 pt-5">
          <div class="flex gap-4"><span class="font-serif text-xl text-clay">01</span><p class="text-sm"><b>Largura</b><span class="mt-1 block text-xs text-ink/55">Topo, meio e base — use a menor.</span></p></div>
          <div class="flex gap-4"><span class="font-serif text-xl text-clay">02</span><p class="text-sm"><b>Altura</b><span class="mt-1 block text-xs text-ink/55">Dois lados e o centro.</span></p></div>
          <div class="flex gap-4"><span class="font-serif text-xl text-clay">03</span><p class="text-sm"><b>Instalação</b><span class="mt-1 block text-xs text-ink/55">Dentro do vão ou cobrindo a parede.</span></p></div>
        </div>
        <a href="#loja" class="mt-8 inline-flex bg-ink px-6 py-4 text-[10px] font-bold uppercase tracking-[.15em] text-white hover:bg-clay">Escolher minha persiana</a>
      </div>
    </section>

    <section id="sobre" class="bg-sand">
      <div class="mx-auto grid max-w-7xl gap-8 px-4 py-14 sm:px-8 sm:py-20 md:grid-cols-3 md:items-center">
        <div class="md:col-span-2">
          <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Angélica Casa</p>
          <h2 class="mt-3 max-w-2xl font-serif text-4xl leading-tight sm:text-5xl">A decoração começa pelo que a luz toca.</h2>
        </div>
        <p class="text-sm leading-7 text-ink/65">Cada persiana é configurada sob medida, com tecido e cor escolhidos por você. Consulte as opções de entrega e instalação disponíveis para a sua região.</p>
      </div>
    </section>

    <section id="faq" class="mx-auto max-w-7xl px-4 py-16 sm:px-8 sm:py-24">
      <div class="mx-auto max-w-2xl text-center">
        <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Perguntas frequentes</p>
        <h2 class="mt-3 font-serif text-4xl">Antes de abrir a janela.</h2>
      </div>
      <div class="mx-auto mt-8 max-w-3xl divide-y divide-ink/15">
        <template v-for="(item,i) in faqs" :key="i">
          <div>
            <button @click="faq=faq===i?-1:i" class="flex w-full items-center justify-between gap-5 py-5 text-left text-sm font-semibold">
              <span v-text="item.q"></span>
              <span class="font-serif text-2xl text-clay" v-text="faq===i?'−':'+'"></span>
            </button>
            <p v-cloak v-show="faq===i" class="max-w-2xl pb-5 text-sm leading-6 text-ink/60" v-text="item.a"></p>
          </div>
        </template>
      </div>
    </section>
  </main>

  <!-- CHECKOUT -->
  <main v-show="view==='checkout'" v-cloak class="mx-auto max-w-6xl px-4 py-10 sm:px-8">
    <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Checkout</p>
    <h1 class="mt-2 font-serif text-4xl">Quase em casa.</h1>
    <div class="mt-6 flex gap-2 text-[10px] font-bold uppercase tracking-wider">
      <span :class="step>=1?'text-clay':''">1 Contato</span><span class="text-ink/30">/</span>
      <span :class="step>=2?'text-clay':''">2 Entrega</span><span class="text-ink/30">/</span>
      <span :class="step>=3?'text-clay':''">3 Frete</span><span class="text-ink/30">/</span>
      <span :class="step>=4?'text-clay':''">4 Pagamento</span>
    </div>
    <div class="mt-8 grid gap-10 lg:grid-cols-[1.2fr_.8fr]">
      <div class="space-y-5">
        <div v-show="step===1" class="space-y-3">
          <label class="block text-[10px] font-bold uppercase tracking-widest">Nome<input v-model="customer.name" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal" placeholder="Nome completo"></label>
          <label class="block text-[10px] font-bold uppercase tracking-widest">E-mail<input type="email" v-model="customer.email" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
          <label class="block text-[10px] font-bold uppercase tracking-widest">WhatsApp<input v-model="customer.phone" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal" placeholder="(11) 99999-0000"></label>
          <label class="block text-[10px] font-bold uppercase tracking-widest">CPF do destinatário
            <input v-model="customer.cpf" inputmode="numeric" maxlength="14" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal" placeholder="000.000.000-00">
            <span class="mt-1 block text-[10px] font-normal normal-case tracking-normal text-ink/50">Necessário para emitir a etiqueta quando escolher entrega.</span>
          </label>
          <p class="text-xs text-ink/55">Entre na sua conta para associar o pedido ao seu histórico. Sem login, o pedido também será salvo.</p>
          <button @click="nextStep(1)" class="bg-ink px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-white">Continuar</button>
        </div>
        <div v-show="step===2" class="space-y-3">
          <label class="block text-[10px] font-bold uppercase tracking-widest">CEP
            <div class="mt-2 flex gap-2">
              <input v-model="customer.cep" @blur="lookupCep()" maxlength="9" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal" placeholder="00000-000">
              <button type="button" @click="lookupCep()" class="border border-ink px-4 text-[10px] font-bold uppercase">Buscar</button>
            </div>
          </label>
          <p v-show="cepStatus" class="text-xs text-ink/55" v-text="cepStatus"></p>
          <div class="grid grid-cols-3 gap-3">
            <label class="col-span-2 text-[10px] font-bold uppercase tracking-widest">Rua<input v-model="customer.street" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
            <label class="text-[10px] font-bold uppercase tracking-widest">Nº<input v-model="customer.number" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
          </div>
          <label class="block text-[10px] font-bold uppercase tracking-widest">Complemento<input v-model="customer.complement" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
          <div class="grid grid-cols-3 gap-3">
            <label class="col-span-2 text-[10px] font-bold uppercase tracking-widest">Bairro<input v-model="customer.neighborhood" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
            <label class="text-[10px] font-bold uppercase tracking-widest">UF<input v-model="customer.uf" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
          </div>
          <label class="block text-[10px] font-bold uppercase tracking-widest">Cidade<input v-model="customer.city" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></label>
          <div class="flex gap-2">
            <button @click="step=1" class="border border-ink/20 px-5 py-3 text-[10px] font-bold uppercase">Voltar</button>
            <button @click="nextStep(2)" class="bg-ink px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-white">Calcular frete</button>
          </div>
        </div>
        <div v-show="step===3" class="space-y-3">
          <p v-if="shippingQuoteError" class="border border-amber-700/30 bg-amber-50 p-3 text-xs text-amber-900" v-text="shippingQuoteError"></p>
          <p class="text-xs text-ink/55">Prazo do Melhor Envio não inclui o tempo de fabricação.</p>
          <template v-for="s in shippingOptions" :key="s.id">
            <label class="flex cursor-pointer items-center justify-between border p-4" :class="shipping===s.id?'border-clay bg-clay/5':'border-ink/15'">
              <span class="flex items-center gap-3">
                <input type="radio" :value="s.id" v-model="shipping">
                <span><b class="block text-sm" v-text="s.name"></b><span class="text-xs text-ink/55" v-text="s.eta"></span></span>
              </span>
              <b v-text="s.price===0?'Grátis':money(s.price)"></b>
            </label>
          </template>
          <label class="block text-[10px] font-bold uppercase tracking-widest">Observação para instalação<textarea v-model="customer.note" rows="2" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-sm font-normal normal-case tracking-normal"></textarea></label>
          <div class="flex gap-2">
            <button @click="step=2" class="border border-ink/20 px-5 py-3 text-[10px] font-bold uppercase">Voltar e recalcular</button>
            <button @click="step=4" class="bg-ink px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-white">Ir ao pagamento</button>
          </div>
        </div>
        <div v-show="step===4" class="space-y-4">
          <div class="border border-ink/15 bg-white p-4">
            <b class="block text-sm">Pagamento seguro pelo Mercado Pago</b>
            <p class="mt-1 text-xs leading-5 text-ink/55">Você será direcionado ao Checkout Pro para escolher Pix, cartão ou outro meio disponível. Os dados do cartão não passam pela Angélica Casa.</p>
          </div>
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" v-model="customer.terms"> Li e aceito a <button type="button" class="underline" @click="go('politicas')">política de troca e privacidade</button></label>
          <div class="flex gap-2">
            <button @click="step=3" class="border border-ink/20 px-5 py-3 text-[10px] font-bold uppercase">Voltar</button>
            <button :disabled="submittingOrder" @click="placeOrder()" class="bg-clay px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-white hover:bg-ink disabled:cursor-wait disabled:opacity-60">{{ submittingOrder ? 'Conectando ao Mercado Pago…' : 'Pagar com Mercado Pago · ' + money(grandTotal) }}</button>
          </div>
        </div>
      </div>
      <aside class="h-fit border border-ink/10 bg-white p-5">
        <h2 class="font-serif text-2xl">Resumo</h2>
        <template v-for="item in cart" :key="item.key">
          <div class="flex gap-3 border-b border-ink/10 py-3">
            <img :src="item.image" class="h-16 w-14 object-cover" :alt="item.name">
            <div class="flex-1 text-xs">
              <p class="font-serif text-base" v-text="item.name"></p>
              <p class="text-ink/50" v-text="item.color+' · '+item.width+'×'+item.height+' cm · '+item.qty+' un'"></p>
              <b v-text="money(item.price*item.qty)"></b>
            </div>
          </div>
        </template>
        <div class="mt-4 space-y-2 text-sm">
          <div class="flex justify-between"><span>Subtotal</span><span v-text="money(subtotal)"></span></div>
          <div v-if="discount>0" class="flex justify-between"><span>Desconto</span><span v-text="'- '+money(discount)"></span></div>
          <div class="flex justify-between"><span>Frete</span><span v-text="money(shippingPrice)"></span></div>
          <div class="flex justify-between border-t border-ink/10 pt-2 font-semibold"><span>Total</span><span v-text="money(grandTotal)"></span></div>
        </div>
        <p class="mt-3 text-[10px] leading-4 text-ink/45">Frete calculado pelo Melhor Envio. O prazo de transporte começa após a fabricação.</p>
      </aside>
    </div>
  </main>

  <!-- SUCCESS -->
  <main v-show="view==='sucesso'" v-cloak class="mx-auto max-w-xl px-4 py-16 text-center sm:px-8">
    <p class="text-[10px] font-bold uppercase tracking-[.25em] text-clay">Pedido registrado</p>
    <h1 class="mt-3 font-serif text-4xl">Recebemos seu pedido.</h1>
    <p class="mt-3 text-sm text-ink/60" v-if="lastOrder?.paymentStatus==='approved'">Pagamento aprovado. Seu pedido está sendo preparado para processamento.</p>
    <p class="mt-3 text-sm text-ink/60" v-else-if="paymentReturn==='failure'">O pagamento não foi concluído. Você pode tentar novamente pelo link seguro abaixo.</p>
    <p class="mt-3 text-sm text-ink/60" v-else>Pedido registrado. O status será atualizado após a confirmação do Mercado Pago.</p>
    <p class="mt-3 text-sm text-ink/60">Pedido <b v-text="lastOrder?.number"></b> · Pagamento: <span v-text="lastOrder?.paymentStatusLabel || 'aguardando confirmação'"></span></p>
    <a v-if="lastOrder?.checkoutUrl && lastOrder?.paymentStatus!=='approved'" :href="lastOrder.checkoutUrl" class="mt-5 inline-flex bg-clay px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-white">Continuar pagamento</a>
    <p class="mt-6 text-sm" v-text="'Número do pedido: '+(lastOrder?.number||'—')+' · '+(lastOrder?.status||'')"></p>
    <div class="mt-8 flex justify-center gap-3">
      <button @click="go('conta')" class="bg-ink px-5 py-3 text-[10px] font-bold uppercase text-white">Acompanhar</button>
      <button @click="go('home')" class="border border-ink/20 px-5 py-3 text-[10px] font-bold uppercase">Continuar comprando</button>
    </div>
  </main>

  <!-- ACCOUNT -->
  <main v-show="view==='conta'" v-cloak class="mx-auto max-w-4xl px-4 py-12 sm:px-8">
    <h1 class="font-serif text-4xl">Minha conta</h1>
    <p class="mt-2 text-sm text-ink/60">Entre na sua conta para consultar os pedidos associados ao seu e-mail. Seus dados de acesso são armazenados com segurança no servidor.</p>
    <div v-show="!user" class="mt-8 grid gap-10 md:grid-cols-2">
      <form @submit.prevent="login()" class="space-y-3">
        <h2 class="font-serif text-2xl">Entrar</h2>
        <input type="email" v-model="auth.email" placeholder="E-mail" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <input type="password" v-model="auth.password" placeholder="Senha" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <button class="bg-ink px-5 py-3 text-[10px] font-bold uppercase text-white">Entrar</button>
      </form>
      <form @submit.prevent="register()" class="space-y-3">
        <h2 class="font-serif text-2xl">Criar conta</h2>
        <input v-model="auth.name" placeholder="Nome" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <input type="email" v-model="auth.email" placeholder="E-mail" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <input type="password" v-model="auth.password" placeholder="Senha (mín. 10 caracteres)" minlength="10" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <button class="border border-ink px-5 py-3 text-[10px] font-bold uppercase">Cadastrar</button>
      </form>
    </div>
    <div v-show="user" class="mt-8">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p>Olá, <b v-text="user?.name"></b></p>
        <button @click="logout()" class="text-xs uppercase tracking-wider underline">Sair</button>
      </div>
      <h2 class="mt-8 font-serif text-2xl">Pedidos</h2>
      <div v-show="!myOrders.length" class="mt-4 text-sm text-ink/55">Nenhum pedido ainda.</div>
      <template v-for="o in myOrders" :key="o.number">
        <article class="mt-4 border border-ink/10 bg-white p-5">
          <div class="flex flex-wrap justify-between gap-2">
            <div>
              <b v-text="o.number"></b>
              <p class="text-xs text-ink/50" v-text="o.date+' · '+o.payment+' · '+o.paymentStatusLabel+' · '+o.status"></p>
            </div>
            <b v-text="money(o.total)"></b>
          </div>
          <div class="mt-3 h-1.5 bg-sand">
            <div class="h-full bg-clay" :style="'width:'+progress(o.status)+'%'"></div>
          </div>
          <p class="mt-2 text-[11px] text-ink/55" v-text="'Pagamento: '+o.payment"></p>
        </article>
      </template>
      <div v-if="user?.role!=='admin'">
        <button @click="deleteAccount()" class="mt-8 border border-red-800/40 px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-red-800">Excluir conta e dados pessoais</button>
        <p class="mt-2 text-xs text-ink/50">Pedidos ficam anonimizados para manter o histórico da loja; perfil, sessões, mensagens e inscrição de e-mail são removidos.</p>
      </div>
    </div>
  </main>

  <!-- TRACK -->
  <main v-show="view==='rastreio'" v-cloak class="mx-auto max-w-lg px-4 py-16 sm:px-8">
    <h1 class="font-serif text-4xl">Rastrear pedido</h1>
    <form class="mt-6 flex gap-2" @submit.prevent="track()">
      <input v-model="trackQuery" placeholder="Número do pedido (AC-...)" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm">
      <button class="bg-ink px-4 text-[10px] font-bold uppercase text-white">Buscar</button>
    </form>
    <article v-show="tracked" class="mt-8 border border-ink/10 bg-white p-5" v-cloak>
      <b v-text="tracked?.number"></b>
      <p class="text-sm" v-text="tracked?.status"></p>
      <p class="mt-2 text-xs text-ink/55" v-text="tracked?.date"></p>
    </article>
  </main>

  <!-- COMPARE -->
  <main v-show="view==='comparar'" v-cloak class="mx-auto max-w-7xl overflow-x-auto px-4 py-12 sm:px-8">
    <h1 class="font-serif text-4xl">Comparar modelos</h1>
    <p v-show="compare.length<2" class="mt-4 text-sm text-ink/55">Adicione pelo menos 2 produtos na loja (botão ＋).</p>
    <table v-show="compare.length" class="mt-8 min-w-[640px] w-full text-left text-sm">
      <thead>
        <tr class="border-b border-ink/15">
          <th class="py-3"></th>
          <template v-for="id in compare" :key="'ch'+id">
            <th class="px-3 py-3">
              <img :src="byId(id)?.image" class="mb-2 h-28 w-full object-cover">
              <span class="font-serif text-lg" v-text="byId(id)?.name"></span>
            </th>
          </template>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-ink/10"><td class="py-3 text-ink/50">Preço / m²</td><template v-for="id in compare" :key="'cp'+id"><td class="px-3" v-text="money(byId(id)?.price)"></td></template></tr>
        <tr class="border-b border-ink/10"><td class="py-3 text-ink/50">Luz</td><template v-for="id in compare" :key="'cl'+id"><td class="px-3" v-text="byId(id)?.light"></td></template></tr>
        <tr class="border-b border-ink/10"><td class="py-3 text-ink/50">Prazo</td><template v-for="id in compare" :key="'ct'+id"><td class="px-3" v-text="byId(id)?.lead"></td></template></tr>
        <tr><td></td><template v-for="id in compare" :key="'cb'+id"><td class="px-3 py-3"><button @click="openProduct(byId(id))" class="border border-ink px-3 py-2 text-[10px] font-bold uppercase">Personalizar</button></td></template></tr>
      </tbody>
    </table>
  </main>

  <!-- CONTACT -->
  <main v-show="view==='contato'" v-cloak class="mx-auto max-w-3xl px-4 py-12 sm:px-8">
    <h1 class="font-serif text-4xl">Fale com a casa</h1>
    <p class="mt-3 text-sm text-ink/60">Orçamento para obras, empresas e janelas especiais (teto, sacada, home office).</p>
    <form class="mt-8 grid gap-3" @submit.prevent="sendContact()">
      <input v-model="contact.name" required placeholder="Nome" class="border border-ink/20 bg-white px-3 py-3 text-sm">
      <input v-model="contact.email" type="email" required placeholder="E-mail" class="border border-ink/20 bg-white px-3 py-3 text-sm">
      <select v-model="contact.interest" class="border border-ink/20 bg-white px-3 py-3 text-sm">
        <option>Dúvida sobre produto</option>
        <option>Medição em domicílio</option>
        <option>Pedido corporativo</option>
        <option>Troca ou garantia</option>
      </select>
      <textarea v-model="contact.message" required rows="4" placeholder="Mensagem" class="border border-ink/20 bg-white px-3 py-3 text-sm"></textarea>
      <button class="w-fit bg-clay px-6 py-3 text-[10px] font-bold uppercase text-white">Enviar</button>
    </form>
  </main>

  <!-- POLICIES -->
  <main v-show="view==='politicas'" v-cloak class="mx-auto max-w-3xl px-4 py-12 text-sm leading-7 text-ink/75 sm:px-8">
    <h1 class="font-serif text-4xl text-ink">Políticas da loja</h1>
    <h2 class="mt-8 font-serif text-2xl text-ink">Troca e arrependimento</h2>
    <p>Consulte nossa equipe antes de concluir o pedido para confirmar condições de cancelamento, devolução, garantia e produtos feitos sob medida. Esta informação deverá ser substituída pela política comercial revisada da loja.</p>
    <h2 class="mt-8 font-serif text-2xl text-ink">Privacidade (LGPD)</h2>
    <p>Os dados são usados para cadastro, atendimento, pagamento e processamento dos pedidos. Em pedidos com entrega, o CPF, telefone e endereço do destinatário são enviados ao Melhor Envio para preparar a etiqueta. Em Minha conta você pode excluir o perfil e solicitar remoção dos dados pessoais associados; registros comerciais podem ser mantidos anonimizados. Esta política precisa ser revisada para refletir os processos e prazos efetivos da loja antes da publicação.</p>
    <h2 class="mt-8 font-serif text-2xl text-ink">Entrega</h2>
    <p>Os prazos de fabricação e transporte são estimativas e devem ser confirmados para cada produto e CEP antes da publicação da loja.</p>
  </main>

  <!-- ADMIN -->
  <main v-show="view==='admin'" v-cloak class="mx-auto max-w-6xl px-4 py-10 sm:px-8">
    <div v-show="!adminOk" class="max-w-sm">
      <h1 class="font-serif text-3xl">Painel</h1>
      <form class="mt-6 space-y-3" @submit.prevent="adminLogin()">
        <input type="email" v-model="auth.email" placeholder="E-mail administrativo" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <input type="password" v-model="adminPass" placeholder="Senha administrativa" class="w-full border border-ink/20 bg-white px-3 py-3 text-sm" required>
        <button class="bg-ink px-5 py-3 text-[10px] font-bold uppercase text-white">Entrar</button>
      </form>
    <p class="mt-3 text-[11px] text-ink/45">Acesso exclusivo para contas administrativas criadas no servidor.</p>
    </div>
    <div v-show="adminOk">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-[10px] font-bold uppercase tracking-[.2em] text-clay">Backoffice</p>
          <h1 class="font-serif text-4xl">Pedidos e estoque</h1>
        </div>
        <button @click="logout();go('home')" class="text-xs uppercase underline">Sair do painel</button>
      </div>
      <div class="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="border border-ink/10 bg-white p-4"><p class="text-[10px] uppercase text-ink/45">Pedidos</p><p class="font-serif text-3xl" v-text="orders.length"></p></div>
        <div class="border border-ink/10 bg-white p-4"><p class="text-[10px] uppercase text-ink/45">Valor em pedidos</p><p class="font-serif text-3xl" v-text="money(orders.filter(o=>o.status!=='Cancelado').reduce((n,o)=>n+o.total,0))"></p></div>
        <div class="border border-ink/10 bg-white p-4"><p class="text-[10px] uppercase text-ink/45">Aguardando pagamento</p><p class="font-serif text-3xl" v-text="orders.filter(o=>o.status==='Aguardando pagamento').length"></p></div>
        <div class="border border-ink/10 bg-white p-4"><p class="text-[10px] uppercase text-ink/45">SKUs</p><p class="font-serif text-3xl" v-text="products.length"></p></div>
      </div>
      <h2 class="mt-10 font-serif text-2xl">Pedidos</h2>
      <div class="mt-4 overflow-x-auto">
        <table class="w-full min-w-[860px] text-left text-sm">
          <thead><tr class="border-b border-ink/15 text-[10px] uppercase tracking-wider text-ink/45"><th class="py-2">Número</th><th>Cliente</th><th>Status do pedido</th><th>Pagamento</th><th>Total</th><th>Expedição</th></tr></thead>
          <tbody>
            <template v-for="o in orders" :key="o.number">
              <tr class="border-b border-ink/10">
                <td class="py-3" v-text="o.number"></td>
                <td v-text="o.customer?.name"></td>
                <td>
                  <select v-model="o.status" @change="updateOrderStatus(o)" class="border border-ink/15 bg-white px-2 py-1 text-xs">
                    <option>Aguardando pagamento</option>
                    <option>Aguardando análise</option>
                    <option>Pago</option>
                    <option>Em fabricação</option>
                    <option>Enviado</option>
                    <option>Entregue</option>
                    <option>Cancelado</option>
                  </select>
                </td>
                <td><span v-text="o.payment"></span><small class="block text-ink/50" v-text="o.paymentStatusLabel"></small></td>
                <td v-text="money(o.total)"></td>
                <td class="max-w-[220px] py-3">
                  <template v-if="o.shipping==='retirada'">
                    <small>Retirada no ateliê</small>
                  </template>
                  <template v-else-if="o.paymentStatus==='approved'">
                    <small class="block text-ink/55" v-text="'Etapa: '+(o.shippingStage||'pendente')"></small>
                    <input v-if="!o.shippingStage" v-model="o.invoiceKey" inputmode="numeric" maxlength="44" placeholder="Chave NF-e (44 dígitos)" class="my-1 w-full border border-ink/20 px-2 py-1 text-[10px]">
                    <button v-if="!o.shippingStage" @click="shippingAction(o,'prepare')" class="border border-ink/20 px-2 py-1 text-[10px] uppercase">Preparar</button>
                    <button v-else-if="o.shippingStage==='cart'" @click="shippingAction(o,'purchase')" class="border border-clay px-2 py-1 text-[10px] uppercase text-clay">Comprar etiqueta</button>
                    <button v-else-if="o.shippingStage==='purchased'" @click="shippingAction(o,'generate')" class="border border-ink/20 px-2 py-1 text-[10px] uppercase">Gerar etiqueta</button>
                    <template v-else-if="['generated','printed'].includes(o.shippingStage)">
                      <a v-if="o.shippingLabelUrl" :href="o.shippingLabelUrl" target="_blank" rel="noopener noreferrer" class="mr-2 text-[10px] underline">Imprimir</a>
                      <button @click="shippingAction(o,'print')" class="border border-ink/20 px-2 py-1 text-[10px] uppercase">Atualizar link</button>
                    </template>
                    <small v-else-if="['preparing','checkout_started','generation_started'].includes(o.shippingStage)" class="block text-amber-800">Ação iniciada. Verifique o Melhor Envio antes de repetir para evitar duplicidade.</small>
                  </template>
                  <small v-else>Disponível após a aprovação</small>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <h2 class="mt-10 font-serif text-2xl">Estoque</h2>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <template v-for="p in products" :key="'st'+p.id">
          <div class="flex items-center justify-between border border-ink/10 bg-white p-3">
            <span class="min-w-0 flex-1 text-sm" v-text="p.name"></span>
            <label class="flex items-center gap-1 text-xs">R$/m² <input type="number" min="0.01" max="100000" step="0.01" v-model.number="p.price" @change="updateProduct(p)" class="w-24 border border-ink/20 px-2 py-1 text-sm"></label>
            <label class="flex items-center gap-1 text-xs">Un. <input type="number" min="0" max="100000" step="1" v-model.number="p.stock" @change="updateProduct(p)" class="w-20 border border-ink/20 px-2 py-1 text-sm"></label>
          </div>
        </template>
      </div>
      <h2 class="mt-10 font-serif text-2xl">Mensagens de contato</h2>
      <div v-show="!contacts.length" class="mt-3 text-sm text-ink/55">Nenhuma mensagem recebida.</div>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <article v-for="message in contacts" :key="message.id" class="border border-ink/10 bg-white p-4">
          <div class="flex justify-between gap-3"><b v-text="message.name"></b><a class="text-xs underline" :href="'mailto:'+message.email" v-text="message.email"></a></div>
          <p class="mt-1 text-[10px] uppercase text-ink/45" v-text="message.interest+' · '+message.created_at"></p>
          <p class="mt-3 whitespace-pre-wrap text-sm" v-text="message.message"></p>
        </article>
      </div>
      <h2 class="mt-10 font-serif text-2xl">Inscritos na newsletter <span class="text-base text-ink/50" v-text="'('+subscribers.length+')'"></span></h2>
      <div class="mt-3 flex flex-wrap gap-2">
        <a v-for="subscriber in subscribers" :key="subscriber.email" class="border border-ink/10 bg-white px-3 py-2 text-xs underline" :href="'mailto:'+subscriber.email" v-text="subscriber.email"></a>
      </div>
    </div>
  </main>

  <StoreFooter />
  <SearchOverlay />
  <ProductModal />
  <CartDrawer />

  <a v-cloak v-show="waLink" :href="waLink" target="_blank" rel="noopener" class="fixed bottom-5 right-5 z-30 grid h-14 w-14 place-items-center rounded-full bg-[#25D366] text-white shadow-soft" aria-label="WhatsApp">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11.5A8.5 8.5 0 0 1 7.3 18.4L4 19.5l1.2-3.2A8.5 8.5 0 1 1 20 11.5Zm-8.4 6.6c1.5 0 2.9-.4 4.1-1.2l.3-.2 2.4.6-.6-2.3.2-.3a6.7 6.7 0 1 0-2.3 2.9l-.3.2c-1.1.7-2.4 1.1-3.8 1.1Zm3.7-5c-.2-.1-1.2-.6-1.4-.7-.2-.1-.3-.1-.5.1l-.6.7c-.1.1-.3.2-.5.1s-1-.4-1.9-1.2c-.7-.6-1.2-1.4-1.3-1.6s0-.4.1-.5l.4-.4.1-.3c0-.1 0-.3 0-.4s-.5-1.1-.6-1.5c-.2-.4-.4-.3-.5-.3h-.4c-.1 0-.4.1-.6.3-.2.2-.8.8-.8 1.9s.8 2.2.9 2.3c.1.2 1.6 2.5 3.9 3.4 2.3.9 2.3.6 2.7.6.4 0 1.3-.5 1.5-1 .2-.5.2-.9.1-1 0-.1-.2-.1-.4-.2Z"/></svg>
  </a>

  <div v-cloak v-show="toast" class="fixed bottom-5 left-1/2 z-[90] -translate-x-1/2 bg-ink px-5 py-3 text-xs text-white shadow-soft" v-text="toast"></div>
  </div>
</template>
