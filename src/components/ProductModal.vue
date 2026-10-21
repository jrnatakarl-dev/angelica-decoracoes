<script>
import { inject } from 'vue';
import { storeKey } from '../storeKey.js';

export default {
  name: 'ProductModal',
  setup() {
    return inject(storeKey);
  },
};
</script>

<template>
<!-- PRODUCT -->
  <div v-cloak v-show="product" class="fixed inset-0 z-50 grid place-items-center bg-ink/55 p-3 backdrop-blur-sm" @click.self="product=null">
    <section class="max-h-[94vh] w-full max-w-5xl overflow-y-auto bg-paper shadow-soft">
      <div class="flex items-center justify-between border-b border-ink/10 px-5 py-4">
        <div>
          <p class="text-[9px] uppercase tracking-[.2em] text-clay">Feita especialmente para você</p>
          <h2 class="mt-1 font-serif text-2xl" v-text="product?.name"></h2>
        </div>
        <button @click="product=null" class="grid h-9 w-9 place-items-center rounded-full hover:bg-sand" aria-label="Fechar">✕</button>
      </div>
      <div class="grid md:grid-cols-2">
        <div>
          <div class="relative min-h-[280px] bg-sand md:min-h-[490px]">
            <img :src="galleryImage" class="absolute inset-0 h-full w-full object-cover" :alt="product?.name">
            <span v-if="product?.image?.startsWith('http')" class="absolute bottom-3 left-3 bg-paper/90 px-3 py-2 text-[9px] font-bold uppercase tracking-wider">Imagem ilustrativa · confirmar acabamento</span>
          </div>
          <div class="flex gap-2 p-3">
            <template v-for="(img,i) in product?.gallery||[]" :key="img">
              <button @click="galleryIndex=i" class="h-16 w-16 overflow-hidden border" :class="galleryIndex===i?'border-clay':'border-transparent'">
                <img :src="img" class="h-full w-full object-cover" alt="">
              </button>
            </template>
          </div>
        </div>
        <div class="space-y-5 p-5 sm:p-8">
          <p class="text-sm leading-6 text-ink/60" v-text="product?.description"></p>
          <p class="text-xs text-clay" v-text="product?.lead"></p>
          <div>
            <label class="text-[10px] font-bold uppercase tracking-[.16em]">Cor</label>
            <div class="mt-3 flex flex-wrap gap-2">
              <template v-for="color in product?.colors||[]" :key="color.name">
                <button @click="selectedColor=color.name" class="flex items-center gap-2 border px-3 py-2 text-xs" :class="selectedColor===color.name?'border-clay bg-clay/5':'border-ink/15'">
                  <span class="h-4 w-4 rounded-full border border-ink/10" :style="'background:'+color.hex"></span>
                  <span v-text="color.name"></span>
                </button>
              </template>
            </div>
          </div>
          <div>
            <label class="text-[10px] font-bold uppercase tracking-[.16em]">Instalação</label>
            <div class="mt-2 grid grid-cols-2 gap-2">
              <button @click="install='vao'" class="border px-3 py-2 text-xs" :class="install==='vao'?'border-clay bg-clay/5':'border-ink/15'">Dentro do vão</button>
              <button @click="install='parede'" class="border px-3 py-2 text-xs" :class="install==='parede'?'border-clay bg-clay/5':'border-ink/15'">Na parede</button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="text-[10px] font-bold uppercase tracking-[.16em]">Largura (cm)<input type="number" min="40" max="500" v-model.number="width" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-base font-normal outline-none focus:border-clay"></label>
            <label class="text-[10px] font-bold uppercase tracking-[.16em]">Altura (cm)<input type="number" min="40" max="400" v-model.number="height" class="mt-2 w-full border border-ink/20 bg-white px-3 py-3 text-base font-normal outline-none focus:border-clay"></label>
          </div>
          <p class="text-[11px] text-ink/50" v-text="'Área: '+areaM2.toFixed(2)+' m² · estoque: '+(product?.stock||0)+' kits'"></p>
          <div class="flex gap-2">
            <input v-model="pdpCep" placeholder="CEP" class="w-full border border-ink/20 px-3 py-2 text-sm">
            <button @click="previewFreight()" class="border border-ink px-3 text-[10px] font-bold uppercase">Frete</button>
          </div>
          <p v-show="pdpFreight" class="text-xs text-ink/60" v-text="pdpFreight"></p>
          <div class="flex items-center justify-between border-y border-ink/10 py-4">
            <div>
              <span class="text-[9px] uppercase tracking-[.15em] text-ink/50">Preço estimado</span>
              <p class="font-serif text-3xl" v-text="money(configPrice)"></p>
              <span class="text-[10px] text-ink/45" v-text="'ou 6x de '+money(configPrice/6)+' sem juros'"></span>
            </div>
            <div class="flex items-center border border-ink/15">
              <button @click="quantity=Math.max(1,quantity-1)" class="px-3 py-2">−</button>
              <span class="min-w-8 text-center text-sm" v-text="quantity"></span>
              <button @click="quantity=Math.min(20,quantity+1)" class="px-3 py-2">+</button>
            </div>
          </div>
          <button @click="addToCart()" class="w-full bg-clay px-5 py-4 text-[10px] font-bold uppercase tracking-[.18em] text-white transition hover:bg-ink">Adicionar à sacola · <span v-text="money(configPrice)"></span></button>
        </div>
      </div>
    </section>
  </div>
</template>
