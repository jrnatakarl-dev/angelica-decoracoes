import { reactive, watch } from 'vue';

const readArray = (key, validate) => {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return [];
    const value = JSON.parse(raw);
    if (!Array.isArray(value)) throw new TypeError('Formato inválido');
    return value.filter(validate);
  } catch (error) {
    console.warn(`Dados locais inválidos em ${key}`, error);
    try { window.localStorage.removeItem(key); } catch { /* armazenamento indisponível */ }
    return [];
  }
};

const validId = (value) => Number.isSafeInteger(value) && value > 0;

const store = reactive({
    categories:[], products:[], faqs:[],

    view:'home', category:'', favoritesOnly:false, query:'', sort:'featured', filterLight:'',
    favorites:[], cart:[], compare:[], recent:[], orders:[], contacts:[], subscribers:[], product:null,
    cartOpen:false, mobileOpen:false, searchOpen:false, faq:-1, toast:'',
    width:100, height:120, quantity:1, selectedColor:'', install:'vao', galleryIndex:0,
    step:1, shipping:'retirada', submittingOrder:false, quotingShipping:false, shippingQuotes:[], shippingQuoteError:'',
    paymentReturn:'', cepStatus:'', pdpCep:'', pdpFreight:'', lastOrder:null,
    user:null, adminOk:false, adminPass:'', trackQuery:'', tracked:null, newsEmail:'',
    customer:{name:'',email:'',phone:'',cpf:'',cep:'',street:'',number:'',complement:'',neighborhood:'',city:'',uf:'',note:'',terms:false},
    auth:{name:'',email:'',password:''}, contact:{name:'',email:'',interest:'Dúvida sobre produto',message:''},
    card:{name:'',installments:1},

    get shopTitle(){if(this.favoritesOnly)return 'Seus favoritos';return this.categories.find(c=>c.id===this.category)?.name||'Mais queridos'},
    get hasFilters(){return !!(this.category||this.favoritesOnly||this.query||this.filterLight)},
    get visibleProducts(){
      let a=this.products.filter(p=>(!this.category||p.category===this.category)&&(!this.favoritesOnly||this.favorites.includes(p.id))&&(!this.filterLight||p.light===this.filterLight)&&(!this.query||(p.name+' '+p.kind+' '+p.description+' '+p.light).toLowerCase().includes(this.query.toLowerCase())));
      if(this.sort==='low')a=[...a].sort((x,y)=>x.price-y.price);
      if(this.sort==='high')a=[...a].sort((x,y)=>y.price-x.price);
      return a;
    },
    get cartCount(){return this.cart.reduce((n,i)=>n+i.qty,0)},
    get subtotal(){return this.cart.reduce((n,i)=>n+i.price*i.qty,0)},
    get areaM2(){return Math.max(0.4,(Number(this.width)||0)*(Number(this.height)||0)/10000)},
    get configPrice(){if(!this.product)return 0;return this.product.price*this.areaM2*this.quantity},
    get galleryImage(){return (this.product?.gallery||[this.product?.image])[this.galleryIndex]||this.product?.image},
    get discount(){return 0},
    get shippingPrice(){
      const s=this.shippingOptions.find(x=>x.id===this.shipping);
      return s?s.price:0;
    },
    get grandTotal(){return Math.max(0,this.subtotal-this.discount+this.shippingPrice)},
    get shippingOptions(){
      return [
        {id:'retirada',name:'Retirada no ateliê',eta:'Combine o horário após a compra',price:0},
        ...this.shippingQuotes.map(quote=>({
          id:quote.id,name:`${quote.company} · ${quote.name}`,
          eta:quote.deliveryDays?`${quote.deliveryDays} dias úteis após fabricação`:'Prazo informado pela transportadora',
          price:quote.price,
        })),
      ];
    },

    get myOrders(){return this.user ? this.orders : []},

    get waLink(){
      // Configure um número real no formato internacional antes de publicar.
      return '';
    },

    async init(){
      this.favorites=readArray('ac_favorites', validId).slice(0, 500);
      this.cart=readArray('ac_cart', item => item && typeof item === 'object'
        && validId(Number(item.id)) && Number.isFinite(Number(item.width))
        && Number.isFinite(Number(item.height)) && Number.isFinite(Number(item.qty))
        && Number.isFinite(Number(item.price))).map(item => ({
          ...item,
          id: Number(item.id),
          width: Math.min(500, Math.max(40, Number(item.width))),
          height: Math.min(500, Math.max(40, Number(item.height))),
          qty: Math.min(20, Math.max(1, Math.floor(Number(item.qty)))),
        })).slice(0, 30);
      this.compare=readArray('ac_compare', validId).slice(0, 3);
      this.recent=readArray('ac_recent', validId).slice(0, 6);

      try {
        const [catalog, session] = await Promise.all([this.api('/api/catalog'), this.api('/api/me')]);
        this.categories=catalog.categories;
        this.products=catalog.products;
        this.faqs=catalog.faqs;
        const productsById = new Map(this.products.map(product => [product.id, product]));
        this.favorites=this.favorites.filter(id => productsById.has(id));
        this.compare=this.compare.filter(id => productsById.has(id));
        this.recent=this.recent.filter(id => productsById.has(id));
        this.cart=this.cart.filter(item => productsById.has(item.id)).map(item => {
          const product = productsById.get(item.id);
          const area = Math.max(0.4, item.width * item.height / 10000);
          return {
            ...item,
            name: product.name,
            image: product.image,
            price: Math.round(product.price * 100 * area) / 100,
          };
        });
        this.user=session.user;
        this.adminOk=this.user?.role==='admin';
        if(this.user) await this.loadOrders();
      } catch(error) {
        this.notify(error.message || 'Não foi possível conectar à loja');
      }

      this.readHash();
      const params = new URLSearchParams(window.location.search);
      this.paymentReturn = params.get('payment_return') || '';
      const orderNumber = params.get('external_reference') || '';
      if (this.paymentReturn && /^AC-[A-F0-9]{12}$/.test(orderNumber)) {
        this.view = 'sucesso';
        try {
          this.lastOrder = await this.api('/api/orders/track/' + encodeURIComponent(orderNumber));
        } catch (error) {
          this.notify('Não foi possível consultar o status do pedido. Guarde o número ' + orderNumber);
        }
      }
    },

    async api(path, options={}){
      const response=await fetch(path,{...options,credentials:'same-origin',headers:{...(options.headers||{}),'Content-Type':'application/json'}});
      const body=await response.json().catch(()=>({}));
      if(!response.ok) throw new Error(body.error||'Não foi possível concluir a solicitação.');
      return body;
    },

    async loadOrders(){
      if (this.user?.role==='admin') {
        const [orderData, contactData, subscriberData] = await Promise.all([
          this.api('/api/admin/orders'),
          this.api('/api/admin/contacts'),
          this.api('/api/admin/subscribers'),
        ]);
        this.orders=orderData.orders;
        this.contacts=contactData.contacts;
        this.subscribers=subscriberData.subscribers;
        return;
      }
      const {orders}=await this.api('/api/orders');
      this.orders=orders;
    },

    readHash(){
      const h=(location.hash||'#inicio').replace('#','');
      const pages=['checkout','conta','sucesso','admin','comparar','contato','politicas','rastreio'];
      if(pages.includes(h)) this.view=h;
      else this.view='home';
    },

    go(v){
      this.view=v; this.mobileOpen=false; this.cartOpen=false; this.searchOpen=false; this.product=null;
      history.replaceState(null,'','#'+(v==='home'?'inicio':v));
      window.scrollTo({top:0,behavior:'smooth'});
    },
    goToSection(view, section){
      this.go(view);
      this.mobileOpen=false;
      setTimeout(()=>document.getElementById(section)?.scrollIntoView({behavior:'smooth'}),0);
    },

    closeOverlays(){this.product=null;this.cartOpen=false;this.searchOpen=false;this.mobileOpen=false},
    openSearch(){this.searchOpen=true;setTimeout(()=>document.querySelector('[data-search-input]')?.focus(),0)},
    byId(id){return this.products.find(p=>p.id===id)},
    money(n){return Number(n||0).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})},
    notify(msg){this.toast=msg;clearTimeout(this._t);this._t=setTimeout(()=>this.toast='',2400)},
    setCategory(id){this.category=id;this.favoritesOnly=false;document.getElementById('loja')?.scrollIntoView({behavior:'smooth'})},
    clearFilters(){this.category='';this.favoritesOnly=false;this.query='';this.filterLight=''},
    toggleFavorite(id){this.favorites=this.favorites.includes(id)?this.favorites.filter(x=>x!==id):[...this.favorites,id]},

    toggleCompare(id){
      if(this.compare.includes(id)) this.compare=this.compare.filter(x=>x!==id);
      else if(this.compare.length>=3) this.notify('Compare no máximo 3 modelos');
      else this.compare=[...this.compare,id];
    },

    openProduct(p){
      if(!p)return;
      this.product=p; this.width=120; this.height=140; this.quantity=1; this.selectedColor=p.colors[0].name; this.install='vao'; this.galleryIndex=0; this.pdpFreight='';
      this.recent=[p.id,...this.recent.filter(x=>x!==p.id)].slice(0,6);
    },

    addToCart(){
      if(!this.product)return;
      if(!Number.isInteger(Number(this.quantity))||this.quantity<1||this.quantity>20){this.notify('A quantidade deve ser de 1 a 20');return}
      const alreadyInCart=this.cart.reduce((total,item)=>total+(item.id===this.product.id?item.qty:0),0);
      if(this.cart.length>=30||this.product.stock<alreadyInCart+this.quantity){this.notify('Estoque insuficiente ou limite de itens atingido');return}
      if(!Number.isFinite(Number(this.width))||!Number.isFinite(Number(this.height))||this.width<40||this.height<40||this.width>500||this.height>500){this.notify('As medidas devem ficar entre 40 e 500 cm');return}
      const unit=Math.round(this.product.price*100*this.areaM2)/100;
      this.cart.push({key:Date.now()+Math.random(),id:this.product.id,name:this.product.name,image:this.product.image,color:this.selectedColor,install:this.install==='vao'?'vão':'parede',width:Number(this.width),height:Number(this.height),price:unit,qty:this.quantity});
      this.product=null; this.cartOpen=true; this.notify('Adicionado à sacola');
    },

    changeQty(i,d){
      const item=this.cart[i];
      if(!item)return;
      const product=this.byId(item.id);
      const alreadyInCart=this.cart.reduce((total,other,index)=>total+(index!==i&&other.id===item.id?other.qty:0),0);
      const max=Math.max(1,Math.min(20,(product?.stock??20)-alreadyInCart));
      item.qty=Math.min(max,Math.max(1,Number(item.qty)+Number(d)));
      this.cart=[...this.cart];
    },
    removeItem(i){this.cart.splice(i,1);this.cart=[...this.cart]},
    startCheckout(){if(!this.cart.length)return;this.cartOpen=false;this.step=1;this.go('checkout')},

    async nextStep(s){
      if(s===1 && (!this.customer.name||!this.customer.email)){this.notify('Preencha nome e e-mail');return}
      if(s===2){
        if(!this.customer.cep||!this.customer.street||!this.customer.city){this.notify('Complete o endereço');return}
        await this.calculateShipping();
        this.step=3;return;
      }
      this.step=s+1;
    },

    async calculateShipping(){
      this.quotingShipping=true;this.shippingQuoteError='';this.shippingQuotes=[];
      try{
        const result=await this.api('/api/shipping/quote',{method:'POST',body:JSON.stringify({
          cep:this.customer.cep,items:this.cart,
        })});
        this.shippingQuotes=result.quotes||[];
        this.shipping=this.shippingQuotes[0]?.id||'retirada';
        if(!this.shippingQuotes.length)this.shippingQuoteError='Não há opções de entrega para este CEP. Você pode retirar no ateliê.';
      }catch(error){
        this.shipping='retirada';this.shippingQuoteError=error.message;
      }finally{this.quotingShipping=false}
    },

    async lookupCep(){
      const cep=(this.customer.cep||'').replace(/\D/g,'');
      if(cep.length!==8){this.cepStatus='CEP inválido';return}
      this.cepStatus='Consultando ViaCEP…';
      try{
        const r=await fetch('https://viacep.com.br/ws/'+cep+'/json/');
        const d=await r.json();
        if(d.erro){this.cepStatus='CEP não encontrado';return}
        this.customer.street=d.logradouro||this.customer.street;
        this.customer.neighborhood=d.bairro||'';
        this.customer.city=d.localidade||'';
        this.customer.uf=d.uf||'';
        this.customer.cep=cep.slice(0,5)+'-'+cep.slice(5);
        this.cepStatus=d.localidade+'/'+d.uf;
      }catch(e){this.cepStatus='Não foi possível consultar o CEP'}
    },

    async previewFreight(){
      const cep=(this.pdpCep||'').replace(/\D/g,'');
      if(cep.length!==8){this.pdpFreight='Informe um CEP com 8 dígitos';return}
      if(!this.product){this.pdpFreight='Selecione um produto';return}
      try{
        const result=await this.api('/api/shipping/quote',{method:'POST',body:JSON.stringify({
          cep,items:[{id:this.product.id,qty:this.quantity,width:this.width,height:this.height}],
        })});
        this.pdpFreight=result.quotes.length
          ?result.quotes.map(quote=>`${quote.company} · ${quote.name}: ${this.money(quote.price)}${quote.deliveryDays?` · ${quote.deliveryDays} dias úteis`:''}`).join(' | ')
          :'Nenhuma transportadora atende este CEP.';
      }catch(e){this.pdpFreight=e.message}
    },

    placeOrder(){
      if(!this.customer.terms){this.notify('Aceite as políticas para continuar');return}
      if(!this.cart.length){this.notify('Sacola vazia');return}
      if(!this.customer.name||!this.customer.email||!this.customer.cep||!this.customer.street||!this.customer.city){this.notify('Complete seus dados e endereço');this.step=1;return}
      if(this.shipping!=='retirada'&&this.customer.cpf.replace(/\D/g,'').length!==11){this.notify('Informe um CPF válido para a entrega');this.step=1;return}
      this.submitOrder();
    },

    async submitOrder(){
      if(this.submittingOrder)return;
      this.submittingOrder=true;
      try{
        const result=await this.api('/api/orders',{method:'POST',body:JSON.stringify({customer:this.customer,items:this.cart,payment:'mercado_pago',shipping:this.shipping})});
        this.lastOrder=result.order;
        this.cart=[];
        if(this.user) await this.loadOrders();
        window.location.assign(result.checkoutUrl);
      }catch(error){this.notify(error.message)}
      finally{this.submittingOrder=false}
    },

    async updateOrderStatus(order){
      try{
        await this.api('/api/admin/orders/'+encodeURIComponent(order.number),{method:'PATCH',body:JSON.stringify({status:order.status})});
        this.notify('Status atualizado');
      }catch(error){this.notify(error.message);await this.loadOrders()}
    },

    async shippingAction(order,action){
      if(action==='purchase'&&!window.confirm('Esta ação compra a etiqueta e debita o saldo da carteira Melhor Envio. Continuar?'))return;
      try{
        await this.api(`/api/admin/orders/${encodeURIComponent(order.number)}/shipping/${action}`,{
          method:'POST',body:JSON.stringify({invoiceKey:order.invoiceKey||''}),
        });
        this.notify(({prepare:'Envio preparado no Melhor Envio',purchase:'Etiqueta comprada',generate:'Etiqueta gerada',print:'Link privado da etiqueta atualizado'})[action]);
        await this.loadOrders();
      }catch(error){
        this.notify(error.message);
        await this.loadOrders();
      }
    },

    async updateProduct(product){
      try{
        await this.api('/api/admin/products/'+product.id,{method:'PATCH',body:JSON.stringify({stock:product.stock,price:product.price})});
        this.notify('Preço e estoque atualizados');
      }catch(error){this.notify(error.message)}
    },

    progress(status){return { 'Aguardando pagamento':20, Pago:40, 'Em fabricação':60, Enviado:80, Entregue:100, Cancelado:0 }[status]||30},

    async login(){
      const email=(this.auth.email||'').trim().toLowerCase();
      const password=this.auth.password||'';
      if(!email||!password){this.notify('Informe e-mail e senha');return}
      try{
        const {user}=await this.api('/api/auth/login',{method:'POST',body:JSON.stringify({email,password})});
        this.user=user;
        this.adminOk=user.role==='admin';
        await this.loadOrders();
        this.notify('Bem-vindo, '+user.name);
      }catch(error){this.notify(error.message)}
    },

    async register(){
      const name=(this.auth.name||'').trim();
      const email=(this.auth.email||'').trim().toLowerCase();
      if((this.auth.password||'').length<10){this.notify('Use uma senha com pelo menos 10 caracteres');return}
      if(!name||!email){this.notify('Informe nome e e-mail');return}
      try{
        const {user}=await this.api('/api/auth/register',{method:'POST',body:JSON.stringify({name,email,password:this.auth.password})});
        this.user=user;
        this.orders=[];
        this.notify('Conta criada');
      }catch(error){this.notify(error.message)}
    },

    async logout(){
      try{await this.api('/api/auth/logout',{method:'POST',body:'{}'})}catch(error){this.notify(error.message)}
      this.user=null;
      this.orders=[];
      this.adminOk=false;
      this.adminPass='';
      this.auth.password='';
    },

    async deleteAccount(){
      if(!window.confirm('Excluir sua conta e remover seus dados pessoais? Os registros de pedidos serão mantidos anonimizados para histórico da loja.'))return;
      try{
        await this.api('/api/me',{method:'DELETE'});
        this.user=null;
        this.orders=[];
        this.auth.password='';
        this.notify('Conta excluída e dados pessoais removidos');
      }catch(error){this.notify(error.message)}
    },

    async track(){
      const q=(this.trackQuery||'').trim().toUpperCase();
      if(!q){this.notify('Informe o número do pedido');return}
      try{this.tracked=await this.api('/api/orders/track/'+encodeURIComponent(q))}
      catch(error){this.tracked=null;this.notify(error.message)}
    },

    async sendContact(){
      try{await this.api('/api/contact',{method:'POST',body:JSON.stringify(this.contact)});this.notify('Mensagem registrada');this.contact={name:'',email:'',interest:'Dúvida sobre produto',message:''}}
      catch(error){this.notify(error.message)}
    },
    async newsletter(){
      try{await this.api('/api/newsletter',{method:'POST',body:JSON.stringify({email:this.newsEmail})});this.notify('Inscrição registrada');this.newsEmail=''}
      catch(error){this.notify(error.message)}
    },
    async adminLogin(){
      if(!this.auth.email||!this.adminPass){this.notify('Informe e-mail e senha');return}
      try{
        const {user}=await this.api('/api/auth/login',{method:'POST',body:JSON.stringify({email:this.auth.email,password:this.adminPass})});
        if(user.role!=='admin'){await this.api('/api/auth/logout',{method:'POST',body:'{}'});this.notify('Acesso restrito a administradores');return}
        this.user=user;this.adminOk=true;this.adminPass='';await this.loadOrders();this.notify('Painel aberto');
      }catch(error){this.notify(error.message)}
    },
    async copy(t){
      if(!t){this.notify('Nada para copiar');return}
      try{await navigator.clipboard.writeText(t);this.notify('Copiado')}
      catch(e){this.notify('Não foi possível copiar neste navegador')}
    }
  });

const persist = (key, value) => {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn(`Falha ao salvar ${key}`, error);
  }
};

watch(() => store.favorites, value => persist('ac_favorites', value));
watch(() => store.cart, value => persist('ac_cart', value), { deep: true });
watch(() => store.compare, value => persist('ac_compare', value));
watch(() => store.recent, value => persist('ac_recent', value));

export default store;
