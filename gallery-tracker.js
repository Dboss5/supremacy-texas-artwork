(() => {
  'use strict';
  const byId = id => document.getElementById(id);
  const isPool = document.body.dataset.galleryPage === 'pool';
  const poolService = 'pool-leak-detection';
  const statusLabels = {
    in_use: 'In use · verified',
    imported_unconfirmed: 'Imported · placement unconfirmed',
    existing_unverified: 'Existing · usage unverified',
    new_not_deployed: 'New · not deployed by this batch',
    unknown: 'Usage not verified'
  };
  const statusExplanations = {
    in_use: 'This record has verified page or post placement evidence. Follow the recorded links below.',
    imported_unconfirmed: 'This image has a recorded WordPress attachment. Its current page or post placement has not been confirmed.',
    existing_unverified: 'This image belongs to the established repository collection. Its current use on WordPress has not been verified.',
    new_not_deployed: 'This intake has not deployed the image. This does not assert that the same image has never appeared elsewhere on the site.',
    unknown: 'The inventory does not provide a recognized usage status for this image.'
  };
  const serviceNames = {hvac:'HVAC','air-conditioning':'Air Conditioning',plumbing:'Plumbing',electrical:'Electrical',pest:'Pest Control','pest-control':'Pest Control','garage-doors':'Garage Doors','garage-door':'Garage Doors','holiday-lighting':'Holiday Lighting',heating:'Heating','pool-leak-detection':'Pool Leak Detection'};
  const qualityNames = {standard:'Standard',supporting:'Supporting',thumbnail:'Thumbnail'};
  const state = {images:[], byId:new Map(), batches:new Map(), categories:new Map(), selected:new Set(), page:1, pageSize:24, poolTab:'new', defaultBatch:'', filtered:[], pageRows:[], downloadController:null, downloadBatch:false};
  let toastTimer;
  const text = value => value == null ? '' : String(value);
  const humanize = value => text(value).replace(/[_-]+/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
  const titleFor = row => text(row.public_metadata?.title || row.title || row.id);
  const categoryFor = id => state.categories.get(text(id)) || humanize(id) || 'Unclassified';
  const batchFor = id => state.batches.get(text(id)) || text(id) || 'Unrecorded batch';
  const serviceFor = id => serviceNames[id] || humanize(id) || 'Unclassified';
  const statusFor = row => Object.hasOwn(statusLabels,row.usage?.status) ? row.usage.status : 'unknown';
  const placementsFor = row => Array.isArray(row.usage?.placements) ? row.usage.placements : [];
  const sourceFor = row => typeof row.source === 'object' && row.source !== null ? text(row.source.name || row.source.label) : text(row.source);
  const node = (tag, className, value) => {const n=document.createElement(tag);if(className)n.className=className;if(value!=null)n.textContent=text(value);return n;};
  const option = (value,label) => {const n=node('option','',label);n.value=value;return n;};
  function assetURL(file) {
    const path=text(file).trim();
    if(!path || /^(?:[a-z][a-z\d+.-]*:|\/|\\)/i.test(path) || /[?#]/.test(path)) return null;
    let decoded;try{decoded=decodeURIComponent(path);}catch{return null;}
    if(decoded.split(/[\\/]/).includes('..') || decoded.includes('\\'))return null;
    const url=new URL(path,new URL('.',location.href));
    return url.origin===location.origin ? url.href : null;
  }
  function webURL(value) {try{const u=new URL(text(value));return ['http:','https:'].includes(u.protocol)?u.href:null;}catch{return null;}}
  function link(url,label,className) {const a=node('a',className,label);a.href=url;return a;}
  function notify(message,persistent=false) {
    clearTimeout(toastTimer);byId('toast').textContent=message;byId('toast').hidden=false;
    if(!persistent)toastTimer=setTimeout(()=>{byId('toast').hidden=true;},6500);
  }
  function showMessage(title,description,retry=false) {
    const panel=byId('message-panel');panel.replaceChildren(node('h3','',title),node('p','',description));panel.hidden=false;
    if(retry){const b=node('button','button','Try again');b.type='button';b.addEventListener('click',loadInventory);panel.append(b);}
  }
  function statusChip(row) {const s=statusFor(row);return node('span','usage-chip usage-'+s,statusLabels[s]);}
  function displayDate(value) {
    if(!value)return 'Date not recorded';
    const d=new Date(value);if(Number.isNaN(d.getTime()))return text(value);
    return new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(d);
  }
  function buildMetrics() {
    const existing=state.images.filter(r=>r.origin==='existing');
    const pool=state.images.filter(r=>r.service===poolService);
    const fresh=pool.filter(r=>r.origin==='new'&&(!state.defaultBatch||r.batch_id===state.defaultBatch));
    const data=isPool ? [
      [fresh.length,'images in the new pool batch'],
      [pool.filter(r=>r.origin==='existing').length,'existing pool references'],
      [pool.filter(r=>statusFor(r)==='in_use').length,'pool images with verified use'],
      [new Set(fresh.map(r=>r.category).filter(Boolean)).size,'topics in the new batch']
    ] : [
      [existing.length,'existing repository images'],
      [state.images.filter(r=>statusFor(r)==='in_use').length,'images with verified use'],
      [state.images.filter(r=>statusFor(r)==='imported_unconfirmed').length,'imports awaiting placement checks'],
      [state.images.filter(r=>r.origin==='new').length,'new additions, tracked separately']
    ];
    byId('metrics').replaceChildren(...data.map(([value,label])=>{const n=node('div','metric');n.append(node('strong','',value.toLocaleString()),node('span','',label));return n;}));
    if(isPool){byId('new-tab-count').textContent=fresh.length;byId('existing-tab-count').textContent=pool.filter(r=>r.origin==='existing').length;}
  }
  function fillSelect(id,values,labels,emptyLabel) {
    const select=byId(id);if(!select)return;
    const before=select.value;
    const options=[option('',emptyLabel),...Array.from(new Set(values.map(text).filter(Boolean))).sort((a,b)=>labels(a).localeCompare(labels(b))).map(v=>option(v,labels(v)))];
    select.replaceChildren(...options);
    if(options.some(o=>o.value===before))select.value=before;
  }
  function fillFilters() {
    const rows=isPool?state.images.filter(r=>r.service===poolService):state.images;
    fillSelect('filter-service',rows.map(r=>r.service),serviceFor,'All services');
    fillSelect('filter-category',rows.map(r=>r.category),categoryFor,'All topics');
    fillSelect('filter-batch',rows.map(r=>r.batch_id),batchFor,'All batches');
    fillSelect('filter-usage',rows.map(statusFor),s=>statusLabels[s],'All statuses');
    fillSelect('filter-quality',rows.map(r=>r.quality),s=>qualityNames[s]||humanize(s),'All size classes');
  }
  function searchText(row) {
    return [row.id,titleFor(row),row.public_metadata?.alt,row.public_metadata?.caption,row.public_metadata?.description,row.file,serviceFor(row.service),categoryFor(row.category),batchFor(row.batch_id),sourceFor(row),...(Array.isArray(row.tags)?row.tags:[]),...placementsFor(row).flatMap(p=>[p.title,p.url,p.post_id])].map(text).join(' ').toLocaleLowerCase();
  }
  function filterValue(name){return byId('filter-'+name)?.value||'';}
  function resetFilters() {
    byId('search').value='';
    for(const select of document.querySelectorAll('#filters select'))select.value='';
    if(isPool){state.poolTab='new';byId('filter-batch').value=state.defaultBatch;updatePoolContext();}
    else byId('filter-origin').value='existing';
    state.page=1;render();
  }
  function updatePoolContext() {
    if(!isPool)return;
    for(const tab of document.querySelectorAll('[data-pool-tab]')){
      const active=tab.dataset.poolTab===state.poolTab;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;
    }
    byId('image-results').setAttribute('aria-labelledby','tab-'+state.poolTab);
    byId('collection-title').textContent=state.poolTab==='new'?'New pool intake':'Pool references already in the repository';
    byId('collection-description').textContent=state.poolTab==='new'?'These additions have their own batch and stable image IDs. “Not deployed by this batch” describes this intake’s activity; it does not claim an image has never appeared elsewhere.':'These are existing pool-related files. Each card identifies its original gallery, and its file path is preserved. General pool scenes provide context rather than evidence of a leak. Open an image to see its recorded usage.';
  }
  function applyFilters() {
    const query=byId('search').value.trim().toLocaleLowerCase();
    const terms=query.split(/\s+/).filter(Boolean);
    const origin=isPool?state.poolTab:filterValue('origin');
    const service=isPool?poolService:filterValue('service');
    const category=filterValue('category'),batch=filterValue('batch'),usage=filterValue('usage'),quality=filterValue('quality');
    return state.images.filter(r=>(!origin||r.origin===origin)&&(!service||r.service===service)&&(!category||text(r.category)===category)&&(!batch||text(r.batch_id)===batch)&&(!usage||statusFor(r)===usage)&&(!quality||text(r.quality)===quality)&&terms.every(t=>r._search.includes(t)));
  }
  function fallbackPreview(container) {
    const fallback=node('div','preview-fallback');fallback.append(node('span','','↗'),node('span','','Preview unavailable'));container.replaceChildren(fallback);
  }
  function downloadLink(row,className='button',label='Download ↓') {
    const url=assetURL(row.file);
    if(!url){const n=node('button',className,'File unavailable');n.type='button';n.disabled=true;return n;}
    const a=link(url,label,className);a.download=text(row.file).split('/').pop();a.setAttribute('aria-label','Download '+titleFor(row));return a;
  }
  function buildCard(row) {
    const title=titleFor(row),card=node('article','image-card'+(state.selected.has(row.id)?' is-selected':''));card.dataset.imageId=row.id;
    const visual=node('div','image-wrap'),view=node('button','image-button');view.type='button';view.setAttribute('aria-label','View details: '+title);view.addEventListener('click',()=>openDetails(row));
    const url=assetURL(row.file);
    if(url){const img=node('img');img.src=url;img.alt=text(row.public_metadata?.alt)||title;img.loading='lazy';img.decoding='async';img.addEventListener('error',()=>fallbackPreview(view),{once:true});view.append(img);}
    else fallbackPreview(view);
    const selectLabel=node('label','select-image'),checkbox=node('input');checkbox.type='checkbox';checkbox.checked=state.selected.has(row.id);checkbox.setAttribute('aria-label','Select '+title);checkbox.addEventListener('change',()=>{checkbox.checked?state.selected.add(row.id):state.selected.delete(row.id);card.classList.toggle('is-selected',checkbox.checked);updateSelection();});selectLabel.append(checkbox);
    visual.append(view,selectLabel,node('span','image-origin origin-'+(row.origin==='new'?'new':'existing'),row.origin==='new'?'New batch':'Existing'));
    const body=node('div','card-body'),kicker=node('div','card-kicker');kicker.append(node('span','',categoryFor(row.category)),node('span','dimensions',row.width&&row.height?row.width+' × '+row.height:'Size unrecorded'));
    body.append(kicker,node('h3','',title),statusChip(row),node('p','image-id',row.id));
    const tags=node('div','card-tags');
    if(!isPool)tags.append(node('span','tag',serviceFor(row.service)));
    if(row.origin==='existing'&&row.original_gallery&&(isPool||row.original_gallery!==row.service))tags.append(node('span','tag','Original: '+serviceFor(row.original_gallery)));
    if(row.category==='general-pool')tags.append(node('span','tag','Pool context'));
    if(row.quality&&row.quality!=='standard')tags.append(node('span','tag',(qualityNames[row.quality]||humanize(row.quality))+' size'));
    if(isPool&&Array.isArray(row.tags))for(const tag of row.tags.slice(0,2))tags.append(node('span','tag',humanize(tag)));
    if(tags.children.length)body.append(tags);
    const actions=node('div','card-actions'),details=node('button','button',placementsFor(row).length?'Details · '+placementsFor(row).length+' placement'+(placementsFor(row).length===1?'':'s'):'Details & usage');details.type='button';details.addEventListener('click',()=>openDetails(row));actions.append(details,downloadLink(row));card.append(visual,body,actions);return card;
  }
  function render() {
    state.filtered=applyFilters();
    const pages=Math.max(1,Math.ceil(state.filtered.length/state.pageSize));state.page=Math.min(state.page,pages);
    const start=(state.page-1)*state.pageSize;state.pageRows=state.filtered.slice(start,start+state.pageSize);
    const count=state.filtered.length;byId('result-count').textContent=count.toLocaleString()+' image'+(count===1?'':'s');
    byId('result-note').textContent=count?'Showing '+(start+1)+'–'+(start+state.pageRows.length)+' · Open a card for metadata and placement evidence.':'Try a broader topic or reset the filters.';
    byId('image-grid').replaceChildren(...state.pageRows.map(buildCard));
    byId('message-panel').hidden=!!count;
    if(!count)showMessage('No images match these filters','Your collection has not changed. Try another search, switch collections, or reset the filters.');
    byId('pagination').hidden=!count;byId('page-info').textContent='Page '+state.page+' of '+pages;
    byId('previous-page').disabled=state.page===1;byId('next-page').disabled=state.page===pages;
    byId('select-page').disabled=!count;byId('image-results').setAttribute('aria-busy','false');updateSelection();
  }
  function updateSelection() {
    const count=state.selected.size;byId('selection-bar').hidden=!count&&!state.downloadController;
    document.body.classList.toggle('has-selection',!!count||!!state.downloadController);
    byId('selection-count').textContent=state.downloadBatch?'Preparing pool batch ZIP':count.toLocaleString()+' selected';
    const hiddenCount=[...state.selected].filter(id=>!state.pageRows.some(r=>r.id===id)).length;
    byId('selection-context').textContent=hiddenCount?hiddenCount+' selection'+(hiddenCount===1?' is':'s are')+' outside this page.':'Selection stays with you across filters.';
    const allPage=state.pageRows.length&&state.pageRows.every(r=>state.selected.has(r.id));byId('select-page').textContent=allPage?'Deselect this page':'Select this page';
    for(const card of byId('image-grid').children){const checked=state.selected.has(card.dataset.imageId);card.classList.toggle('is-selected',checked);const cb=card.querySelector('input');if(cb)cb.checked=checked;}
    byId('export-csv').disabled=!count||!!state.downloadController;byId('download-selected').disabled=!count||!!state.downloadController;byId('clear-selection').disabled=!!state.downloadController;byId('cancel-download').hidden=!state.downloadController;
    if(byId('download-pool-batch'))byId('download-pool-batch').disabled=!!state.downloadController||!poolBatchRows().length;
  }
  function addDefinition(list,label,value,mono=false) {list.append(node('dt','',label),node('dd',mono?'mono':'',value||'Not recorded'));}
  function openDetails(row) {
    const content=byId('dialog-content'),layout=node('div','detail-layout'),preview=node('div','detail-preview'),info=node('div','detail-info');
    const url=assetURL(row.file);
    if(url){const img=node('img');img.src=url;img.alt=text(row.public_metadata?.alt)||titleFor(row);img.addEventListener('error',()=>{img.remove();const f=node('div','preview-fallback');f.append(node('span','','Preview unavailable'));preview.prepend(f);},{once:true});preview.append(img);}else fallbackPreview(preview);
    preview.append(downloadLink(row,'button','Download original file ↓'));
    info.append(node('span','eyebrow',serviceFor(row.service)+' / '+(row.origin==='new'?'New batch':'Existing artwork')));
    const heading=node('h2','',titleFor(row));heading.id='dialog-title';info.append(heading,statusChip(row),node('p','detail-summary',statusExplanations[statusFor(row)]));
    const facts=node('dl','detail-list');addDefinition(facts,'Image ID',row.id,true);addDefinition(facts,'Batch',batchFor(row.batch_id));addDefinition(facts,'File path',row.file,true);addDefinition(facts,'Topic',categoryFor(row.category));if(row.original_gallery)addDefinition(facts,'Original gallery',serviceFor(row.original_gallery));if(row.category==='general-pool')addDefinition(facts,'Image role','General pool context; not evidence of a leak.');addDefinition(facts,'Dimensions',row.width&&row.height?row.width+' × '+row.height+' px':'Not recorded');addDefinition(facts,'Size class',qualityNames[row.quality]||humanize(row.quality));
    if(Array.isArray(row.tags)&&row.tags.length)addDefinition(facts,'Tags',row.tags.map(humanize).join(' · '));
    info.append(facts);
    const usage=node('section','metadata-section');usage.append(node('h3','','Recorded placements'));
    const placements=placementsFor(row);
    if(placements.length){const list=node('ul','placement-list');for(const placement of placements){const li=node('li'),purl=webURL(placement.url),label=text(placement.title)||text(placement.url)||'Recorded placement';if(purl){const a=link(purl,label);a.target='_blank';a.rel='noopener noreferrer';li.append(a);}else li.append(node('span','',label));const extra=[humanize(placement.kind),placement.post_id!=null?'Post ID '+placement.post_id:''].filter(Boolean).join(' · ');if(extra)li.append(node('small','',extra));list.append(li);}usage.append(list);}else usage.append(node('p','empty-placements',statusFor(row)==='new_not_deployed'?'No deployment placements have been recorded for this batch.':'No verified page or post placement is recorded. This does not establish that the image is unused.'));
    const attachments=Array.isArray(row.usage?.attachment_ids)?row.usage.attachment_ids:[];
    if(attachments.length)usage.append(node('p','','WordPress attachment ID'+(attachments.length===1?'':'s')+': '+attachments.join(', ')));
    if(row.usage?.scope){const scope=node('details','detail-scope');scope.append(node('summary','','What this usage check covers'),node('p','',row.usage.scope));usage.append(scope);}
    info.append(usage);
    if(Array.isArray(row.limitations)&&row.limitations.length){const notes=node('section','metadata-section');notes.append(node('h3','','Placement notes'));for(const note of row.limitations)notes.append(node('p','',note));info.append(notes);}
    const metadata=node('section','metadata-section');metadata.append(node('h3','','Public image metadata'));const fields=node('dl','metadata-fields');for(const [key,label] of [['title','Title'],['alt','Alt text'],['caption','Caption'],['description','Description']]){const wrap=node('div');wrap.append(node('dt','',label),node('dd','',row.public_metadata?.[key]||'Not recorded'));fields.append(wrap);}metadata.append(fields);info.append(metadata);
    const source=node('section','metadata-section');source.append(node('h3','','Source record'),node('p','',sourceFor(row)||'Source name not recorded'));
    const sourceURL=webURL(row.source_page);if(sourceURL){const a=link(sourceURL,'Open original source page ↗','source-link');a.target='_blank';a.rel='noopener noreferrer';source.append(a);}source.append(node('p','','The preview and download use the repository file. Source records are kept separate from public image descriptions.'));info.append(source);
    layout.append(preview,info);content.replaceChildren(layout);const dialog=byId('image-dialog');dialog.showModal();dialog.scrollTop=0;byId('dialog-close').focus();
  }
  function downloadBlob(blob,name) {const url=URL.createObjectURL(blob),a=link(url,name);a.download=name;a.hidden=true;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
  function csvCell(value) {let s=text(value);if(/^[\s]*[=+\-@]|^[\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
  function exportCSV() {
    const rows=[...state.selected].map(id=>state.byId.get(id)).filter(Boolean);
    const header=['image_id','file','origin','batch_id','batch_label','service','category','width','height','quality','usage_status','attachment_ids','placement_urls','placement_titles','title','alt','caption','description','source','source_page','tags'];
    const lines=[header,...rows.map(r=>[r.id,r.file,r.origin,r.batch_id,batchFor(r.batch_id),r.service,r.category,r.width,r.height,r.quality,statusFor(r),(r.usage?.attachment_ids||[]).join(' | '),placementsFor(r).map(p=>p.url).join(' | '),placementsFor(r).map(p=>p.title).join(' | '),r.public_metadata?.title||r.title,r.public_metadata?.alt,r.public_metadata?.caption,r.public_metadata?.description,sourceFor(r),r.source_page,(r.tags||[]).join(' | ')])];
    downloadBlob(new Blob(['\ufeff'+lines.map(r=>r.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'supremacy-selected-images.csv');notify('Exported '+rows.length+' selected image record'+(rows.length===1?'':'s')+'. Usage records are unchanged.');
  }
  const crcTable=Uint32Array.from({length:256},(_,i)=>{let c=i;for(let k=0;k<8;k++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
  function crc32(bytes){let crc=0xffffffff;for(let i=0;i<bytes.length;i++)crc=crcTable[(crc^bytes[i])&255]^(crc>>>8);return (crc^0xffffffff)>>>0;}
  function zipName(row){const base=text(row.file).split('/').pop()||'image';return (text(row.id)+'-'+base).replace(/[\x00-\x1f<>:"/\\|?*]/g,'-');}
  function zipHeader(size){const bytes=new Uint8Array(size);return {bytes,view:new DataView(bytes.buffer)};}
  function poolBatchRows(){return state.images.filter(r=>r.origin==='new'&&r.service===poolService&&(!state.defaultBatch||text(r.batch_id)===state.defaultBatch));}
  async function downloadZIP(batchRows=null) {
    if(state.downloadController)return;
    const rows=Array.isArray(batchRows)?batchRows:[...state.selected].map(id=>state.byId.get(id)).filter(Boolean);if(!rows.length)return;
    if(rows.length>65535){notify('Select fewer than 65,536 files for one ZIP.');return;}
    const controller=new AbortController();state.downloadController=controller;state.downloadBatch=Array.isArray(batchRows);updateSelection();
    const chunks=[],central=[];let offset=0,centralSize=0;
    const now=new Date(),dosTime=(now.getHours()<<11)|(now.getMinutes()<<5)|(now.getSeconds()>>1),dosDate=((Math.max(1980,Math.min(2107,now.getFullYear()))-1980)<<9)|((now.getMonth()+1)<<5)|now.getDate();
    try {
      for(let i=0;i<rows.length;i++){
        const row=rows[i],url=assetURL(row.file);if(!url)throw new Error('The repository file path is unavailable for '+row.id+'.');
        notify('Preparing ZIP · '+(i+1)+' of '+rows.length+' images',true);
        const response=await fetch(url,{signal:controller.signal});if(!response.ok)throw new Error('Could not download '+row.id+' (HTTP '+response.status+').');
        const bytes=new Uint8Array(await response.arrayBuffer());if(bytes.length>0xffffffff||offset+bytes.length>0xffffffff)throw new Error('This selection is too large for a single ZIP. Please select a smaller group.');
        const filename=new TextEncoder().encode(zipName(row));if(filename.length>65535)throw new Error('A filename is too long for this ZIP.');
        const checksum=crc32(bytes),local=zipHeader(30),lv=local.view;lv.setUint32(0,0x04034b50,true);lv.setUint16(4,20,true);lv.setUint16(6,0x800,true);lv.setUint16(10,dosTime,true);lv.setUint16(12,dosDate,true);lv.setUint32(14,checksum,true);lv.setUint32(18,bytes.length,true);lv.setUint32(22,bytes.length,true);lv.setUint16(26,filename.length,true);
        const entry=zipHeader(46),cv=entry.view;cv.setUint32(0,0x02014b50,true);cv.setUint16(4,20,true);cv.setUint16(6,20,true);cv.setUint16(8,0x800,true);cv.setUint16(12,dosTime,true);cv.setUint16(14,dosDate,true);cv.setUint32(16,checksum,true);cv.setUint32(20,bytes.length,true);cv.setUint32(24,bytes.length,true);cv.setUint16(28,filename.length,true);cv.setUint32(42,offset,true);
        chunks.push(local.bytes,filename,bytes);central.push(entry.bytes,filename);centralSize+=46+filename.length;offset+=30+filename.length+bytes.length;
      }
      if(controller.signal.aborted)throw new DOMException('Download canceled','AbortError');
      const end=zipHeader(22),ev=end.view;ev.setUint32(0,0x06054b50,true);ev.setUint16(8,rows.length,true);ev.setUint16(10,rows.length,true);ev.setUint32(12,centralSize,true);ev.setUint32(16,offset,true);
      downloadBlob(new Blob([...chunks,...central,end.bytes],{type:'application/zip'}),(state.downloadBatch?'supremacy-pool-leak-detection-batch.zip':'supremacy-selected-images.zip'));notify('ZIP ready: '+rows.length+' repository image'+(rows.length===1?'':'s')+'. Usage records are unchanged.');
    }catch(error){notify(error.name==='AbortError'?'ZIP download canceled. Your selection is preserved.':error.message+' No ZIP was created. Your selection is preserved.',false);}
    finally{state.downloadController=null;state.downloadBatch=false;updateSelection();}
  }
  async function loadInventory() {
    byId('image-results').setAttribute('aria-busy','true');byId('select-page').disabled=true;
    try{
      const response=await fetch('image-inventory.json',{cache:'no-cache'});if(!response.ok)throw new Error('HTTP '+response.status);
      const inventory=await response.json();if(!Array.isArray(inventory.images))throw new Error('The inventory does not contain an images list.');
      state.batches=new Map((Array.isArray(inventory.batches)?inventory.batches:[]).map(b=>[text(b.id),text(b.label)||text(b.id)]));state.categories=new Map((Array.isArray(inventory.categories)?inventory.categories:[]).map(c=>[text(c.id),text(c.label)||text(c.id)]));
      const seen=new Set();state.images=inventory.images.filter(r=>{if(!r||!r.id||!r.file||seen.has(text(r.id)))return false;seen.add(text(r.id));return true;}).map(r=>({...r,id:text(r.id),_search:''}));
      for(const row of state.images)row._search=searchText(row);state.byId=new Map(state.images.map(r=>[r.id,r]));
      const newBatches=[...new Set(state.images.filter(r=>r.service===poolService&&r.origin==='new').map(r=>text(r.batch_id)).filter(Boolean))];state.defaultBatch=newBatches.find(id=>id.includes('2026-11-25'))||newBatches.at(-1)||'';
      state.selected=new Set([...state.selected].filter(id=>state.byId.has(id)));fillFilters();buildMetrics();
      if(isPool){byId('filter-batch').value=state.defaultBatch;updatePoolContext();}
      const params=new URLSearchParams(location.search);if(params.has('q'))byId('search').value=params.get('q');
      if(params.has('id'))byId('search').value=params.get('id');
      for(const key of ['origin','service','category','batch','usage','quality']){const el=byId('filter-'+key),value=params.get(key);if(el&&value!==null&&[...el.options].some(o=>o.value===value))el.value=value;}
      if(isPool&&params.get('tab')==='existing'){state.poolTab='existing';byId('filter-batch').value='';updatePoolContext();}
      byId('inventory-updated').textContent='Inventory snapshot · '+displayDate(inventory.updated_at);state.page=1;render();
    }catch(error){byId('image-grid').replaceChildren();byId('pagination').hidden=true;byId('result-count').textContent='Inventory unavailable';byId('result-note').textContent='The image files and usage records have not been changed.';byId('image-results').setAttribute('aria-busy','false');showMessage('We couldn’t load the inventory','Please try again. If you opened this HTML file directly, open the hosted gallery so its inventory can load.',true);console.error('Image inventory load failed:',error);}
  }
  let searchTimer;byId('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.page=1;render();},120);});
  for(const select of document.querySelectorAll('#filters select'))select.addEventListener('change',()=>{state.page=1;render();});
  byId('reset-filters').addEventListener('click',resetFilters);
  byId('page-size').addEventListener('change',event=>{state.pageSize=Number(event.target.value)===48?48:24;state.page=1;render();});
  function turnPage(delta){state.page+=delta;render();byId('image-results').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});}
  byId('previous-page').addEventListener('click',()=>turnPage(-1));byId('next-page').addEventListener('click',()=>turnPage(1));
  byId('select-page').addEventListener('click',()=>{const all=state.pageRows.every(r=>state.selected.has(r.id));for(const row of state.pageRows)all?state.selected.delete(row.id):state.selected.add(row.id);updateSelection();});
  byId('clear-selection').addEventListener('click',()=>{state.selected.clear();updateSelection();});byId('export-csv').addEventListener('click',exportCSV);byId('download-selected').addEventListener('click',()=>downloadZIP());if(byId('download-pool-batch'))byId('download-pool-batch').addEventListener('click',()=>downloadZIP(poolBatchRows()));byId('cancel-download').addEventListener('click',()=>state.downloadController?.abort());
  if(isPool){const tabs=[...document.querySelectorAll('[data-pool-tab]')];for(const tab of tabs){tab.addEventListener('click',()=>{state.poolTab=tab.dataset.poolTab;byId('filter-batch').value=state.poolTab==='new'?state.defaultBatch:'';byId('filter-usage').value='';state.page=1;updatePoolContext();render();});tab.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const target=event.key==='Home'?tabs[0]:event.key==='End'?tabs.at(-1):tabs.find(t=>t!==tab);target.click();target.focus();}});}}
  byId('dialog-close').addEventListener('click',()=>byId('image-dialog').close());byId('image-dialog').addEventListener('click',event=>{if(event.target===byId('image-dialog')){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)event.target.close();}});
  loadInventory();
})();
