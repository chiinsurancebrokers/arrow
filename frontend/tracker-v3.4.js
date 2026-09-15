(function(){
  const POLICY_START='2026-09-01';
  const API_BASE=window.ARROW_API_BASE || (typeof HAL_API_BASE!=='undefined' ? HAL_API_BASE : '');
  let flagsOverridden=false;

  const WAR_UNREST={
    "Belarus":["BELARUS","MSQ"],
    "Russia":["RUSSIA","SVO","DME","VKO","ZIA","LED","AER","KZN","SVX","OVB"],
    "Ukraine":["UKRAINE","KBP","IEV","LWO","ODS","HRK"],
    "Gaza":["GAZA"],
    "Israel":["ISRAEL","TLV","HFA","ETM"],
    "Lebanon":["LEBANON","BEY"]
  };
  const KIDNAP_ONLY={
    "Afghanistan":["AFGHANISTAN","KBL"],"Colombia":["COLOMBIA","BOG","MDE","CLO","CTG"],
    "Iraq":["IRAQ","BGW","EBL","BSR","NJF"],"Mexico":["MEXICO","MEX","CUN","GDL","MTY"],
    "Nigeria":["NIGERIA","LOS","ABV","PHC"],"Pakistan":["PAKISTAN","ISB","KHI","LHE"],
    "Philippines":["PHILIPPINES","MNL","CEB","CRK"],"Somalia":["SOMALIA","MGQ"],
    "Venezuela":["VENEZUELA","CCS","MAR"],"Yemen":["YEMEN","SAH","ADE"]
  };
  const MIDDLE_EAST={
    DXB:["United Arab Emirates","united-arab-emirates"],DWC:["United Arab Emirates","united-arab-emirates"],
    AUH:["United Arab Emirates","united-arab-emirates"],SHJ:["United Arab Emirates","united-arab-emirates"],
    DOH:["Qatar","qatar"],BAH:["Bahrain","bahrain"],KWI:["Kuwait","kuwait"],MCT:["Oman","oman"],
    RUH:["Saudi Arabia","saudi-arabia"],JED:["Saudi Arabia","saudi-arabia"],DMM:["Saudi Arabia","saudi-arabia"],
    AMM:["Jordan","jordan"],BEY:["Lebanon","lebanon"],TLV:["Israel","israel"],BGW:["Iraq","iraq"],
    EBL:["Iraq","iraq"],IKA:["Iran","iran"],THR:["Iran","iran"],SAH:["Yemen","yemen"],ADE:["Yemen","yemen"]
  };

  function allEmployees(){
    try{return (typeof employees!=='undefined'&&Array.isArray(employees))?employees:[];}catch(e){return[];}
  }
  function routeTokens(route){
    const raw=String(route||'').toUpperCase();
    return{raw,tokens:raw.split(/[^A-Z0-9]+/).filter(Boolean)};
  }
  function matches(route,lookup){
    const {raw,tokens}=routeTokens(route),hits=[];
    Object.entries(lookup).forEach(([country,aliases])=>{
      if(aliases.some(a=>raw.includes(a)||tokens.includes(a)))hits.push(country);
    });
    return[...new Set(hits)];
  }
  function classifiedTrip(trip){return{hard:matches(trip.route,WAR_UNREST),kidnap:matches(trip.route,KIDNAP_ONLY)};}

  function clearLegacyTrips(){
    allEmployees().forEach(e=>{e.trips=[];});
    setStats({employee_count:0,total_days:0,days_remaining:250});
    const list=document.getElementById('employeesList');if(list)list.innerHTML='';
  }

  function setStats(s){
    const values={totalEmployees:s.employee_count||0,totalDays:s.total_days||0,daysRemaining:Number.isFinite(s.days_remaining)?s.days_remaining:250,avgDays:(s.employee_count?((s.total_days||0)/s.employee_count).toFixed(1):'0.0')};
    Object.entries(values).forEach(([id,v])=>{const el=document.getElementById(id);if(el)el.textContent=v;});
    const label=document.querySelector('#totalEmployees')?.closest('.stat-card')?.querySelector('.stat-label');
    if(label)label.textContent='Travelling Employees (2026/27)';
  }

  function hidePublicArchive(){
    document.querySelector('.archive-card')?.remove();
    document.querySelector('.export-all-wrap')?.remove();
  }

  function syncNote(text,error){
    let note=document.getElementById('trackerSyncNote');
    const grid=document.querySelector('.stats-grid');
    if(grid&&!note){note=document.createElement('div');note.id='trackerSyncNote';note.className='renewal-reset-note';grid.insertAdjacentElement('afterend',note);}
    if(note){note.classList.toggle('sync-error',!!error);note.innerHTML=text;}
  }

  function standingConflictNotice(){
    const banner=document.getElementById('pulseBanner');if(!banner)return;
    const title=banner.querySelector('.pulse-banner-title'),body=banner.querySelector('.pulse-banner-body');
    if(title)title.textContent='⚠️ Travel Security Notice — War, Unrest & Disruption';
    if(body)body.innerHTML='Certificate CGT P804302600 excludes travel to an <strong>Area of War, Unrest or Disruption</strong> unless declared and agreed by Underwriters before travel. For business travel this includes any country/region where the FCDO advises against <strong>ALL travel</strong>, plus Belarus, Russia, Ukraine, Gaza, Israel and Lebanon by name. Check FCDO advice before booking and again before departure.';
    if(localStorage.getItem('pulseBannerDismissed_v34')!=='1')banner.classList.remove('hidden');
    const dismiss=banner.querySelector('.pulse-btn.secondary');
    if(dismiss)dismiss.onclick=function(){localStorage.setItem('pulseBannerDismissed_v34','1');banner.classList.add('hidden');};
  }

  function middleEastAlert(){
    const banner=document.getElementById('fcdoBanner'),links=document.getElementById('fcdoLinks');if(!banner||!links)return;
    const codes=new Set();
    allEmployees().forEach(emp=>(emp.trips||[]).filter(t=>!t.canceled).forEach(trip=>{
      routeTokens(trip.route).tokens.forEach(code=>{if(MIDDLE_EAST[code])codes.add(code);});
    }));
    if(!codes.size){banner.classList.add('hidden');return;}
    banner.classList.remove('hidden');
    links.innerHTML=[...codes].sort().map(code=>{const[country,slug]=MIDDLE_EAST[code];return`<a class="fcdo-pill" href="https://www.gov.uk/foreign-travel-advice/${slug}" target="_blank" rel="noopener noreferrer">FCDO: ${country}</a>`;}).join('');
  }

  function restrictedTripBanner(){
    let box=document.getElementById('restrictedTripBanner');const hits=[];
    allEmployees().forEach(emp=>(emp.trips||[]).filter(t=>!t.canceled).forEach(trip=>{
      const c=classifiedTrip(trip);if(c.hard.length)hits.push({emp,trip,countries:c.hard});
    }));
    if(!hits.length){if(box)box.remove();return;}
    if(!box){
      box=document.createElement('div');box.id='restrictedTripBanner';box.className='restricted-trip-banner';
      const anchor=document.getElementById('fcdoBanner')||document.getElementById('pulseBanner');
      if(anchor)anchor.insertAdjacentElement('afterend',box);else document.querySelector('.stats-grid')?.insertAdjacentElement('beforebegin',box);
    }
    box.innerHTML='<div class="restricted-trip-title">⛔ Policy restriction detected in a current trip</div>'+
      hits.map(h=>`<div><strong>${h.emp.name}</strong> — ${h.trip.route}: ${h.countries.join(', ')}. <strong>Cover is excluded unless the trip was declared and agreed by Underwriters before travel.</strong></div>`).join('')+
      '<div class="restricted-trip-foot">This alert applies the named War/Unrest/Disruption endorsement. Always check current FCDO advice because additional regions can become restricted.</div>';
  }

  function overrideFlags(){
    if(flagsOverridden||typeof getInsuranceFlags!=='function')return;
    flagsOverridden=true;
    const legacy=getInsuranceFlags;
    getInsuranceFlags=function(trip){
      const base=legacy(trip).filter(f=>f.text!=='Geo limit');
      if(trip.canceled)return base;
      const c=classifiedTrip(trip);
      if(c.hard.length)base.push({text:'⛔ Restricted — cover excluded unless pre-agreed',tooltip:`Policy War/Unrest/Disruption restriction: ${c.hard.join(', ')}. Cover is excluded unless declared and agreed by Underwriters before travel.`});
      if(c.kidnap.length)base.push({text:'⚠️ Kidnap cover excluded',tooltip:`The Kidnap exclusion names ${c.kidnap.join(', ')}. This refers specifically to Kidnap cover and is not a blanket statement about every policy section.`});
      return base;
    };
  }

  function decorate(){
    document.querySelectorAll('.progress-label').forEach(el=>{el.textContent='Current 2026/27 administrative pool';});
    document.querySelectorAll('.flag').forEach(el=>{
      const t=el.textContent||'';if(t.includes('Restricted'))el.classList.add('flag-restricted');if(t.includes('Kidnap'))el.classList.add('flag-kidnap');
    });
  }

  function renderCurrent(summary,current){
    const target=allEmployees();
    target.splice(0,target.length,...(current.employees||[]));
    setStats(summary);
    overrideFlags();
    try{if(typeof renderEmployees==='function')renderEmployees();}catch(e){console.error('Current tracker render failed',e);}
    decorate();standingConflictNotice();middleEastAlert();restrictedTripBanner();
    syncNote(`<strong>2026/27 live pool:</strong> ${summary.total_days} days used/reserved • ${summary.days_remaining} remaining. The new policy year was reset to <strong>0 / 0 / 250</strong>; only trips entered for this policy period are counted.`,false);
  }

  async function loadCurrent(){
    try{
      const res=await fetch(API_BASE+'/api/tracker/current',{headers:{'Accept':'application/json'}});
      if(!res.ok)throw new Error('tracker '+res.status);
      const data=await res.json();
      renderCurrent(data.summary||{},data.current||{employees:[]});
    }catch(e){
      clearLegacyTrips();standingConflictNotice();middleEastAlert();restrictedTripBanner();
      syncNote('<strong>2026/27 baseline:</strong> 0 travelling employees • 0 days • 250 remaining. Live trip sync is temporarily unavailable.',true);
      console.error(e);
    }
  }

  function run(){
    hidePublicArchive();
    clearLegacyTrips();
    standingConflictNotice();
    overrideFlags();
    loadCurrent();
    window.setInterval(loadCurrent,60000);
    window.addEventListener('focus',loadCurrent);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();