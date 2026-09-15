(function(){
  const root=document.body;
  const role=root.dataset.adminRole;
  const prefix=role==='chi'?'CHI Insurance':'Arrow';
  const keyName='arrow_admin_key_'+role;
  let key=sessionStorage.getItem(keyName)||'';
  let history=[];

  const $=(id)=>document.getElementById(id);
  const esc=(s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function authHeaders(){return {'Content-Type':'application/json','X-Admin-Key':key};}
  function askKey(){ key=prompt(prefix+' administrator access key:')||''; if(key) sessionStorage.setItem(keyName,key); }
  async function api(path, options={}){
    if(!key) askKey();
    const res=await fetch(path,{...options,headers:{...authHeaders(),...(options.headers||{})}});
    if(res.status===401||res.status===403){ sessionStorage.removeItem(keyName); key=''; throw new Error('Administrator access denied. Reload and enter the correct key.'); }
    if(!res.ok){ let msg='Request failed'; try{msg=(await res.json()).detail||msg}catch{} throw new Error(msg); }
    return res.json();
  }
  function renderTracker(t){
    $('trackerStats').innerHTML=`<div class="metric"><b>${t.total_days}</b><span>days used</span></div><div class="metric"><b>${t.days_remaining}</b><span>days remaining</span></div><div class="metric"><b>${t.total_trips}</b><span>trips</span></div><div class="metric"><b>${t.employee_count}</b><span>employees</span></div>`;
    $('trackerNotice').textContent=t.administrative_notice;
    $('employees').innerHTML=t.employees.map(e=>`<tr><td>${esc(e.name)}</td><td>${e.days}</td><td>${e.trip_count}</td><td>${esc(e.trips.map(x=>`${x.dates||''} ${x.route||''}`).join(' | '))}</td></tr>`).join('');
  }
  async function load(){
    try{
      const d=await api('/api/admin/dashboard');
      $('cert').textContent=`${d.certificate.certificate_no} • ${d.certificate.period_of_insurance}`;
      if(role==='arrow' && d.tracker){ renderTracker(d.tracker); }
      else { document.querySelectorAll('[data-arrow-only]').forEach(el=>el.hidden=true); }
      $('claims').innerHTML=`<b>Medical:</b> ${esc(d.claims_contacts.medical)}<br><b>Claims:</b> ${esc(d.claims_contacts.crawford_phone)} • ${esc(d.claims_contacts.crawford_email)}<br><b>Kidnap/security:</b> ${esc(d.claims_contacts.kidnap_security)}`;
      if(role==='chi' && d.provider_status){
        $('chiOnly').hidden=false;
        $('provider').innerHTML=`Claude: <b>${d.provider_status.claude_configured?'configured':'NOT configured'}</b> (${esc(d.provider_status.claude_model)})<br>OpenAI fallback: <b>${d.provider_status.openai_fallback_configured?'configured':'NOT configured'}</b> (${esc(d.provider_status.openai_model)})<br>Full policy wording layer: <b>${d.provider_status.full_wording_available?'available':'not yet loaded'}</b><br>Employee AI requests today (this instance): <b>${d.provider_status.employee_usage_guard.ai_requests_today_this_instance}/${d.provider_status.employee_usage_guard.global_daily_limit}</b>`;
        $('policyAdmin').textContent=`Age limit: ${d.policy_admin.age_limit}\n\nLaw/jurisdiction: ${d.policy_admin.law_and_jurisdiction}`;
      }
    }catch(e){$('error').textContent=e.message;}
  }
  async function chat(){
    const i=$('adminInput'), text=i.value.trim(); if(!text)return;
    $('adminMessages').innerHTML+=`<div class="msg user">${esc(text)}</div>`; i.value='';
    try{
      const d=await api('/api/admin/chat',{method:'POST',body:JSON.stringify({message:text,history:history.slice(-10)})});
      history.push({role:'user',content:text},{role:'assistant',content:d.answer});
      $('adminMessages').innerHTML+=`<div class="msg bot"><small>${esc(d.provider)} • admin ${esc(d.admin_role)}</small>${esc(d.answer).replace(/\n/g,'<br>')}</div>`;
    }catch(e){$('adminMessages').innerHTML+=`<div class="msg err">${esc(e.message)}</div>`;}
    $('adminMessages').scrollTop=$('adminMessages').scrollHeight;
  }
  window.adminChat=chat; window.resetAdminKey=()=>{sessionStorage.removeItem(keyName);location.reload();};
  document.addEventListener('DOMContentLoaded',()=>{$('adminInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();chat();}});load();});
})();
