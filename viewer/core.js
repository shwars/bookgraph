/* Pure graph projections and layouts; usable in the browser and in Node checks. */
(function(root){
'use strict';
const idOf=n=>typeof n==='object'?n.id:n;
const nodeLayer=n=>n.viewer?.layer||'story';
const hasEndpoint=(e,ids)=>ids.has(idOf(e.source))&&ids.has(idOf(e.target));
const edgeAllowed=(e,state)=>(state.analysis||e.scope!=='analysis')&&(!state.truth||e.truth_status===state.truth);
function traverse(edges,id,direction){
 const visited=new Set([id]),queue=[id];
 for(let i=0;i<queue.length;i++)for(const e of edges){
  const a=idOf(e.source),b=idOf(e.target);
  const next=direction==='ancestors'?(b===queue[i]?a:null):(a===queue[i]?b:null);
  if(next&&!visited.has(next)){visited.add(next);queue.push(next);}
 }
 return visited;
}
function project(data,state){
 const character=state.mode==='characters';
 let nodes=data.nodes.filter(n=>n.type===(character?'character':'event')&&state.layers.has(nodeLayer(n)));
 if(character){if(state.importance)nodes=nodes.filter(n=>n.viewer.importance===state.importance);}
 else{
  if(state.act)nodes=nodes.filter(n=>String(n.viewer.act)===state.act);
  if(state.participant)nodes=nodes.filter(n=>n.participants.includes(state.participant));
  if(state.place)nodes=nodes.filter(n=>state.place==='__unknown'?!n.places.length:n.places.includes(state.place));
  if(state.status)nodes=nodes.filter(n=>n.event_status===state.status);
 }
 let ids=new Set(nodes.map(n=>n.id));
 let edges=(character?data.relations:data.dependencies).filter(e=>hasEndpoint(e,ids)&&edgeAllowed(e,state));
 if(character&&state.relation)edges=edges.filter(e=>e.kind===state.relation);
 if(!character&&!state.before)edges=edges.filter(e=>e.kind!=='before');
 if(!character&&state.chain&&ids.has(state.selected)){
  let chain=new Set([state.selected]);
  for(const dir of state.chain==='both'?['ancestors','descendants']:[state.chain])for(const id of traverse(edges,state.selected,dir))chain.add(id);
  nodes=nodes.filter(n=>chain.has(n.id));ids=new Set(nodes.map(n=>n.id));edges=edges.filter(e=>hasEndpoint(e,ids));
 }
 return {nodes:nodes.map(n=>({...n})),edges:edges.map(e=>({...e}))};
}
function levels(nodes,edges){
 const ids=new Set(nodes.map(n=>n.id)),incoming=new Map(nodes.map(n=>[n.id,0])),out=new Map(nodes.map(n=>[n.id,[]])),rank=new Map(nodes.map(n=>[n.id,0]));
 for(const e of edges)if(hasEndpoint(e,ids)&&e.kind!=='prevents'){incoming.set(idOf(e.target),incoming.get(idOf(e.target))+1);out.get(idOf(e.source)).push(idOf(e.target));}
 const queue=nodes.filter(n=>!incoming.get(n.id)).map(n=>n.id).sort();
 for(let i=0;i<queue.length;i++)for(const next of out.get(queue[i])){
  rank.set(next,Math.max(rank.get(next),rank.get(queue[i])+1));incoming.set(next,incoming.get(next)-1);if(!incoming.get(next))queue.push(next);
 }
 return {rank,cycle:queue.length!==nodes.length};
}
function components(nodes,edges){
 const adjacency=new Map(nodes.map(n=>[n.id,[]]));
 for(const e of edges){adjacency.get(idOf(e.source))?.push(idOf(e.target));adjacency.get(idOf(e.target))?.push(idOf(e.source));}
 const seen=new Set(),groups=[];
 for(const n of nodes){if(seen.has(n.id))continue;const ids=[n.id];seen.add(n.id);for(let i=0;i<ids.length;i++)for(const id of adjacency.get(ids[i])||[])if(!seen.has(id)){seen.add(id);ids.push(id);}groups.push(ids);}
 return groups.sort((a,b)=>b.length-a.length);
}
function dependencyLayout(nodes,edges){
 let y=160;const decorations=[],lookup=new Map(nodes.map(n=>[n.id,n]));
 for(const editorial of [false,true]){
  const subset=nodes.filter(n=>(nodeLayer(n)==='editorial')===editorial),ids=new Set(subset.map(n=>n.id)),links=edges.filter(e=>hasEndpoint(e,ids));if(!subset.length)continue;
  decorations.push({type:'title',x:30,y:y-45,text:editorial?'Редакторский аппарат · отдельный граф':'Причины, условия и последствия'});
  const isolated=[];
  for(const component of components(subset,links)){
   if(component.length===1){isolated.push(lookup.get(component[0]));continue;}
   const cset=new Set(component),members=component.map(id=>lookup.get(id)),cEdges=links.filter(e=>hasEndpoint(e,cset)),l=levels(members,cEdges),rows=new Map();
   for(const n of members.sort((a,b)=>(a.viewer.time_rank||0)-(b.viewer.time_rank||0)||a.id.localeCompare(b.id,'ru'))){const level=l.rank.get(n.id),row=rows.get(level)||0;n.x=145+level*320;n.y=y+row*120;n.width=240;n.height=76;rows.set(level,row+1);}
   y+=Math.max(...rows.values())*120+75;
   if(l.cycle)decorations.push({type:'note',x:30,y:y-20,text:'Есть цикл ограничений: проверьте основания связей.'});
  }
  if(isolated.length){decorations.push({type:'note',x:30,y:y-25,text:'События без установленных зависимостей в выбранных фильтрах'});isolated.forEach((n,i)=>{n.x=145+i%4*300;n.y=y+Math.floor(i/4)*115;n.width=240;n.height=76;});y+=Math.ceil(isolated.length/4)*115+100;}
 }
 return {decorations};
}
function timelineLayout(nodes,edges){
 const decorations=[];let baseY=160;
 const firstMention=n=>[...n.occurrences].sort((a,b)=>a.unit_id.localeCompare(b.unit_id)||a.block_id.localeCompare(b.block_id))[0];
 for(const editorial of [false,true]){
  const group=nodes.filter(n=>(nodeLayer(n)==='editorial')===editorial);if(!group.length)continue;
  decorations.push({type:'title',x:30,y:baseY-45,text:editorial?'Редакторский аппарат · даты комментария':'Примерный порядок по тексту · одно событие, один узел'});
  const bands=[];let offset=235;
  if(editorial){
   const years=[...new Set(group.map(n=>(n.date_text||'').match(/\b(18|19|20)\d{2}\b/)?.[0]||'Дата неизвестна'))].sort();
   for(const year of years){bands.push({key:year,title:year,x:offset,width:360});offset+=390;}
  }else{
   for(let act=1;act<=4;act++)if(group.some(n=>n.viewer.act===act)){bands.push({key:'act'+act,title:['I · У кофейной','II · У Огудаловых','III · Обед и отъезд','IV · Светлая летняя ночь'][act-1],x:offset,width:950});offset+=1000;}
   if(group.some(n=>!n.viewer.act)){bands.push({key:'unknown',title:'Положение в тексте не установлено',x:offset,width:400});offset+=450;}
  }
  for(const b of bands)decorations.push({type:'time',x:b.x,y:baseY-10,text:b.title});
  const groupBand=n=>editorial?((n.date_text||'').match(/\b(18|19|20)\d{2}\b/)?.[0]||'Дата неизвестна'):n.viewer.act?'act'+n.viewer.act:'unknown';
  const mentionRank=n=>{const o=firstMention(n);return o?Number(o.unit_id.split('-')[1])+Number(o.block_id.slice(1))/10000:0;};
  for(const band of bands){
   const list=group.filter(n=>groupBand(n)===band.key),values=list.map(mentionRank),lo=Math.min(...values),hi=Math.max(...values);
   for(const n of list){const fraction=editorial||hi===lo?0:(mentionRank(n)-lo)/(hi-lo);n.x=band.x+fraction*(band.width-250)+120;n.width=240;n.height=80;}
  }
  const lanes=[...new Set(group.map(n=>n.places[0]||'Место не установлено'))],order=['Кофейная Гаврилы','Бульвар Бряхимова','Дом Огудаловых','Квартира Карандышева','Волга'];
  lanes.sort((a,b)=>(order.indexOf(a)<0?99:order.indexOf(a))-(order.indexOf(b)<0?99:order.indexOf(b))||a.localeCompare(b,'ru'));
  let y=baseY+30;
  for(const lane of lanes){
   const list=group.filter(n=>(n.places[0]||'Место не установлено')===lane).sort((a,b)=>a.x-b.x||a.id.localeCompare(b.id,'ru')),ends=[];
   for(const n of list){let row=ends.findIndex(end=>end<n.x-140);if(row<0)row=ends.length;ends[row]=n.x+140;n.y=y+45+row*104;}
   const height=Math.max(1,ends.length)*104+30;decorations.push({type:'lane',x:20,y,width:offset+30,height,text:lane});y+=height+15;
  }
  baseY=y+140;
 }
 return {decorations};
}
const api={idOf,nodeLayer,project,traverse,levels,components,dependencyLayout,timelineLayout};
root.BookGraphCore=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
