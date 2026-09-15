(function(){
  const root=document.body;
  const role=root.dataset.adminRole;
  const prefix=role==='chi'?'CHI Insurance':'Arrow';
  const keyName='arrow_admin_key_'+role;
  const API_BASE=window.ARROW_API_BASE||'';
  let key=sessionStorage.getItem(keyName)||'';
  let history=[];
  let currentTrips=[];
  let currentRoster=[];
  let editingTripId='';

  const $=(id)=>document.getElementById(id);
  const esc=(s)=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function authHeaders(){return {'Content-Type':'application/json','X-Admin-Key':key};}
  function askKey(){key=prompt(prefix+' administrator access key:')||'';if(key)sessionStorage.setItem(keyName,key);}
  async function api(path,options={}){
    if(!key)askKey();
    const res=await fetch(API_BASE+path,{...options,headers:{...authHeaders(),...(options.headers||{})}});
    if(res.status===401||res.status===403){sessionStorage.removeItem(keyName);key='';throw new Error('Administrator access denied. Reload and enter the correct key.');}
    if(!res.ok){let msg='Request failed';try{msg=(await res.json()).detail||msg}catch{}throw new Error(msg);}
    return res.json();
  }

  function tripDetails(e){
    return (e.trips||[]).map(x=>`${x.dates||''} ${x.route||''}${x.canceled?' [CANCELLED]':''}`).join(' | ');
  }

  function renderTracker(t){
    if(!$('trackerStats'))return;
    $('trackerStats').innerHTML=
      `<div class="metric"><b>${t.total_days}</b><span>days reserved/used</span></div>`+
      `<div class="metric"><b>${t.days_remaining}</b><span>days remaining</span></div>`+
      `<div class="metric"><b>${t.total_trips}</b><span>current trips</span></div>`+
      `<div class="metric"><b>${t.employee_count}</b><span>travelling employees</span></div>`;
    if($('trackerNotice'))$('trackerNotice').textContent=t.administrative_notice||'';
    if($('employees')){
      $('employees').innerHTML=(t.employees||[]).map(e=>
        `<tr><td>${esc(e.name)}</td><td>${e.days}</td><td>${e.trip_count}</td><td>${esc(tripDetails(e))}</td></tr>`
      ).join('') || '<tr><td colspan="4">No current-policy trips recorded yet.</td></tr>';
    }
  }

  function renderArchive(a){
    if(!$('archiveStats'))return;
    $('archiveStats').innerHTML=
      `<div class="metric"><b>${a.total_days}</b><span>days used</span></div>`+
      `<div class="metric"><b>${a.trip_count}</b><span>counted trips</span></div>`+
      `<div class="metric"><b>${a.canceled_trip_count}</b><span>cancelled trips</span></div>`+
      `<div class="metric"><b>${a.employee_count}</b><span>employees</span></div>`;
    $('archiveNotice').textContent=a.notice||'';
    $('archiveEmployees').innerHTML=(a.employees||[]).map(e=>
      `<tr><td>${esc(e.name)}</td><td>${e.days}</td><td>${e.trip_count}</td><td>${e.canceled_trip_count}</td><td>${esc(tripDetails(e))}</td></tr>`
    ).join('');
  }

  function populateRoster(roster){
    currentRoster=roster||[];
    const list=$('employeeRoster');
    if(!list)return;
    list.innerHTML=currentRoster.map(e=>`<option value="${esc(e.name)}"></option>`).join('');
  }

  function daysBetween(start,end){
    if(!start||!end)return '';
    const a=new Date(start+'T00:00:00'),b=new Date(end+'T00:00:00');
    if(Number.isNaN(a.getTime())||Number.isNaN(b.getTime())||b<a)return '';
    return Math.round((b-a)/86400000)+1;
  }

  function updateTripPreview(){
    const days=daysBetween($('tripStart')?.value,$('tripEnd')?.value);
    if($('tripDaysPreview'))$('tripDaysPreview').textContent=days?`${days} day${days===1?'':'s'} will be reserved from the pool`:'Dates calculate days automatically';
    const route=String($('tripRoute')?.value||'').toUpperCase();
    const named=[
      ['Belarus',['BELARUS','MSQ']],['Russia',['RUSSIA','SVO','DME','VKO','LED']],
      ['Ukraine',['UKRAINE','KBP','IEV','LWO','ODS']],['Gaza',['GAZA']],
      ['Israel',['ISRAEL','TLV','HFA']],['Lebanon',['LEBANON','BEY']]
    ];
    const hard=named.filter(([,a])=>a.some(x=>route.includes(x))).map(([c])=>c);
    const mid=['DXB','DWC','AUH','SHJ','DOH','BAH','KWI','MCT','RUH','JED','DMM','AMM','BEY','TLV','BGW','EBL','IKA','THR','SAH','ADE'].some(x=>route.includes(x));
    const el=$('tripPolicyPreview');
    if(!el)return;
    if(hard.length){
      el.className='trip-policy-preview danger';
      el.textContent=`Policy restriction: ${hard.join(', ')} — cover is excluded unless declared and agreed by Underwriters before travel.`;
    }else if(mid){
      el.className='trip-policy-preview warn';
      el.textContent='Middle East route detected — check current FCDO advice before booking and before departure.';
    }else{
      el.className='trip-policy-preview';
      el.textContent='';
    }
  }

  function renderTripManagement(data){
    if(!data)return;
    populateRoster(data.roster||[]);
    currentTrips=data.trips||[];
    renderTracker(data.summary);

    if($('tripStorage')){
      const s=data.storage||{};
      $('tripStorage').innerHTML=s.production_ready
        ? `<span class="storage-ok">Railway PostgreSQL connected — trip changes are persistent.</span>`
        : `<span class="storage-warn">${esc(s.warning||'Railway PostgreSQL is not configured.')}</span>`;
    }

    if($('tripRows')){
      $('tripRows').innerHTML=currentTrips.map(t=>`
        <tr class="${t.canceled?'trip-cancelled':''}">
          <td>${esc(t.employee)}</td>
          <td>${esc(t.start_date)} → ${esc(t.end_date)}</td>
          <td>${esc(t.route)}</td>
          <td>${t.days}</td>
          <td>${t.canceled?'Cancelled':'Counted'}</td>
          <td class="trip-actions">
            <button class="btn mini secondary" onclick="editTrip('${t.id}')">Edit</button>
            <button class="btn mini secondary" onclick="toggleTripCancel('${t.id}',${t.canceled?'false':'true'})">${t.canceled?'Restore':'Cancel'}</button>
            <button class="btn mini danger-btn" onclick="deleteTrip('${t.id}')">Delete</button>
          </td>
        </tr>
      `).join('') || '<tr><td colspan="6">No current-policy trips yet. The live dashboard is 0 employees / 0 days / 250 remaining.</td></tr>';
    }
  }

  function resetTripForm(){
    editingTripId='';
    ['tripEmployee','tripEmail','tripStart','tripEnd','tripRoute','tripNotes'].forEach(id=>{if($(id))$(id).value='';});
    if($('tripSaveBtn'))$('tripSaveBtn').textContent='Add trip';
    if($('tripEditCancel'))$('tripEditCancel').hidden=true;
    updateTripPreview();
  }

  async function refreshTrips(){
    const d=await api('/api/admin/trips');
    renderTripManagement(d);
  }

  async function saveTrip(){
    const payload={
      employee:$('tripEmployee').value.trim(),
      email:$('tripEmail').value.trim(),
      start_date:$('tripStart').value,
      end_date:$('tripEnd').value,
      route:$('tripRoute').value.trim(),
      notes:$('tripNotes').value.trim()
    };
    if(!payload.employee||!payload.start_date||!payload.end_date||!payload.route){
      $('tripMessage').textContent='Employee, start date, end date and route are required.';
      return;
    }
    $('tripSaveBtn').disabled=true;
    $('tripMessage').textContent=editingTripId?'Updating trip…':'Adding trip…';
    try{
      await api(editingTripId?`/api/admin/trips/${editingTripId}`:'/api/admin/trips',{
        method:editingTripId?'PUT':'POST',
        body:JSON.stringify(payload)
      });
      $('tripMessage').textContent=editingTripId?'Trip updated.':'Trip added to the current 2026/27 tracker.';
      resetTripForm();
      await refreshTrips();
    }catch(e){
      $('tripMessage').textContent=e.message;
    }finally{
      $('tripSaveBtn').disabled=false;
    }
  }

  function editTrip(id){
    const t=currentTrips.find(x=>x.id===id);if(!t)return;
    editingTripId=id;
    $('tripEmployee').value=t.employee||'';
    $('tripEmail').value=t.email||'';
    $('tripStart').value=t.start_date||'';
    $('tripEnd').value=t.end_date||'';
    $('tripRoute').value=t.route||'';
    $('tripNotes').value=t.notes||'';
    $('tripSaveBtn').textContent='Save changes';
    $('tripEditCancel').hidden=false;
    updateTripPreview();
    $('tripFormCard')?.scrollIntoView({behavior:'smooth',block:'start'});
  }

  async function toggleTripCancel(id,canceled){
    try{
      await api(`/api/admin/trips/${id}/cancel`,{method:'POST',body:JSON.stringify({canceled})});
      await refreshTrips();
    }catch(e){$('tripMessage').textContent=e.message;}
  }

  async function deleteTrip(id){
    if(!confirm('Delete this trip permanently? The action will remain in the server audit log.'))return;
    try{
      await api(`/api/admin/trips/${id}`,{method:'DELETE'});
      if(editingTripId===id)resetTripForm();
      await refreshTrips();
    }catch(e){$('tripMessage').textContent=e.message;}
  }

  async function load(){
    try{
      const d=await api('/api/admin/dashboard');
      $('cert').textContent=`${d.certificate.certificate_no} • ${d.certificate.period_of_insurance}`;
      if(role==='arrow'){
        if(d.tracker)renderTracker(d.tracker);
        if(d.archive)renderArchive(d.archive);
      }else{
        document.querySelectorAll('[data-arrow-only]').forEach(el=>el.hidden=true);
      }

      $('claims').innerHTML=`<b>Medical:</b> ${esc(d.claims_contacts.medical)}<br><b>Claims:</b> ${esc(d.claims_contacts.crawford_phone)} • ${esc(d.claims_contacts.crawford_email)}<br><b>Kidnap/security:</b> ${esc(d.claims_contacts.kidnap_security)}`;

      if(role==='chi'&&d.provider_status){
        $('chiOnly').hidden=false;
        $('provider').innerHTML=`Claude: <b>${d.provider_status.claude_configured?'configured':'NOT configured'}</b> (${esc(d.provider_status.claude_model)})<br>OpenAI fallback: <b>${d.provider_status.openai_fallback_configured?'configured':'NOT configured'}</b> (${esc(d.provider_status.openai_model)})<br>Full policy wording layer: <b>${d.provider_status.full_wording_available?'available':'not yet loaded'}</b><br>Employee AI requests today (this instance): <b>${d.provider_status.employee_usage_guard.ai_requests_today_this_instance}/${d.provider_status.employee_usage_guard.global_daily_limit}</b>`;
        $('policyAdmin').textContent=`Age limit: ${d.policy_admin.age_limit}\n\nLaw/jurisdiction: ${d.policy_admin.law_and_jurisdiction}`;
        if(d.trip_management){
          renderTripManagement({
            summary:d.tracker,
            storage:d.trip_management.storage,
            roster:d.trip_management.roster,
            trips:d.trip_management.trips
          });
        }
      }
    }catch(e){$('error').textContent=e.message;}
  }

  async function chat(){
    const i=$('adminInput'),text=i.value.trim();if(!text)return;
    $('adminMessages').innerHTML+=`<div class="msg user">${esc(text)}</div>`;i.value='';
    try{
      const d=await api('/api/admin/chat',{method:'POST',body:JSON.stringify({message:text,history:history.slice(-10)})});
      history.push({role:'user',content:text},{role:'assistant',content:d.answer});
      $('adminMessages').innerHTML+=`<div class="msg bot"><small>${esc(d.provider)} • admin ${esc(d.admin_role)}</small>${esc(d.answer).replace(/\n/g,'<br>')}</div>`;
    }catch(e){$('adminMessages').innerHTML+=`<div class="msg err">${esc(e.message)}</div>`;}
    $('adminMessages').scrollTop=$('adminMessages').scrollHeight;
  }

  window.adminChat=chat;
  window.resetAdminKey=()=>{sessionStorage.removeItem(keyName);location.reload();};
  window.saveTrip=saveTrip;
  window.editTrip=editTrip;
  window.toggleTripCancel=toggleTripCancel;
  window.deleteTrip=deleteTrip;
  window.cancelTripEdit=resetTripForm;

  document.addEventListener('DOMContentLoaded',()=>{
    $('adminInput')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();chat();}});
    ['tripStart','tripEnd','tripRoute'].forEach(id=>$(id)?.addEventListener('input',updateTripPreview));
    load();
  });
})();