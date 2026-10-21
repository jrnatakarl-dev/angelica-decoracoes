<script>
import { inject } from 'vue';
import { storeKey } from '../storeKey.js';

export default {
  name: 'StoreFooter',
  setup() {
    return inject(storeKey);
  },
};
</script>

<template>
<footer class="bg-ink text-white">
    <div class="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-8 md:grid-cols-4">
      <div class="md:col-span-2">
        <a href="#inicio" @click.prevent="go('home')" class="font-serif text-3xl">angélica casa</a>
        <p class="mt-3 max-w-sm text-sm leading-6 text-white/60">Persianas sob medida para deixar a luz entrar do seu jeito.</p>
        <form class="mt-5 flex max-w-sm gap-2" @submit.prevent="newsletter()">
          <input v-model="newsEmail" type="email" required placeholder="Seu e-mail" class="w-full bg-white/10 px-3 py-3 text-sm text-white outline-none placeholder:text-white/40">
          <button class="bg-clay px-4 text-[10px] font-bold uppercase">Assinar</button>
        </form>
      </div>
      <div class="text-xs">
        <b class="uppercase tracking-widest">Explore</b>
        <a class="mt-4 block text-white/60 hover:text-white" href="#colecoes" @click.prevent="goToSection('home', 'colecoes')">Coleções</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#loja" @click.prevent="goToSection('home', 'loja')">Produtos</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#" @click.prevent="go('comparar')">Comparar</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#" @click.prevent="go('admin')">Painel</a>
      </div>
      <div class="text-xs">
        <b class="uppercase tracking-widest">Ajuda</b>
        <a class="mt-4 block text-white/60 hover:text-white" href="#guia" @click.prevent="goToSection('home', 'guia')">Como medir</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#" @click.prevent="go('rastreio')">Rastreio</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#" @click.prevent="go('politicas')">Troca e LGPD</a>
        <a class="mt-2 block text-white/60 hover:text-white" href="#" @click.prevent="go('contato')">Contato</a>
      </div>
    </div>
    <div class="border-t border-white/15 px-4 py-4 text-center text-[10px] text-white/45">© <span v-text="new Date().getFullYear()"></span> Angélica Casa · Persianas sob medida.</div>
  </footer>
</template>
