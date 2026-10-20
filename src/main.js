import { createApp } from 'vue';
import App from './App.vue';
import store from './store.js';
import { storeKey } from './storeKey.js';
import './style.css';

createApp(App).provide(storeKey, store).mount('#app');
