(function(){
  // copy buttons: <button data-copy="#id">
  document.querySelectorAll('[data-copy]').forEach(function(b){
    b.addEventListener('click',function(){
      var el=document.querySelector(b.getAttribute('data-copy'));var t=el.value||el.textContent;
      (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy note'},1500)},function(){el.select&&el.select();document.execCommand&&document.execCommand('copy');b.textContent='Copied';setTimeout(function(){b.textContent='Copy note'},1500)});
    });
  });
  // live char counter
  var n=document.getElementById('note');var c=document.getElementById('notecount');if(n&&c){c.textContent=n.value.length+' / 200 characters'}
  // filter + dossier expansion on the candidate table
  var tbl=document.getElementById('links');
  if(tbl){
    var f=document.getElementById('filter');
    if(f){f.addEventListener('input',function(){var q=f.value.toLowerCase();tbl.querySelectorAll('tbody tr.link').forEach(function(r){var show=r.textContent.toLowerCase().indexOf(q)>=0;r.style.display=show?'':'none';var d=r.nextElementSibling;if(d&&d.classList.contains('dossier')&&!show){d.remove()}})})}
    var cache=null;
    function load(){return cache?Promise.resolve(cache):fetch('data/topology_links.geojson').then(function(r){return r.json()}).then(function(j){cache={};j.features.forEach(function(x){cache[x.properties.id]=x.properties.argument});return cache})}
    tbl.querySelectorAll('tbody tr.link').forEach(function(r){r.addEventListener('click',function(e){if(e.target.tagName==='A')return;var nx=r.nextElementSibling;if(nx&&nx.classList.contains('dossier')){nx.remove();return}
      load().then(function(m){var tr=document.createElement('tr');tr.className='dossier';var td=document.createElement('td');td.colSpan=r.children.length;td.textContent=m[r.dataset.id]||'(dossier not found)';tr.appendChild(td);r.parentNode.insertBefore(tr,r.nextSibling)})})});
    // sort
    tbl.querySelectorAll('thead th[data-k]').forEach(function(th){th.style.cursor='pointer';th.addEventListener('click',function(){var k=+th.dataset.k;var rows=[].slice.call(tbl.querySelectorAll('tbody tr.link'));var dir=th.dataset.dir==='a'?-1:1;th.dataset.dir=dir===1?'a':'d';
      rows.sort(function(a,b){var x=a.children[k].dataset.v||a.children[k].textContent,y=b.children[k].dataset.v||b.children[k].textContent;var nx=parseFloat(x),ny=parseFloat(y);if(!isNaN(nx)&&!isNaN(ny))return (nx-ny)*dir;return x.localeCompare(y)*dir});
      var tb=tbl.querySelector('tbody');tb.querySelectorAll('tr.dossier').forEach(function(d){d.remove()});rows.forEach(function(r){tb.appendChild(r)})})});
  }
  // live feed (static fallback is rendered at build time)
  var fb=document.getElementById('feedbody');
  if(fb){fetch('data/feed.json',{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(j){
    var s=document.getElementById('feedstamp');if(s)s.textContent=j.generated_utc;
    fb.innerHTML='';j.entries.forEach(function(e){var tr=document.createElement('tr');
      function td(t){var d=document.createElement('td');d.textContent=t;tr.appendChild(d);return d}
      var a=document.createElement('td');var l=document.createElement('a');l.href=e.url;l.textContent=e.title;a.appendChild(l);tr.appendChild(a);
      td(e.ok?'reachable (HTTP '+(e.http||'?')+')':'NOT reachable'+(e.error?': '+e.error:''));td(e.last_updated||e.pushed_at||e.last_modified||'-');td(e.changed_since_previous_check?'CHANGED':'no change');td(e.checked_utc);fb.appendChild(tr)})}).catch(function(){})}
})();
