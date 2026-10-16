(() => {
  'use strict';
  const map = __MAP__, districts = __DISTRICTS__, water = __WATER__;
  const metadata = __METADATA__;
  const {makeScale, classIndex, matches, csvCell} = AtlasModel;
  const $ = id => document.getElementById(id);
  const number = (value, digits = 0) => new Intl.NumberFormat('pt-BR', {maximumFractionDigits: digits}).format(value);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const features = districts.toGeoJSON().features.sort((a,b) => a.properties.cdistscodi-b.properties.cdistscodi);
  const layers = new Map();
  const state = {metric:'quantidade_bairros', query:'', selected:null, opacity:.72};
  let scale, visible = features;
  const labels = L.layerGroup().addTo(map);
  const labelMarkers = new Map();
  $('map-slot').appendChild(map.getContainer());
  map.getContainer().setAttribute('aria-label','Mapa de distritos: use as setas para navegar e as teclas + e - para ampliar ou reduzir.');
  map.zoomControl.setPosition('topright');
  L.control.scale({imperial:false,position:'bottomright'}).addTo(map);
  map.eachLayer(layer => {
    if (layer instanceof L.TileLayer) {
      layer.on('tileerror', () => { $('network-notice').hidden = false; });
      layer.on('tileload', () => { $('network-notice').hidden = true; });
    }
  });
  districts.eachLayer(layer => {
    const p = layer.feature.properties;
    layers.set(p.cdistscodi,layer);
    const label = L.marker(layer.getBounds().getCenter(), {interactive:false,keyboard:false,
      icon:L.divIcon({className:'district-map-label',html:escape(p.nome_distrito),iconSize:[44,14],iconAnchor:[22,7]})});
    labelMarkers.set(p.cdistscodi,label);
    layer.on('click', () => select(p.cdistscodi));
    layer.on('mouseover', () => layer.setStyle({weight:2.5,color:'#183f31',fillOpacity:Math.min(1,state.opacity+.13)}));
    layer.on('mouseout', () => layer.setStyle(style(layer.feature)));
    layer.bindTooltip('',{sticky:true});
  });
  water.eachLayer(layer => {
    const p = layer.feature.properties;
    layer.bindTooltip('<strong>'+escape(p.nome || 'Recurso hídrico')+'</strong><br>Bacia: '+escape(p.bacia || 'Não informada')+'<br><small>Faixa marginal do recurso hídrico</small>',{sticky:true});
  });
  function color(feature) {
    const index = classIndex(feature.properties[state.metric],scale);
    return index < 0 ? '#b8bfbc' : scale.bins[index].color;
  }
  function style(feature) {
    const selected = feature.properties.cdistscodi === state.selected;
    return {fillColor:color(feature),fillOpacity:state.opacity,color:selected?'#172f23':'#476744',weight:selected?3:1.2,opacity:.95};
  }
  function metricValue(feature) { return number(feature.properties[state.metric], state.metric==='area_km2'?1:0); }
  function select(code) {
    state.selected = code;
    if (!$('districts-toggle').checked) { $('districts-toggle').checked=true; update(); }
    renderDetails(); renderList(); districts.eachLayer(layer => layer.setStyle(style(layer.feature)));
    map.fitBounds(layers.get(code).getBounds(), {padding:[45,45],maxZoom:14,animate:!matchMedia('(prefers-reduced-motion: reduce)').matches});
  }
  function renderDetails() {
    const feature = features.find(f => f.properties.cdistscodi === state.selected);
    $('detail-content').hidden = !feature; $('overview-content').hidden = !!feature;
    if (!feature) {
      $('detail-title').textContent='Conheça o território';
      $('detail-description').textContent='Selecione um distrito no mapa ou na lista para explorar seus bairros.';
      return;
    }
    const p=feature.properties;
    $('detail-title').textContent='Distrito Sanitário '+p.nome_distrito.replace('DS ','');
    $('detail-description').textContent='Recife, Pernambuco · Código '+String(p.cdistscodi).padStart(2,'0');
    $('detail-count').textContent=p.quantidade_bairros;
    $('detail-area').textContent=number(p.area_km2,2);
    $('neighborhood-list').replaceChildren(...p.bairros.map(name=>{const node=document.createElement('span');node.textContent=name;return node;}));
  }
  function renderList() {
    $('district-list').replaceChildren(...visible.map(feature => {
      const p=feature.properties, button=document.createElement('button');
      button.className='district-item'; button.setAttribute('aria-pressed',String(p.cdistscodi===state.selected));
      button.setAttribute('aria-label',p.nome_distrito+', '+metricValue(feature)+(state.metric==='area_km2'?' quilômetros quadrados':' bairros'));
      const swatch=document.createElement('span'); swatch.className='district-swatch'; swatch.style.background=color(feature);
      const title=document.createElement('span');title.textContent=p.nome_distrito;
      const value=document.createElement('small');value.textContent=metricValue(feature)+(state.metric==='area_km2'?' km²':' bairros');
      button.append(swatch,title,value);button.onclick=()=>select(p.cdistscodi);return button;
    }));
    $('result-count').textContent=visible.length+' de '+features.length;
    $('no-results').hidden=visible.length>0;
    $('download').disabled=!visible.length;
  }
  function renderLegend() {
    $('legend-title').textContent=state.metric==='area_km2'?'Área por distrito (km²)':'Bairros por distrito';
    $('legend-bins').replaceChildren(...scale.bins.map((bin,i)=>{
      const row=document.createElement('div');row.className='legend-row';
      const swatch=document.createElement('i');swatch.style.background=bin.color;
      const label=document.createElement('span');
      if (state.metric==='quantidade_bairros') {
        const lo=Math.ceil(bin.low), hi=i===scale.bins.length-1?Math.floor(bin.high):Math.ceil(bin.high)-1;
        label.textContent=lo===hi?String(lo):lo+' – '+hi;
      } else label.textContent=number(bin.low,3)+' a '+(i===scale.bins.length-1?'':'< ')+number(bin.high,3);
      row.append(swatch,label);return row;
    }));
  }
  function renderRanking() {
    $('ranking-caption').textContent=(state.metric==='area_km2'?'Área em km²':'Quantidade de bairros')+(state.query?' · resultado da busca':'');
    const sorted=[...visible].sort((a,b)=>b.properties[state.metric]-a.properties[state.metric]);
    $('ranking').replaceChildren(...sorted.map(feature=>{
      const row=document.createElement('button');row.className='rank-row';
      row.setAttribute('aria-label','Selecionar '+feature.properties.nome_distrito);
      const title=document.createElement('span');title.textContent=feature.properties.nome_distrito;
      const track=document.createElement('i'),bar=document.createElement('b');bar.style.width=(feature.properties[state.metric]/scale.max*100)+'%';bar.style.background=color(feature);track.append(bar);
      const value=document.createElement('span');value.textContent=metricValue(feature);row.append(title,track,value);row.onclick=()=>select(feature.properties.cdistscodi);return row;
    }));
  }
  function update() {
    scale=makeScale(features.map(f=>f.properties[state.metric]));
    visible=features.filter(f=>matches(f.properties,state.query));
    if (!visible.some(f=>f.properties.cdistscodi===state.selected)) state.selected=null;
    const codes=new Set(visible.map(f=>f.properties.cdistscodi));
    labels.clearLayers();
    layers.forEach((layer,code)=>{
      if (codes.has(code)) {districts.addLayer(layer); if ($('districts-toggle').checked) labels.addLayer(labelMarkers.get(code));}
      else districts.removeLayer(layer);
      layer.setStyle(style(layer.feature));
      layer.setTooltipContent('<strong>'+escape(layer.feature.properties.nome_distrito)+'</strong><br>'+metricValue(layer.feature)+(state.metric==='area_km2'?' km²':' bairros')+'<br><small>Clique para explorar os bairros</small>');
    });
    if ($('districts-toggle').checked) districts.addTo(map); else map.removeLayer(districts);
    if ($('water-toggle').checked) water.addTo(map); else map.removeLayer(water);
    $('map-status').textContent=$('districts-toggle').checked?visible.length+' distritos visíveis':'Camada de distritos oculta';
    $('metric-help').textContent=state.metric==='area_km2'?'Quanto mais escuro, maior a área do distrito.':'Quanto mais escuro, maior o número de bairros.';
    $('interpretation').textContent=state.metric==='area_km2'?'As cores representam a área geográfica dos distritos, calculada a partir dos polígonos oficiais. A área não representa população ou demanda por serviços.':'As cores representam a quantidade de bairros em cada distrito. Não representam população, risco ou qualidade dos serviços de saúde.';
    renderList();renderLegend();renderDetails();renderRanking();
  }
  function fit() {
    if (visible.length) map.fitBounds(L.featureGroup(visible.map(f=>layers.get(f.properties.cdistscodi))).getBounds(),{padding:[35,35],animate:false});
  }
  $('metric').onchange=e=>{state.metric=e.target.value;update();};
  $('search').oninput=e=>{state.query=e.target.value;update();};
  $('search').onkeydown=e=>{if(e.key==='Enter' && visible.length===1) select(visible[0].properties.cdistscodi);};
  $('districts-toggle').onchange=update;$('water-toggle').onchange=update;
  $('opacity').oninput=e=>{state.opacity=Number(e.target.value)/100;$('opacity-value').textContent=e.target.value+'%';districts.eachLayer(layer=>layer.setStyle(style(layer.feature)));};
  $('fit').onclick=fit;
  $('reset').onclick=()=>{state.query='';state.selected=null;$('search').value='';$('districts-toggle').checked=true;update();fit();};
  $('clear-selection').onclick=()=>{state.selected=null;update();fit();};
  $('download').onclick=()=>{
    const rows=[['codigo','distrito','quantidade_bairros','area_km2','bairros'],...visible.map(f=>{const p=f.properties;return [p.cdistscodi,p.nome_distrito,p.quantidade_bairros,String(p.area_km2).replace('.',','),p.bairros.join(' | ')];})];
    const blob=new Blob(['\uFEFF'+rows.map(row=>row.map(csvCell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='distritos-recife.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  $('about-open').onclick=()=>$('about-dialog').showModal();
  $('correction-open').onclick=()=>$('about-dialog').showModal();
  $('about-close').onclick=()=>$('about-dialog').close();
  $('total-districts').textContent=features.length;
  $('total-neighborhoods').textContent=features.reduce((sum,f)=>sum+f.properties.quantidade_bairros,0);
  $('total-water').textContent=metadata.waterCount;
  $('total-area').textContent=number(features.reduce((sum,f)=>sum+f.properties.area_km2,0),1);
  const unit=document.createElement('span');unit.textContent='km²';$('total-area').append(unit);
  $('snapshot-date').textContent='Gerado em '+metadata.date;
  $('provenance').textContent='Origem desta exportação: '+metadata.source+'. Dados e biblioteca de mapa incorporados ao HTML. Apenas as ruas de fundo precisam de internet.';
  update();
  new ResizeObserver(()=>{map.invalidateSize({pan:false});}).observe($('map-canvas'));
  requestAnimationFrame(()=>{map.invalidateSize();fit();});
})();
