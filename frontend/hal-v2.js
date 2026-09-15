(function(){
  const SESSION_KEY='arrow_hal_browser_session_v2';
  function sessionId(){
    let id=localStorage.getItem(SESSION_KEY);
    if(!id){
      try{id=crypto.randomUUID();}catch(e){id='hal-'+Date.now()+'-'+Math.random().toString(36).slice(2);}
      localStorage.setItem(SESSION_KEY,id);
    }
    return id;
  }

  // Attach a stable, non-identifying browser-session id only to HAL chat calls.
  // The server combines this with a broad IP guard to control abuse without requiring employee accounts.
  const originalFetch=window.fetch.bind(window);
  window.fetch=function(input, init){
    try{
      const url=typeof input==='string'?input:(input&&input.url)||'';
      if(url.includes('/api/chat')){
        init=init||{};
        const headers=new Headers(init.headers||{});
        headers.set('X-HAL-Session',sessionId());
        init={...init,headers};
      }
    }catch(e){}
    return originalFetch(input,init);
  };

  function panel(){ return document.getElementById('halPanel'); }
  function input(){ return document.getElementById('halInput'); }
  function sendText(text, incomplete){
    const el=input(); if(!el) return;
    el.value=text; el.focus();
    if(!incomplete && typeof window.sendHalMessage==='function') window.sendHalMessage();
  }
  function correctVisiblePolicyLabels(){
    // Section 2 page 23: first completed 8-hour delay. Section 3 page 24:
    // delayed-baggage reimbursement after baggage is lost for more than 12 hours.
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    const replacements=[
      ['Travel Delay: €50/4hrs (max €500)','Travel Delay: first completed 8-hour delay €50; then €50/completed hour (policy limits apply)'],
      ['Delayed Baggage: €1,000 (after 4hrs)','Delayed Baggage: €1,000 (after more than 12hrs)']
    ];
    let n; while((n=walker.nextNode())) replacements.forEach(([a,b])=>{if(n.nodeValue.includes(a))n.nodeValue=n.nodeValue.replace(a,b);});
  }
  function enhance(){
    correctVisiblePolicyLabels();
    const p=panel(); if(!p || p.querySelector('.hal-v2-actions')) return;
    const actions=document.createElement('div'); actions.className='hal-v2-actions';
    const items=[
      ['🛡️ Am I covered if…','Am I covered if ',true],
      ['📋 Show me how to claim','Show me how to claim',false],
      ['☎️ Who should I call?','Who should I call for help with a claim?',false]
    ];
    items.forEach(([label,text,incomplete])=>{ const b=document.createElement('button'); b.type='button'; b.className='hal-v2-action'; b.textContent=label; b.onclick=()=>sendText(text,incomplete); actions.appendChild(b); });
    const note=document.createElement('div'); note.className='hal-v2-note'; note.innerHTML='<span class="hal-v2-claim-label">Claim guidance:</span> HAL explains policy wording, claim steps and contacts. It does not approve or reject an individual claim. AI questions are usage-limited so the service remains available to everyone.';
    const el=input();
    if(el && el.parentElement){ const host=el.parentElement.parentElement; host.insertBefore(actions,el.parentElement); host.insertBefore(note,el.parentElement); }
    else { p.appendChild(actions); p.appendChild(note); }
  }
  document.addEventListener('DOMContentLoaded',enhance);
  setTimeout(enhance,500);
})();
