(function(){
  const SESSION_KEY='arrow_hal_browser_session_v2';
  let halPendingRequests=0, halSlowTimer=null;
  function sessionId(){let id=localStorage.getItem(SESSION_KEY);if(!id){try{id=crypto.randomUUID();}catch(e){id='hal-'+Date.now()+'-'+Math.random().toString(36).slice(2);}localStorage.setItem(SESSION_KEY,id);}return id;}
  function panel(){return document.getElementById('halPanel');}
  function input(){return document.getElementById('halInput');}
  function messages(){return document.getElementById('halMessages');}
  function scrollBottom(){const w=messages();if(w)w.scrollTop=w.scrollHeight;}
  function setBusy(active){
    const p=panel(),btn=document.getElementById('halSendBtn');let t=document.getElementById('halThinking');
    if(active){
      if(p)p.setAttribute('aria-busy','true');
      if(btn){if(!btn.dataset.idleText)btn.dataset.idleText=btn.textContent||'Send';btn.disabled=true;btn.textContent='Working…';}
      if(!t){t=document.createElement('div');t.id='halThinking';t.className='hal-msg bot hal-thinking';t.setAttribute('role','status');t.setAttribute('aria-live','polite');t.innerHTML='<span class="hal-thinking-orb"></span><span class="hal-thinking-label">HAL is checking your policy wording</span><span class="hal-thinking-dots"><i></i><i></i><i></i></span>';messages()?.appendChild(t);}
      scrollBottom();clearTimeout(halSlowTimer);halSlowTimer=setTimeout(()=>{const l=document.querySelector('#halThinking .hal-thinking-label');if(l)l.textContent='Still working — checking the full policy';scrollBottom();},4500);
    }else{
      if(p)p.removeAttribute('aria-busy');clearTimeout(halSlowTimer);halSlowTimer=null;if(t)t.remove();if(btn){btn.disabled=false;btn.textContent=btn.dataset.idleText||'Send';}
    }
  }
  function begin(){halPendingRequests++;setBusy(true);}function end(){halPendingRequests=Math.max(0,halPendingRequests-1);if(!halPendingRequests)setBusy(false);}
  const originalFetch=window.fetch.bind(window);
  window.fetch=function(arg,init){let isHal=false;try{const u=typeof arg==='string'?arg:(arg&&arg.url)||'';if(u.includes('/api/chat')){isHal=true;init=init||{};const h=new Headers(init.headers||{});h.set('X-HAL-Session',sessionId());init={...init,headers:h};begin();}}catch(e){}
    const req=originalFetch(arg,init);if(!isHal)return req;return req.then(async r=>{try{await r.clone().text();}catch(e){}finally{end();}return r;},e=>{end();throw e;});};
  function sendText(text,incomplete){const e=input();if(!e)return;e.value=text;e.focus();if(!incomplete&&typeof window.sendHalMessage==='function')window.sendHalMessage();}
  function setExpanded(expanded){const p=panel();if(!p)return;p.classList.toggle('hal-expanded',!!expanded);document.body.classList.toggle('hal-chat-expanded-open',!!expanded&&p.classList.contains('show'));const b=p.querySelector('.hal-expand-btn');if(b){b.textContent=expanded?'⤡':'⤢';b.setAttribute('aria-label',expanded?'Restore HAL window':'Expand HAL window');b.setAttribute('aria-pressed',expanded?'true':'false');}setTimeout(scrollBottom,60);}
  function ensureHeader(){const p=panel();if(!p||p.querySelector('.hal-expand-btn'))return;const h=p.querySelector('.hal-header');if(!h)return;const c=h.querySelector('.hal-close'),b=document.createElement('button');b.type='button';b.className='hal-expand-btn';b.textContent='⤢';b.setAttribute('aria-label','Expand HAL window');b.onclick=e=>{e.preventDefault();e.stopPropagation();setExpanded(!p.classList.contains('hal-expanded'));};if(c){h.insertBefore(b,c);c.addEventListener('click',()=>setExpanded(false));}else h.appendChild(b);}
  function enhance(){ensureHeader();const p=panel();if(!p||p.querySelector('.hal-v2-actions'))return;const a=document.createElement('div');a.className='hal-v2-actions';[['🛡️ Am I covered if…','Am I covered if ',true],['📋 Show me how to claim','Show me how to claim',false],['☎️ Who should I call?','Who should I call for help with a claim?',false]].forEach(([l,t,i])=>{const b=document.createElement('button');b.type='button';b.className='hal-v2-action';b.textContent=l;b.onclick=()=>sendText(t,i);a.appendChild(b);});const n=document.createElement('div');n.className='hal-v2-note';n.innerHTML='<span class="hal-v2-claim-label">Claim guidance:</span> HAL explains policy wording, claim steps and contacts. It does not approve or reject an individual claim. AI questions are usage-limited so the service remains available to everyone.';const e=input();if(e&&e.parentElement){const host=e.parentElement.parentElement;host.insertBefore(a,e.parentElement);host.insertBefore(n,e.parentElement);}else{p.appendChild(a);p.appendChild(n);}}
  document.addEventListener('keydown',e=>{if(e.key!=='Escape')return;const p=panel();if(!p||!p.classList.contains('show'))return;if(p.classList.contains('hal-expanded'))setExpanded(false);else if(typeof window.closeHalChat==='function')window.closeHalChat();});
  document.addEventListener('DOMContentLoaded',enhance);setTimeout(enhance,500);
})();