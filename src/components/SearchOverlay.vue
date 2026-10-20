<script>
import { inject } from 'vue';
import { storeKey } from '../storeKey.js';

export default {
  name: 'SearchOverlay',
  setup() {
    return inject(storeKey);
  },
};
</script>

<template>
<!-- SEARCH -->
  <div v-cloak v-show="searchOpen" class="fixed inset-0 z-[80] bg-ink/50 p-4 backdrop-blur-sm" @click.self="searchOpen=false; query=''">
    <div class="mx-auto mt-16 max-w-xl bg-paper p-5 shadow-soft">
      <input data-search-input v-model="query" @input="category='';favoritesOnly=false" placeholder="Buscar persiana, tecido, blackout…" class="w-full border-b border-ink/20 bg-transparent py-3 text-lg outline-none">
      <div class="mt-4 max-h-80 overflow-y-auto">
        <template v-for="p in visibleProducts.slice(0,8)" :key="'s'+p.id">
          <button @click="searchOpen=false; openProduct(p); query=''" class="flex w-full items-center gap-3 py-3 text-left hover:bg-sand/60">
            <img :src="p.image" class="h-12 w-10 object-cover" :alt="p.name">
            <span><span class="block font-serif" v-text="p.name"></span><span class="text-xs text-ink/50" v-text="money(p.price)+'/m²'"></span></span>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
