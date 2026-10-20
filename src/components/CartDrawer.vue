<script>
import { inject } from 'vue';
import { storeKey } from '../storeKey.js';

export default {
  name: 'CartDrawer',
  setup() {
    return inject(storeKey);
  },
};
</script>

<template>
<!-- CART -->
  <div v-cloak v-show="cartOpen" class="fixed inset-0 z-[60] bg-ink/45" @click.self="cartOpen=false">
    <aside class="ml-auto flex h-full w-full max-w-md flex-col bg-paper shadow-soft">
      <div class="flex items-center justify-between border-b border-ink/10 p-5">
        <div>
          <p class="text-[9px] uppercase tracking-[.18em] text-clay">Sua seleção</p>
          <h2 class="font-serif text-2xl">Sacola <span class="text-base text-ink/45" v-text="'('+cartCount+')'"></span></h2>
        </div>
        <button @click="cartOpen=false" class="grid h-9 w-9 place-items-center rounded-full hover:bg-sand" aria-label="Fechar sacola">✕</button>
      </div>
      <div class="flex-1 overflow-y-auto p-5">
        <template v-if="!cart.length">
          <div class="py-16 text-center">
            <p class="font-serif text-2xl">Sua sacola está vazia.</p>
            <button @click="cartOpen=false;goToSection('home', 'loja')" class="mt-5 border-b border-ink pb-1 text-xs uppercase tracking-widest">Explorar peças</button>
          </div>
        </template>
        <template v-for="(item,i) in cart" :key="item.key">
          <div class="flex gap-4 border-b border-ink/10 py-4">
            <img :src="item.image" class="h-24 w-20 object-cover" :alt="item.name">
            <div class="flex-1">
              <p class="font-serif text-lg" v-text="item.name"></p>
              <p class="mt-1 text-[10px] text-ink/55" v-text="item.color+' · '+item.install+' · '+item.width+' × '+item.height+' cm'"></p>
              <div class="mt-3 flex items-center justify-between">
                <b class="text-sm" v-text="money(item.price*item.qty)"></b>
                <div class="flex items-center gap-3 text-sm">
                  <button @click="changeQty(i,-1)" aria-label="Diminuir">−</button>
                  <span v-text="item.qty"></span>
                  <button @click="changeQty(i,1)" aria-label="Aumentar">+</button>
                  <button @click="removeItem(i)" class="ml-2 text-ink/40" aria-label="Remover">×</button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
      <div v-show="cart.length" class="border-t border-ink/10 p-5">
        <div class="flex justify-between text-sm"><span>Subtotal estimado</span><b v-text="money(subtotal)"></b></div>
        <p class="mt-2 text-[10px] leading-5 text-ink/50">Frete e descontos estimados no checkout. Pagamentos ainda não estão integrados.</p>
        <button @click="startCheckout()" class="mt-4 w-full bg-ink px-4 py-4 text-[10px] font-bold uppercase tracking-[.17em] text-white hover:bg-clay">Continuar para checkout</button>
      </div>
    </aside>
  </div>
</template>
