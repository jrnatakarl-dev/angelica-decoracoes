<script>
import { inject } from 'vue';
import { storeKey } from '../storeKey.js';

export default {
  name: 'StoreHeader',
  setup() {
    return inject(storeKey);
  },
};
</script>

<template>
<div class="bg-ink px-4 py-2 text-center text-[10px] font-semibold uppercase tracking-[.2em] text-white sm:text-xs">
    Catálogo online &nbsp;·&nbsp; Pedidos salvos com segurança &nbsp;·&nbsp; Sob medida
  </div>

  <header class="sticky top-0 z-40 border-b border-ink/10 bg-paper/95 backdrop-blur">
    <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 lg:px-8">
      <button class="lg:hidden" @click="mobileOpen=!mobileOpen" aria-label="Abrir menu">
        <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
      <a href="#inicio" @click.prevent="go('home')" class="flex items-center gap-3" aria-label="Angélica Casa">
        <span class="grid h-10 w-10 place-items-center rounded-full bg-clay font-serif text-xl text-white">a</span>
        <span class="block font-serif text-2xl leading-none">angélica <span class="text-sm">casa</span></span>
      </a>
      <nav class="hidden items-center gap-7 text-sm text-ink/75 lg:flex">
        <a class="hover:text-clay" href="#colecoes" @click.prevent="goToSection('home', 'colecoes')">Coleções</a>
        <a class="hover:text-clay" href="#loja" @click.prevent="goToSection('home', 'loja')">Persianas</a>
        <a class="hover:text-clay" href="#guia" @click.prevent="goToSection('home', 'guia')">Guia de medidas</a>
        <a class="hover:text-clay" href="#sobre" @click.prevent="goToSection('home', 'sobre')">Nossa casa</a>
        <a class="hover:text-clay" href="#contato" @click.prevent="go('contato')">Contato</a>
      </nav>
      <div class="flex items-center gap-1 sm:gap-3">
      <button @click="openSearch()" class="p-2" aria-label="Buscar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>
        </button>
        <button @click="go('conta')" class="hidden p-2 sm:block" aria-label="Minha conta">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="8" r="3.2"/><path d="M5 19c1.4-3.2 4-5 7-5s5.6 1.8 7 5"/></svg>
        </button>
        <button @click="favoritesOnly=!favoritesOnly;goToSection('home', 'loja')" class="relative p-2" aria-label="Favoritos">
          <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M20.8 8.8c0 5.2-8.8 11-8.8 11s-8.8-5.8-8.8-11a4.8 4.8 0 0 1 8.8-2.6 4.8 4.8 0 0 1 8.8 2.6Z"/></svg>
          <span v-show="favorites.length" v-cloak v-text="favorites.length" class="absolute -right-0.5 -top-0.5 grid h-4 w-4 place-items-center rounded-full bg-clay text-[9px] text-white"></span>
        </button>
        <button @click="go('comparar')" class="relative hidden p-2 md:block" aria-label="Comparar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 20V10M12 20V4M20 20v-7"/></svg>
          <span v-show="compare.length" v-cloak v-text="compare.length" class="absolute -right-0.5 -top-0.5 grid h-4 w-4 place-items-center rounded-full bg-ink text-[9px] text-white"></span>
        </button>
        <button @click="cartOpen=true" class="flex items-center gap-2 border border-ink/20 px-3 py-2 text-xs font-semibold uppercase tracking-wider transition hover:bg-ink hover:text-white sm:px-4">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 4h2l2.2 11.2a2 2 0 0 0 2 1.6h8.9a2 2 0 0 0 2-1.6L22 8H6"/><circle cx="10" cy="20" r="1"/><circle cx="18" cy="20" r="1"/></svg>
          <span class="hidden sm:inline">Sacola</span>
          <span v-text="cartCount" class="grid h-5 min-w-5 place-items-center rounded-full bg-clay px-1 text-[10px] text-white"></span>
        </button>
      </div>
    </div>
    <div v-cloak v-show="mobileOpen" class="border-t border-ink/10 bg-paper px-5 py-4 lg:hidden">
      <nav class="grid gap-4 text-sm">
        <a @click.prevent="mobileOpen=false;goToSection('home', 'colecoes')" href="#colecoes">Coleções</a>
        <a @click.prevent="mobileOpen=false;goToSection('home', 'loja')" href="#loja">Persianas</a>
        <a @click.prevent="mobileOpen=false;goToSection('home', 'guia')" href="#guia">Como medir</a>
        <a @click.prevent="mobileOpen=false;go('conta')" href="#conta">Minha conta</a>
        <a @click.prevent="mobileOpen=false;go('contato')" href="#contato">Contato</a>
        <a @click.prevent="mobileOpen=false;go('rastreio')" href="#rastreio">Rastrear pedido</a>
      </nav>
    </div>
  </header>
</template>
