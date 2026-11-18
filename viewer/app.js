(function(){
'use strict';
const $=id=>document.getElementById(id),D=window.BOOKGRAPH_DATA,C=window.BookGraphCore;
if(!D||!window.d3||!window.marked||!window.DOMPurify||!C){$('card-content').textContent='Не удалось загрузить данные или библиотеки. Сохраните каталог viewer целиком рядом с wiki и выполните python viewer/export.py.';return;}
const nodesById=new Map(D.nodes.map(n=>[n.id,n])),byPage=new Map(D.nodes.map(n=>[n.page,n]));
const TYPE={character:'Персонаж',event:'Событие',place:'Место',object:'Предмет',organization:'Организация',context:'Контекст'};
const LAYER={story:'Основное действие',mentioned:'Упоминания и предыстория',literary:'Литературная отсылка',editorial:'Редакционный аппарат'};
const ROLE={main:'Главный персонаж',secondary:'Второстепенный персонаж',episodic:'Эпизодическое лицо'};
const TRUTH={confirmed:'Подтверждено в своём слое',claimed:'Сообщено персонажем',disputed:'Спорно',refuted:'Опровергнуто',unknown:'Не установлено'};
const SCOPE={canon:'Канон пьесы',analysis:'∴ Аналитический вывод',editorial:'Аппарат издания',history:'Исторический контекст'};
const STATUS={occurred:'Показано в действии',reported:'Сообщено / пересказано',planned:'Запланировано',disputed:'Спорно',refuted:'Опровергнуто',hypothetical:'Гипотетическое'};
const REL={family:'Родство',marriage:'Брак',engagement:'Помолвка',love:'Любовь',courtship:'Ухаживание и обещания',acquaintance:'Знакомство',business:'Деловые отношения',service:'Служебные отношения',patronage:'Покровительство',rivalry:'Соперничество',conflict:'Конфликт',deception:'Обман',colleagues:'Совместное исполнение / работа',violence:'Насилие',reference:'Литературная отсылка',editorial:'Актёры и роли'};
const COLORS={male:'#678d99',female:'#b87c69',unknown:'#989a92'};
const escapes={'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>escapes[c]);
const asset=path=>'../'+path.split('/').map(encodeURIComponent).join('/');
const norm=value=>String(value||'').toLocaleLowerCase('ru').replaceAll('ё','е');
let state={mode:'characters',layers:new Set(['story']),importance:'',relation:'',act:'',participant:'',place:'',status:'',truth:'',analysis:true,before:false,chain:'',selected:null,pinned:false};
let view={nodes:[],edges:[]},nodeGroups,edgeGroups,world,zoom,graph=d3.select('#graph'),history=[],currentPage='',documentHistory=[],toastTimer;
let positions=new Map();
const unitByPage=new Map(D.units.map(u=>[u.page,u]));
const currentSelected=()=>nodesById.get(state.selected);
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3500);}
function tag(text,cls=''){return '<span class="tag '+cls+'">'+esc(text)+'</span>';}
function targetParts(raw,owner=''){
 const target=String(raw).replace(/^!?\[\[|\]\]$/g,'').split('|')[0],hash=target.indexOf('#');
 let page=(hash<0?target:target.slice(0,hash)).replace(/\.md$/,'');page=D.aliases[page]||page||owner;
 return {page,anchor:hash<0?'':target.slice(hash+1)};
}
function sourceLabel(raw){const t=targetParts(raw),u=unitByPage.get(t.page);return (u?.title||(t.page.endsWith('/notes')?'Примечание издания':D.pages[t.page]?.title||t.page))+(t.anchor?' · '+t.anchor.replace('^',''):'');}
function sourceButton(source){const target=source.replace(/^\[\[|\]\]$/g,'');return '<button class="source-link" data-target="'+esc(target)+'">'+esc(sourceLabel(source))+' ↗</button>';}
function entityButton(id,detail=''){return '<button class="entity-link" data-entity="'+esc(id)+'">'+esc(nodesById.get(id)?.title||id)+(detail?'<small>'+esc(detail)+'</small>':'')+'</button>';}
function sourcesHTML(sources){const unique=[...new Set(sources)];return unique.slice(0,5).map(sourceButton).join('')+(unique.length>5?'<details><summary class="micro">Все источники ('+unique.length+')</summary>'+unique.slice(5).map(sourceButton).join('')+'</details>':'');}
function renderMarkdown(text,owner=''){
 let markdown=text.replace(/<!--.*?-->/gs,'');
 markdown=markdown.replace(/!\[\[([^\]\n]+)\]\]/g,(_,inside)=>{const [path,label]=inside.split('|');if(!/\.(png|jpe?g|webp|gif|svg)$/i.test(path))return '![['+inside+']]';return '<img loading="lazy" src="'+asset(path)+'" alt="Художественная иллюстрация" />';});
 markdown=markdown.replace(/\[\[([^\]\n]+)\]\]/g,(_,inside)=>{const [target,label]=inside.split('|');const note=target.includes('/notes#^note');return (note?'<sup>':'')+'<a href="#" data-target="'+esc(target||owner)+'">'+esc(note?'['+(label||sourceLabel(target))+']':label||sourceLabel(target))+'</a>'+(note?'</sup>':'');});
 markdown=markdown.replace(/^\^([\w-]+)\s*$/gm,'');
 const html=DOMPurify.sanitize(marked.parse(markdown),{ADD_ATTR:['data-target'],FORBID_TAGS:['style','iframe','form','input','script'],FORBID_ATTR:['style']});
 const holder=document.createElement('div');holder.innerHTML=html;
 holder.querySelectorAll('a:not([data-target])').forEach(a=>{
  const href=a.getAttribute('href')||'';
  if(/^(https?:)/i.test(href)){a.target='_blank';a.rel='noopener noreferrer';}
  else if(href.startsWith('#')){a.dataset.heading=decodeURIComponent(href.slice(1));a.href='#';}
  else if(!/^[a-z]+:/i.test(href)){let path=href.replace(/^\.\//,'').replace(/\.md(?=#|$)/,'');if(!path.startsWith('wiki/')&&!path.startsWith('source/'))path=owner.slice(0,owner.lastIndexOf('/')+1)+path;if(D.pages[targetParts(path).page])a.dataset.target=path;else a.href=asset(path);}
 });return holder.innerHTML;
}
for(const kind of [...new Set(D.relations.map(e=>e.kind))])$('relation').add(new Option(REL[kind]||kind,kind));
for(const n of D.nodes.filter(n=>n.type==='character'))$('participant').add(new Option(n.title,n.id));
for(const n of D.nodes.filter(n=>n.type==='place'))$('place').add(new Option(n.title,n.id));
$('export-date').textContent='Экспорт: '+new Date(D.exported_at).toLocaleString('ru-RU',{timeZone:'Europe/Moscow',dateStyle:'short',timeStyle:'short'});
function syncControls(){
 document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.mode===state.mode)));
 document.querySelectorAll('[name=layer]').forEach(i=>i.checked=state.layers.has(i.value));
 for(const [id,key]of [['importance','importance'],['relation','relation'],['act','act'],['participant','participant'],['place','place'],['event-status','status'],['truth','truth'],['chain','chain']])$(id).value=state[key];
 $('analysis').checked=state.analysis;$('show-before').checked=state.before;
 $('character-filters').hidden=state.mode!=='characters';$('event-filters').hidden=state.mode==='characters';
}
function fit(animate=true){
 if(!world||!view.nodes.length)return;
 const box=world.node().getBBox(),width=$('graph').clientWidth,height=$('graph').clientHeight,top=140,bottom=70;
 const scale=Math.max(.035,Math.min(1.12,(width-72)/Math.max(1,box.width),(height-top-bottom)/Math.max(1,box.height)));
 const t=d3.zoomIdentity.translate((width-box.width*scale)/2-box.x*scale,top+(height-top-bottom-box.height*scale)/2-box.y*scale).scale(scale);
 if(animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches)graph.transition().duration(300).call(zoom.transform,t);else graph.call(zoom.transform,t);
}
function focusNode(id){const n=view.nodes.find(n=>n.id===id);if(!n)return;const w=$('graph').clientWidth,h=$('graph').clientHeight,k=Math.max(state.mode==='characters'?.9:.85,Math.min(1.2,d3.zoomTransform(graph.node()).k));graph.call(zoom.transform,d3.zoomIdentity.translate(w/2-n.x*k,h/2+25-n.y*k).scale(k));}
function splitLabel(text,max=28,maxLines=3){const lines=[''];for(const w of text.split(/\s+/)){const last=lines.length-1;if((lines[last]+' '+w).length>max&&lines[last])lines.push(w);else lines[last]+=(lines[last]?' ':'')+w;}return lines.slice(0,maxLines).map((l,i)=>i===maxLines-1&&lines.length>maxLines?l+'…':l);}
function addLines(selection,text,max,x,y,lineHeight=15,maxLines=3){const lines=splitLabel(text,max,maxLines);selection.selectAll('tspan').data(lines).join('tspan').attr('x',x).attr('y',(_,i)=>y+i*lineHeight).text(l=>l);return lines.length;}
function charLayout(nodes,edges){
 let offset=210;const decorations=[];
 for(const editorial of [false,true]){
  const group=nodes.filter(n=>(C.nodeLayer(n)==='editorial')===editorial);if(!group.length)continue;
  const ids=new Set(group.map(n=>n.id)),links=edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).map(e=>({...e}));
  const centerX=570,centerY=offset+270;
  group.forEach((n,i)=>{n.radius={main:43,secondary:31,episodic:23}[n.viewer.importance];const p=positions.get(n.id),angle=i/group.length*Math.PI*2;n.x=p?.x??centerX+Math.cos(angle)*310;n.y=p?.y??centerY+Math.sin(angle)*260;});
  const sim=d3.forceSimulation(group).randomSource(d3.randomLcg(.413)).force('link',d3.forceLink(links).id(n=>n.id).distance(e=>e.kind==='family'?230:260).strength(.18)).force('charge',d3.forceManyBody().strength(-1350)).force('collision',d3.forceCollide().radius(n=>n.radius+49).iterations(3)).force('x',d3.forceX(centerX).strength(.025)).force('y',d3.forceY(centerY).strength(.12)).stop();
  for(let i=0;i<350;i++)sim.tick();
  if(editorial){const minY=Math.min(...group.map(n=>n.y));group.forEach(n=>n.y+=offset-minY);decorations.push({type:'title',x:Math.min(...group.map(n=>n.x))-30,y:offset-70,text:'Редакторский аппарат · исполнители и роли'});}
  offset=Math.max(...group.map(n=>n.y))+240;group.forEach(n=>positions.set(n.id,{x:n.x,y:n.y}));
 }return {decorations};
}
function render(){
 syncControls();view=C.project(D,state);
 const titles={characters:['ЛЮДИ И ОТНОШЕНИЯ','Карта персонажей','Кого связывают любовь, родство, деньги и обещания.'],timeline:['СЮЖЕТ ПО ПОРЯДКУ ТЕКСТА','Хронология событий','Примерный порядок событий по тексту пьесы. Вертикаль — места.'],dependencies:['ПРИЧИНЫ И ПОСЛЕДСТВИЯ','Зависимости событий','Как поступки, решения и условия меняют ход пьесы.']};
 const [k,t,description]=titles[state.mode];$('view-kicker').textContent=k;$('view-title').textContent=t;$('view-description').textContent=description;
 $('graph-count').innerHTML=esc(view.nodes.length)+(state.mode==='characters'?' персонажей':' событий')+'<br>'+esc(view.edges.length)+' связей';
 $('graph').setAttribute('aria-label','Интерактивный граф: '+t);
 $('canvas-hint').textContent=state.mode==='characters'?'Наведите на персонажа · Нажмите, чтобы закрепить карточку':state.mode==='timeline'?'Одно событие — один узел. Повторные упоминания доступны в карточке; порядок текста не доказывает причинность.':'Нет ребра — зависимость не установлена. Одна колонка не доказывает одновременность.';
 $('legend-content').innerHTML=state.mode==='characters'?'<div class="legend-item"><i class="dot" style="background:var(--female)"></i> Женский пол</div><div class="legend-item"><i class="dot" style="background:var(--male)"></i> Мужской пол</div><div class="legend-item"><i class="dot" style="background:var(--unknown)"></i> Не установлен</div><p>Размер — редакторская оценка сюжетной роли. Стрелка направлена от субъекта отношения к другому лицу.</p>':'<div class="legend-item"><i class="sample-line"></i> Причина → последствие</div><div class="legend-item"><i class="sample-line" style="border-color:#b08f5d"></i> Условие → событие</div><div class="legend-item"><i class="sample-line" style="border-color:#b16c5f"></i> Препятствие</div><div class="legend-item"><i class="sample-line" style="border-top-style:dotted"></i> Раньше (по запросу)</div>';
 $('empty').hidden=!!view.nodes.length;graph.selectAll('*').remove();
 const defs=graph.append('defs');for(const [kind,color]of [['normal','#9caa98'],['requires','#b08f5d'],['prevents','#b16c5f'],['before','#aaa799']])defs.append('marker').attr('id','arrow-'+kind).attr('viewBox','0 -4 8 8').attr('refX',7).attr('refY',0).attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto').append('path').attr('d','M0,-3L7,0L0,3Z').attr('fill',color);
 world=graph.append('g').attr('class','world');zoom=d3.zoom().scaleExtent([.025,3.2]).on('zoom',event=>{world.attr('transform',event.transform);$('zoom-level').textContent=Math.round(event.transform.k*100)+'%';});graph.call(zoom).on('dblclick.zoom',null);
 const layout=state.mode==='characters'?charLayout(view.nodes,view.edges):state.mode==='timeline'?C.timelineLayout(view.nodes,view.edges):C.dependencyLayout(view.nodes,view.edges);
 const decor=world.append('g').attr('class','decorations');
 for(const d of layout.decorations){if(d.type==='lane'){decor.append('rect').attr('class','lane-bg').attr('x',d.x).attr('y',d.y).attr('width',d.width).attr('height',d.height).attr('rx',9);decor.append('text').attr('class','lane-title').attr('x',d.x+12).attr('y',d.y+20).text(d.text);}else decor.append('text').attr('class',d.type==='title'?'group-title':d.type==='time'?'time-label':'group-note').attr('x',d.x).attr('y',d.y).text(d.text);}
 const lookup=new Map(view.nodes.map(n=>[n.id,n]));
 const pairCount=new Map();view.edges.forEach(e=>{e.a=C.occurrenceEndpoint?.(view.nodes,e.source,D.facts[e.fact_ids[0]])||lookup.get(e.source);e.b=C.occurrenceEndpoint?.(view.nodes,e.target,D.facts[e.fact_ids[0]])||lookup.get(e.target);const key=[e.source,e.target].sort().join('\u0000');e.parallel=pairCount.get(key)||0;pairCount.set(key,e.parallel+1);});
 edgeGroups=world.append('g').attr('class','edges').selectAll('g').data(view.edges).join('g').attr('class',e=>'edge kind-'+e.kind+' scope-'+e.scope).attr('tabindex',0).attr('role','button').attr('aria-label',e=>e.source+' → '+e.label+' → '+e.target).on('click',(event,e)=>{event.stopPropagation();showEdge(e);}).on('keydown',(event,e)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();showEdge(e);}});
 edgeGroups.append('path').attr('class','line').attr('marker-end',e=>'url(#arrow-'+(['requires','prevents','before'].includes(e.kind)?e.kind:'normal')+')').attr('stroke-dasharray',e=>e.truth_status!=='confirmed'?'5 5':null);edgeGroups.append('path').attr('class','hit');edgeGroups.append('text').attr('class','edge-label').attr('text-anchor','middle');
 nodeGroups=world.append('g').attr('class','nodes').selectAll('g').data(view.nodes).join('g').attr('class',n=>'node '+(state.mode==='characters'?'character':'event')).attr('data-id',n=>n.id).attr('data-instance',n=>n.instanceId||n.id).attr('tabindex',0).attr('role','button').attr('aria-label',n=>n.title+' · '+(n.type==='character'?ROLE[n.viewer.importance]:STATUS[n.event_status])+(n.occurrence?' · '+sourceLabel('source/'+D.book_id+'/bychapter/'+n.occurrence.unit_id+'#^'+n.occurrence.block_id):'')).on('pointerenter',(event,n)=>{if(event.pointerType==='mouse'&&!state.pinned)selectNode(n.id,false,false,n.occurrence);}).on('focus',(event,n)=>{if(!state.pinned)selectNode(n.id,false,false,n.occurrence);}).on('click',(event,n)=>{event.stopPropagation();selectNode(n.id,true,true,n.occurrence);}).on('keydown',(event,n)=>{
  if(event.key==='Enter'||event.key===' '){event.preventDefault();selectNode(n.id,true,true,n.occurrence);}
  if(['ArrowRight','ArrowLeft','ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();const index=view.nodes.indexOf(n),step=['ArrowRight','ArrowDown'].includes(event.key)?1:-1,next=view.nodes[(index+step+view.nodes.length)%view.nodes.length];nodeGroups.filter(d=>d===next).node()?.focus({preventScroll:true});focusNode(next.id);}
 });
 if(state.mode==='characters'){
  nodeGroups.each(function(n,i){const el=d3.select(this),r=n.radius,color=COLORS[n.viewer.gender];el.append('circle').attr('class','halo').attr('r',r+8);el.append('circle').attr('class','portrait-bg').attr('r',r).attr('fill',d3.color(color).copy({opacity:.09})).attr('stroke',color);if(n.portrait){const clip='portrait-'+i;defs.append('clipPath').attr('id',clip).append('circle').attr('r',r-3);el.append('image').attr('href',asset(n.portrait)).attr('x',-r+3).attr('y',-r+3).attr('width',r*2-6).attr('height',r*2-6).attr('preserveAspectRatio','xMidYMid meet').attr('clip-path','url(#'+clip+')');}else el.append('text').attr('text-anchor','middle').attr('dy','.33em').attr('fill',color).attr('font-family','Georgia').attr('font-size',r*.7).text(n.title.split(/\s+/).slice(0,2).map(w=>w[0]).join(''));
   const text=el.append('text').attr('class','node-label'),lines=addLines(text,n.title,24,0,r+22,16,2);el.append('text').attr('class','node-role').attr('y',r+22+lines*16).text(n.viewer.layer==='story'?ROLE[n.viewer.importance]:LAYER[n.viewer.layer]);});
  nodeGroups.call(d3.drag().clickDistance(5).on('drag',function(event,n){d3.select(this).raise();n.x=event.x;n.y=event.y;positions.set(n.id,{x:n.x,y:n.y});updateGeometry();arrangeEdgeLabels();}));
 }else{
  nodeGroups.each(function(n){const el=d3.select(this),width=n.width,height=n.height;el.append('rect').attr('x',-width/2).attr('y',-height/2).attr('width',width).attr('height',height).attr('rx',8);el.append('circle').attr('class','status-mark').attr('cx',-width/2+14).attr('cy',-height/2+15).attr('r',3).attr('fill',n.event_status==='planned'?'#ba9a5f':'#63866a');el.append('text').attr('class','event-meta').attr('x',-width/2+24).attr('y',-height/2+18).text(n.occurrence?(unitByPage.get('source/'+D.book_id+'/bychapter/'+n.occurrence.unit_id)?.title.replace(' — Явление ',' · ')+' · '+n.occurrence.block_id):n.viewer.layer==='editorial'?'Аппарат издания':STATUS[n.event_status]);addLines(el.append('text'),n.title,31,-width/2+13,-height/2+38,14,3);});
 }updateGeometry();highlight();if(state.chain&&state.selected)focusNode(state.selected);else fit(false);
}
function updateGeometry(){
 if(!nodeGroups)return;nodeGroups.attr('transform',n=>'translate('+n.x+','+n.y+')');
 edgeGroups.each(function(e){const a=e.a,b=e.b,dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len;let ax,ay,bx,by;
  if(state.mode==='characters'){ax=a.x+ux*(a.radius+3);ay=a.y+uy*(a.radius+3);bx=b.x-ux*(b.radius+9);by=b.y-uy*(b.radius+9);}else{const horizontal=Math.abs(dx)>=Math.abs(dy)*1.2;ax=a.x+(horizontal?Math.sign(dx)*a.width/2:0);ay=a.y+(horizontal?0:Math.sign(dy)*a.height/2);bx=b.x-(horizontal?Math.sign(dx)*(b.width/2+7):0);by=b.y-(horizontal?0:Math.sign(dy)*(b.height/2+7));}
  const offset=state.mode==='characters'?(e.parallel+1)*23:14+e.parallel*16,sign=e.source.localeCompare(e.target,'ru')<0?1:-1,cx=(ax+bx)/2-uy*offset*sign,cy=(ay+by)/2+ux*offset*sign,path='M'+ax+','+ay+'Q'+cx+','+cy+' '+bx+','+by,el=d3.select(this);el.selectAll('path').attr('d',path);addLines(el.select('text'),(e.scope==='analysis'?'∴ ':'')+e.label,state.mode==='characters'?30:20,(ax+2*cx+bx)/4,(ay+2*cy+by)/4-5,12,2);
 });
}
function arrangeEdgeLabels(){
 if(state.mode!=='characters'||!edgeGroups)return;
 const obstacles=view.nodes.map(n=>({x:n.x-n.radius-8,y:n.y-n.radius-8,w:n.radius*2+16,h:n.radius*2+65})),placed=[];
 const overlap=(a,b)=>Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));
 const elements=edgeGroups.nodes().sort((a,b)=>{const ea=d3.select(a).datum(),eb=d3.select(b).datum();return Number(eb.source===state.selected||eb.target===state.selected)-Number(ea.source===state.selected||ea.target===state.selected);});
 for(const element of elements){
  const e=d3.select(element).datum(),text=d3.select(element).select('text'),box=text.node().getBBox(),a=e.a,b=e.b,dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len;
  let best=null;
  for(const t of [.5,.32,.68,.2,.8])for(const offset of [18,-18,36,-36,58,-58,84,-84]){
   const x=a.x+dx*t-uy*offset,y=a.y+dy*t+ux*offset,r={x:x-box.width/2-5,y:y-11,w:box.width+10,h:box.height+7};
   const score=obstacles.reduce((v,b)=>v+overlap(r,b)*6,0)+placed.reduce((v,b)=>v+overlap(r,b)*3,0)+Math.abs(t-.5)*50+Math.abs(offset)*.15;
   if(!best||score<best.score)best={score,x,y,r};
  }
  const old=text.select('tspan').attr('y');text.selectAll('tspan').attr('x',best.x).attr('y',function(){return Number(this.getAttribute('y'))-Number(old)+best.y;});placed.push(best.r);
 }
}
function highlight(){if(!nodeGroups||!edgeGroups)return;arrangeEdgeLabels();const selected=state.selected,ids=new Set(state.chain?view.nodes.map(n=>n.id):selected?[selected]:[]);view.edges.forEach(e=>{if(e.source===selected||e.target===selected){ids.add(e.source);ids.add(e.target);}});nodeGroups.classed('selected',n=>n.id===selected).classed('dim',n=>!!selected&&!ids.has(n.id));edgeGroups.classed('near',e=>e.source===selected||e.target===selected).classed('dim',e=>!!selected&&!state.chain&&e.source!==selected&&e.target!==selected);}
function selectNode(id,pin=false,remember=false,occurrence=null){const n=nodesById.get(id);if(!n)return;if(remember&&state.selected&&state.selected!==id)history.push(state.selected);state.selected=id;state.pinned=pin;state.occurrence=occurrence;renderCard(n);highlight();if(pin){$('inspector').classList.add('open');if(remember)focusNode(id);}}
function renderCard(n){
 $('panel-label').textContent=TYPE[n.type]||'WIKI КНИГИ';$('pin').hidden=false;$('pin').setAttribute('aria-pressed',String(state.pinned));$('pin').textContent=state.pinned?'Закреплено · снять':'Закрепить';$('back-card').hidden=!history.length;
 let html='<div class="subtitle">'+esc(n.type==='character'?ROLE[n.viewer.importance]:STATUS[n.event_status]||TYPE[n.type])+'</div><h2>'+esc(n.title)+'</h2>';
 if(n.portrait)html+='<div class="card-image"><img src="'+asset(n.portrait)+'" alt="Акварельный образ: '+esc(n.title)+'"></div><p class="art-note">Художественная интерпретация. Внешность по визуальным референсам фильма; это оформление, а не факт пьесы.</p>';
 html+='<div class="tag-row">'+tag(LAYER[n.viewer.layer],n.viewer.layer==='editorial'?'editorial':'')+(n.type==='event'?tag(STATUS[n.event_status]):'')+'</div><div class="card-summary">'+renderMarkdown(n.summary,n.page)+'</div>';
 if(n.aliases.length)html+='<p class="micro">Также: '+esc(n.aliases.join(', '))+'</p>';
 if(n.type==='event')html+='<p class="micro">'+esc(n.viewer.time_label)+'</p>';
 html+='<div class="card-actions"><button class="primary" data-full="'+esc(n.id)+'">Полная wiki-карточка ↗</button>';
 const source=state.occurrence||n.occurrences[0];if(source)html+='<button data-target="source/'+D.book_id+'/bychapter/'+esc(source.unit_id)+'#^'+esc(source.block_id)+'">Читать фрагмент ↗</button>';html+='</div>';
 if(n.type==='character'){
  const relations=D.relations.filter(e=>(e.source===n.id||e.target===n.id)&&state.layers.has(nodesById.get(e.source)?.viewer.layer)&&state.layers.has(nodesById.get(e.target)?.viewer.layer)&&(!state.truth||e.truth_status===state.truth)&&(state.analysis||e.scope!=='analysis')&&(!state.relation||state.relation===e.kind));
  html+='<section class="card-section"><h3>Отношения <span class="micro">'+relations.length+'</span></h3>';
  for(const e of relations)html+='<button class="entity-link" data-edge="'+esc(e.id)+'">'+esc(e.source===n.id?e.target:e.source)+'<small>'+esc(e.source)+' → '+esc(e.label)+' → '+esc(e.target)+' · '+esc(TRUTH[e.truth_status])+'</small></button>';
  html+=(relations.length?'':'<p class="micro">Нет отношений в выбранных фильтрах.</p>')+'</section>';
  const events=D.nodes.filter(e=>e.type==='event'&&e.participants.includes(n.id)&&e.viewer.layer!=='editorial');
  html+='<section class="card-section"><h3>События с участием персонажа</h3><button data-events="'+esc(n.id)+'">Показать на хронологии</button>'+events.slice(0,6).map(e=>entityButton(e.id,STATUS[e.event_status])).join('')+(events.length>6?'<details><summary class="micro">Все события ('+events.length+')</summary>'+events.slice(6).map(e=>entityButton(e.id)).join('')+'</details>':'')+'</section>';
  html+='<details class="card-section"><summary class="micro">Размер и цвет узла</summary><p class="micro">'+esc(n.viewer.importance_method)+'. '+esc(n.viewer.gender_method)+'.</p>'+sourcesHTML(n.viewer.gender_sources||[])+'</details>';
 }else if(n.type==='event'){
  html+='<section class="card-section"><h3>Участники</h3>'+n.participants.map(id=>entityButton(id,D.facts[n.fact_ids.find(fid=>D.facts[fid].predicate==='participates'&&D.facts[fid].object===id)]?.role||'участник')).join('')+'</section><section class="card-section"><h3>Места</h3>'+(n.places.length?n.places.map(id=>entityButton(id)).join(''):'<p class="micro">Место не установлено.</p>')+'</section>';
  const deps=D.dependencies.filter(e=>(e.source===n.id||e.target===n.id)&&(state.analysis||e.scope!=='analysis')&&(!state.truth||e.truth_status===state.truth));
  html+='<section class="card-section"><h3>Причины, условия и последствия</h3>'+deps.map(e=>'<button class="entity-link" data-edge="'+esc(e.id)+'">'+esc(e.source===n.id?e.target:e.source)+'<small>'+esc((e.scope==='analysis'?'∴ ':'')+e.source+' → '+e.label+' → '+e.target)+'</small></button>').join('')+(deps.length?'':'<p class="micro">Зависимости не установлены. Это не доказывает независимость события.</p>')+'</section>';
  const parts=n.fact_ids.map(id=>D.facts[id]).filter(f=>f.predicate==='part_of');if(parts.length)html+='<section class="card-section"><h3>Вложенность</h3>'+parts.map(f=>entityButton(f.object,'часть события')).join('')+'</section>';
  html+='<section class="card-section"><h3>Все появления в тексте</h3>'+n.occurrences.map(o=>sourceButton('[[source/'+D.book_id+'/bychapter/'+o.unit_id+'#^'+o.block_id+']]')+'<p class="micro">'+esc(o.kind)+'</p>').join('')+'</section>';
 }
 html+='<section class="card-section"><h3>Основания в издании</h3>'+sourcesHTML(n.sources)+'</section>';$('card-content').innerHTML=html;
}
function welcome(){state.selected=null;state.pinned=false;state.occurrence=null;$('panel-label').textContent='WIKI КНИГИ';$('pin').hidden=true;$('back-card').hidden=true;$('card-content').innerHTML='<div class="welcome"><div class="welcome-mark">∴</div><span class="eyebrow">ЛИТЕРАТУРНЫЙ АТЛАС</span><h2>За каждой связью —<br>история.</h2><p>Наведите на узел, чтобы познакомиться с персонажем или событием. Нажмите, чтобы закрепить заметку и открыть её источники.</p><div class="card-section"><h3>Начать с Ларисы</h3>'+entityButton('Лариса Огудалова','Дочь Хариты Игнатьевны · главная героиня')+'</div><p class="micro">Здесь можно прочесть полную пьесу и проверить, на каких репликах построена карта.</p></div>';highlight();}
function showEdge(edge){
 state.pinned=true;$('pin').hidden=false;$('pin').setAttribute('aria-pressed','true');$('pin').textContent='Закреплено · снять';$('panel-label').textContent='ОСНОВАНИЯ СВЯЗИ';$('inspector').classList.add('open');edgeGroups?.classed('selected',e=>e.id===edge.id);
 let html='<div class="subtitle">'+esc(REL[edge.kind]||edge.label)+'</div><h2>'+esc(edge.label)+'</h2>'+entityButton(edge.source,'Откуда направлена связь')+entityButton(edge.target,'Куда направлена связь')+'<div class="tag-row">'+tag(SCOPE[edge.scope],edge.scope)+tag(TRUTH[edge.truth_status])+'</div>';
 for(const id of edge.fact_ids){const f=D.facts[id];html+='<section class="fact-item"><p>'+esc(f.explanation||f.label)+'</p><small>'+esc(SCOPE[f.scope])+' · '+esc(TRUTH[f.truth_status])+'</small>';if(f.at_event)html+=entityButton(f.at_event,'Связанное событие');if(f.valid_from)html+=entityButton(f.valid_from,'Действует начиная с');if(f.valid_until)html+=entityButton(f.valid_until,'Действует до');html+=sourcesHTML(f.sources)+'<details><summary class="micro">Исходный факт</summary><small>'+esc(f.fact_id)+'</small><p class="micro">'+esc(f.subject)+' → '+esc(f.predicate)+' → '+esc(f.object)+'</p></details></section>';}
 if(edge.kind==='requires')html+='<p class="micro">На схеме условие направлено к зависимому событию. В исходном факте «'+esc(edge.target)+' требует '+esc(edge.source)+'» направление обратное.</p>';$('card-content').innerHTML=html;
}
function navigateEntity(id){
 const n=nodesById.get(id);if(!n)return;if(state.selected&&state.selected!==id)history.push(state.selected);const targetMode=n.type==='character'?'characters':n.type==='event'?'timeline':null;
 if(targetMode){if((state.mode==='characters')!==(targetMode==='characters'))state.mode=targetMode;state.layers.add(n.viewer.layer);state.importance='';state.act='';state.participant='';state.place='';state.status='';state.chain='';state.selected=id;state.pinned=true;render();selectNode(id,true,false);focusNode(id);}else selectNode(id,true,false);
}
function navigateTarget(raw,owner=currentPage){const t=targetParts(raw,owner);if(D.pages[t.page])openPage(t.page,t.anchor);else{const path=t.page+(t.page.endsWith('.json')||t.page.endsWith('.png')?'':'.md');window.open(asset(path),'_blank','noopener');}}
function buildTOC(activePage){let html='<h3>Оглавление пьесы</h3>',lastAct='';for(const u of D.units){const act=u.title.match(/^Действие (\d)/)?.[1];if(act&&act!==lastAct){html+='<h3>Действие '+['','I','II','III','IV'][Number(act)]+'</h3>';lastAct=act;}html+='<button data-page="'+esc(u.page)+'" class="'+(activePage===u.page?'active':'')+'">'+esc(u.classification==='canon'?u.title.replace(/^Действие \d — /,''):u.title)+'</button>';}html+='<h3>Аппарат и wiki</h3><button data-page="source/'+D.book_id+'/notes">Примечания и переводы</button><button data-page="wiki/viewer-audit.'+D.book_id+'">Проверка данных viewer</button><button data-page="wiki/audit.'+D.book_id+'">Неопределённости wiki</button>';$('toc').innerHTML=html;}
function openPage(page,anchor='',push=true){
 const doc=D.pages[page];if(!doc){toast('Страница отсутствует в пакете. Обновите экспорт данных.');return;}
 if(push&&currentPage&&$('document-dialog').open)documentHistory.push({page:currentPage,scroll:$('document-body').scrollTop});currentPage=page;$('document-title').textContent=doc.title;buildTOC(page);let html='';const unit=unitByPage.get(page);
 if(unit){
  html='<h1>'+esc(unit.title)+'</h1><div class="source-header">'+esc(unit.classification==='editorial'?'Редакционный комментарий. Исторические сведения отдельно не проверялись.':unit.classification==='framing'?'Авторская титульная рамка.':unit.classification==='cast'?'Авторский состав лиц и обстановка действия.':'Полный текст явления. Выделение показывает адрес источника, а не границы всего события.')+'</div>';
  if(unit.classification==='framing')html+='<p>'+esc(unit.source_title||unit.title)+'</p>';
  for(const b of unit.blocks)html+='<section id="block-'+esc(b.id)+'" class="source-block'+(anchor==='^'+b.id?' highlight':'')+'">'+renderMarkdown(b.markdown,page)+'<a class="block-id" href="#" data-target="'+esc(page+'#^'+b.id)+'">'+esc(b.id)+'</a></section>';
 }else if(page===`source/${D.book_id}/notes`){html='<h1>Примечания и переводы</h1><p class="source-header">Авторскими помечены только переводы № 6–8.</p>';for(const note of D.notes)html+='<section id="block-'+esc(note.id)+'" class="source-block'+(anchor==='^'+note.id?' highlight':'')+'"><h3>Примечание '+esc(note.title)+'</h3>'+note.blocks.map(b=>'<p>'+esc(b)+'</p>').join('')+'</section>';}
 else{html=renderMarkdown(doc.body,page);const n=byPage.get(page);if(n)html+='<details><summary>Структурированные факты ('+n.fact_ids.length+')</summary>'+n.fact_ids.map(id=>{const f=D.facts[id];return '<section class="fact-item"><small>'+esc(id)+' · '+esc(SCOPE[f.scope])+' · '+esc(TRUTH[f.truth_status])+'</small><p>'+esc(f.predicate)+' → '+(f.object?'<button class="link-button" data-entity="'+esc(f.object)+'">'+esc(f.object)+'</button>':esc(f.value))+'</p><p>'+esc(f.explanation||'')+'</p>'+sourcesHTML(f.sources)+'</section>';}).join('')+'</details>';}
 $('document-body').innerHTML=html;if(!$('document-dialog').open)$('document-dialog').showModal();$('document-body').scrollTop=0;requestAnimationFrame(()=>{if(anchor.startsWith('^'))$('document-body').querySelector('#block-'+CSS.escape(anchor.slice(1)))?.scrollIntoView({block:'center'});else if(anchor)scrollHeading(anchor);});
}
function scrollHeading(anchor){const key=norm(anchor).replace(/[^\p{L}\p{N}]+/gu,'');[...$('document-body').querySelectorAll('h1,h2,h3,h4')].find(h=>norm(h.textContent).replace(/[^\p{L}\p{N}]+/gu,'')===key)?.scrollIntoView({block:'start'});}
function closeDocument(){if($('document-dialog').open)$('document-dialog').close();documentHistory=[];currentPage='';}
function reset(){const mode=state.mode;state={mode,layers:new Set(['story']),importance:'',relation:'',act:'',participant:'',place:'',status:'',truth:'',analysis:true,before:false,chain:'',selected:null,pinned:false};$('search').value='';$('search-results').hidden=true;history=[];welcome();render();}
document.addEventListener('click',event=>{
 const b=event.target.closest('[data-entity],[data-target],[data-full],[data-edge],[data-events],[data-page],[data-heading]');if(!b)return;event.preventDefault();
 if(b.dataset.heading){scrollHeading(b.dataset.heading);return;}
 if(b.dataset.target){navigateTarget(b.dataset.target);return;}
 if(b.dataset.page){openPage(b.dataset.page);return;}
 if(b.dataset.full){openPage(nodesById.get(b.dataset.full).page);return;}
 if(b.dataset.entity){closeDocument();navigateEntity(b.dataset.entity);return;}
 if(b.dataset.edge){const e=[...D.relations,...D.dependencies].find(e=>e.id===b.dataset.edge);if(e)showEdge(e);return;}
 if(b.dataset.events){state.mode='timeline';state.participant=b.dataset.events;state.act='';state.place='';state.status='';state.chain='';state.selected=null;state.pinned=false;render();welcome();}
});
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{if(state.mode===b.dataset.mode)return;state.mode=b.dataset.mode;state.chain='';state.selected=null;state.pinned=false;welcome();render();}));
document.querySelectorAll('[name=layer]').forEach(i=>i.addEventListener('change',()=>{i.checked?state.layers.add(i.value):state.layers.delete(i.value);render();if(currentSelected())renderCard(currentSelected());}));
for(const [id,key]of [['importance','importance'],['relation','relation'],['act','act'],['participant','participant'],['place','place'],['event-status','status'],['truth','truth'],['chain','chain']])$(id).addEventListener('change',()=>{state[key]=$(id).value;if(key==='chain'&&state.chain&&!currentSelected()){state.chain='';toast('Сначала выберите событие.');}render();if(currentSelected())renderCard(currentSelected());});
$('analysis').addEventListener('change',()=>{state.analysis=$('analysis').checked;render();if(currentSelected())renderCard(currentSelected());});$('show-before').addEventListener('change',()=>{state.before=$('show-before').checked;render();});
$('reset').onclick=reset;$('empty-reset').onclick=reset;$('fit').onclick=()=>fit();$('zoom-in').onclick=()=>graph.transition().duration(150).call(zoom.scaleBy,1.35);$('zoom-out').onclick=()=>graph.transition().duration(150).call(zoom.scaleBy,1/1.35);
$('pin').onclick=()=>{state.pinned=!state.pinned;$('pin').setAttribute('aria-pressed',String(state.pinned));$('pin').textContent=state.pinned?'Закреплено · снять':'Закрепить';};
$('close-panel').onclick=()=>{$('inspector').classList.remove('open');welcome();};$('back-card').onclick=()=>{const id=history.pop();if(id){const old=history.slice();navigateEntity(id);history=old;$('back-card').hidden=!history.length;}};
$('open-reader').onclick=()=>openPage(D.units.find(u=>u.classification==='canon').page);
$('document-close').onclick=closeDocument;$('document-back').onclick=()=>{const previous=documentHistory.pop();if(previous){openPage(previous.page,'',false);$('document-body').scrollTop=previous.scroll;}else closeDocument();};
$('document-dialog').addEventListener('close',()=>{currentPage='';documentHistory=[];});$('about').onclick=()=>openPage('wiki/viewer-audit.'+D.book_id);
document.querySelector('.brand').onclick=e=>{e.preventDefault();state.mode='characters';reset();};
$('search').addEventListener('input',()=>{const query=norm($('search').value.trim()),results=$('search-results');if(!query){results.hidden=true;$('search').setAttribute('aria-expanded','false');return;}const matches=D.nodes.filter(n=>[n.title,...n.aliases].some(t=>norm(t).includes(query))).sort((a,b)=>(norm(a.title).startsWith(query)?0:1)-(norm(b.title).startsWith(query)?0:1)||({character:0,event:1,place:2}[a.type]??3)-({character:0,event:1,place:2}[b.type]??3)).slice(0,30);results.innerHTML=matches.length?matches.map(n=>'<button data-search-id="'+esc(n.id)+'">'+esc(n.title)+'<small>'+esc(TYPE[n.type])+' · '+esc(LAYER[n.viewer.layer])+'</small></button>').join(''):'<p>Ничего не найдено.</p>';results.hidden=false;$('search').setAttribute('aria-expanded','true');});
$('search-results').addEventListener('click',event=>{const b=event.target.closest('[data-search-id]');if(!b)return;navigateEntity(b.dataset.searchId);$('search-results').hidden=true;$('search').setAttribute('aria-expanded','false');});
$('search').addEventListener('keydown',event=>{if(event.key==='ArrowDown'){event.preventDefault();$('search-results').querySelector('button')?.focus();}if(event.key==='Enter')$('search-results').querySelector('button')?.click();if(event.key==='Escape'){$('search-results').hidden=true;$('search').setAttribute('aria-expanded','false');}});
document.addEventListener('pointerdown',event=>{if(!event.target.closest('.search-wrap')){$('search-results').hidden=true;$('search').setAttribute('aria-expanded','false');}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!event.target.matches('input,textarea,select')){event.preventDefault();$('search').focus();}if(event.key==='Escape'&&!$('document-dialog').open){state.pinned=false;$('inspector').classList.remove('open');welcome();}if(event.key==='Escape'){$('search-results').hidden=true;$('search').setAttribute('aria-expanded','false');}});
let resizeStart=null;$('splitter').addEventListener('pointerdown',e=>{resizeStart={x:e.clientX,width:$('inspector').clientWidth};$('splitter').setPointerCapture(e.pointerId);e.preventDefault();});
function setPanelWidth(width){const value=Math.max(300,Math.min(650,window.innerWidth-550,width));document.documentElement.style.setProperty('--panel',value+'px');$('splitter').setAttribute('aria-valuenow',String(value));}
$('splitter').addEventListener('pointermove',e=>{if(resizeStart)setPanelWidth(resizeStart.width+resizeStart.x-e.clientX);});$('splitter').addEventListener('pointerup',()=>{resizeStart=null;});$('splitter').addEventListener('pointercancel',()=>{resizeStart=null;});$('splitter').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setPanelWidth($('inspector').clientWidth+(e.key==='ArrowLeft'?20:-20));}});
welcome();render();
let previousSize='';new ResizeObserver(entries=>{const r=entries[0].contentRect,key=Math.round(r.width)+'x'+Math.round(r.height);if(key!==previousSize){previousSize=key;fit(false);}}).observe($('graph'));
window.addEventListener('error',event=>toast('Ошибка просмотра: '+event.message));
})();
