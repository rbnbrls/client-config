/* Multi-persona workflow pages: one clear page per navigation capability. */
(function () {
  const content = document.querySelector('.content');
  const nav = document.querySelector('.sidebar');
  if (!content || !nav) return;

  // The legacy dashboard loader can finish after a workflow page has replaced
  // the dashboard DOM. Keep its asynchronous refreshes safe on every page.
  ['renderCustomers', 'renderChanges', 'renderAudit'].forEach((name) => {
    const original = window[name];
    if (typeof original !== 'function') return;
    window[name] = (...args) => {
      const required = {renderCustomers:'customerList', renderChanges:'changeList', renderAudit:'auditList'}[name];
      if (!document.getElementById(required)) return;
      return original(...args);
    };
  });
  const originalLoadAll = window.loadAll;
  if (typeof originalLoadAll === 'function') {
    window.loadAll = (...args) => document.getElementById('metricCustomers') ? originalLoadAll(...args) : Promise.resolve();
  }

  const homeMarkup = content.innerHTML;
  const pages = {
    prospect: {group:'Prospect & sales', title:'Prospectdossier', persona:'Sales', intro:'Leg de eerste klantcontext, behoefte en mogelijke dienstverlening vast voordat een voorstel ontstaat.', status:'Roadmap', actions:[]},
    sales: {group:'Prospect & sales', title:'Voorstel & prijs', persona:'Sales · Fee', intro:'Werk een voorstel uit met scope, service-afspraken en kosten die later als klantconfiguratie kunnen worden overgenomen.', status:'Roadmap', actions:[]},
    onboarding: {group:'Onboarden als klant', title:'Klantdossier', persona:'Accountmanager', intro:'Doorloop de onboarding als één gezamenlijke workflow van eerste klantprofiel tot overdracht naar dagelijkse bediening.', status:'Prototype', onboarding:true},
    requirements: {group:'Onboarden als klant', title:'Afspraken & vereisten', persona:'Accountmanager · Legal', intro:'Leg klantspecifieke afspraken, vereisten, bronnen en reconciliatiestatus vast.', status:'Beschikbaar', action:'openClientRequirements'},
    chain: {group:'Onboarden als klant', title:'Keten & partijen', persona:'Operations · Risk', intro:'Breng fonds, fiduciair, managers, submanagers, custodian en andere partijen in samenhang in beeld.', status:'Beschikbaar', action:'openClientGraph'},
    outsourcing: {group:'Onboarden als klant', title:'Uitbesteding & risico', persona:'Risk · Compliance', intro:'Beoordeel de uitbestedingsrelatie en leg de menselijke DORA-/ICT-scopebeoordeling vast.', status:'Beschikbaar', action:'openDoraAssessments'},
    policy: {group:'Onboarden als klant', title:'Beleid & afspraken', persona:'Compliance · Legal', intro:'Beheer controls, bronreviews, beleidsbesluiten en klantvarianten zonder onbevestigde normen hard te blokkeren.', status:'Beschikbaar', action:'openPolicies'},
    overview: {group:'Dagelijkse klantbediening', title:'Klantoverzicht', persona:'Accountmanager', intro:'Bekijk de actuele klantbediening, configuratiestatus, open wijzigingen en recente auditactiviteit.', status:'Startpunt', overview:true},
    changes: {group:'Dagelijkse klantbediening', title:'Wijzigingen beheren', persona:'Accountmanager · Operations', intro:'Simuleer, review, keur goed en activeer wijzigingen met een herleidbare audittrail.', status:'Beschikbaar', action:'openChange'},
    review: {group:'Dagelijkse klantbediening', title:'Review & audit', persona:'Reviewer · Risk', intro:'Controleer bewijs, acties, beslissingen en publicatiestatus voordat een wijziging of export verder gaat.', status:'Beschikbaar', action:'openAudit'},
    exports: {group:'Dagelijkse klantbediening', title:'Exports delen', persona:'Operations · Partner', intro:'Maak gecontroleerde partnerexports en volg welke versie wanneer en met wie is gedeeld.', status:'Beschikbaar', action:'showToast', message:'Partnerprofielen zijn beschikbaar via de API.'},
    identity: {group:'Platform & governance', title:'Identiteit & toegang', persona:'Platform · Security', intro:'Bekijk de readiness voor echte identiteit, SSO, claims en functiescheiding.', status:'Voorbereiding', action:'openIdentityReadiness'},
    schema: {group:'Platform & governance', title:'Schema & parameters', persona:'Platform · Data', intro:'Beheer versieerbare parameterdefinities en valideer configuratie tegen de juiste schemaversie.', status:'Beschikbaar', action:'openConfigurationSchemas'},
    discovery: {group:'Platform & governance', title:'Pilot & open besluiten', persona:'Product · Legal', intro:'Leg pilotprofiel, eerste keten, data dictionary, beleidseigenaren en open ADR-besluiten vast.', status:'Menselijke gate', action:'openDiscovery'}
  };

  const action = (page) => {
    if (page.action === 'showToast') return () => window.showToast?.(page.message);
    if (page.action && typeof window[page.action] === 'function') return () => window[page.action]();
    return null;
  };
  const button = (label, className, handler) => {
    const el = document.createElement('button'); el.type = 'button'; el.className = className; el.textContent = label;
    if (handler) el.addEventListener('click', handler); return el;
  };
  const pageKeyFor = (label) => ({
    'Prospectdossier':'prospect','Voorstel & prijs':'sales','Klantdossier':'onboarding','Afspraken & vereisten':'requirements',
    'Keten & partijen':'chain','Uitbesteding & risico':'outsourcing','Beleid & afspraken':'policy','Klantoverzicht':'overview',
    'Wijzigingen beheren':'changes','Review & audit':'review','Exports delen':'exports','Identiteit & toegang':'identity',
    'Schema & parameters':'schema','Pilot & open besluiten':'discovery'
  }[label]);
  const setActive = (key) => nav.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.page === key));
  const pageLink = (key, label) => button(label, 'btn', () => openPage(key));
  const openAction = (page) => {
    const handler = action(page);
    if (handler) handler();
    else window.showToast?.(`${page.title} is als workflow-slice gepland.`);
  };
  const renderStandard = (key, page) => {
    const shell = document.createElement('div'); shell.className = 'workflow-page';
    shell.innerHTML = `<div class="workflow-breadcrumb"><span>${page.group}</span><b> / ${page.title}</b></div><div class="workflow-heading"><div><div class="eyebrow">${page.persona}</div><h1>${page.title}</h1><p>${page.intro}</p></div><span class="workflow-status">${page.status}</span></div><div class="workflow-grid"><section class="workflow-card workflow-card-primary"><div class="workflow-card-kicker">Wat je hier doet</div><h2>${page.title}</h2><p>${page.intro}</p><div class="workflow-actions"></div></section><section class="workflow-card"><div class="workflow-card-kicker">Samenwerking</div><h2>Persona in ontwikkeling</h2><p>Deze functie is nu zichtbaar voor het hele team. Later worden toegang, taken en goedkeuringen per persona ingericht.</p><div class="workflow-persona">${page.persona}</div></section></div><section class="workflow-next"><div><div class="workflow-card-kicker">Klantreis</div><h2>Volgende stap</h2><p>Werk vanuit de klantreis verder of open een aangrenzende functie.</p></div><div class="workflow-actions workflow-actions-wrap"></div></section>`;
    const actions = shell.querySelector('.workflow-card-primary .workflow-actions');
    if (page.action || page.status === 'Roadmap' || page.status === 'Voorbereiding' || page.status === 'Menselijke gate') actions.append(button(page.status === 'Roadmap' ? 'Open roadmap-status' : `Open ${page.title}`, 'btn primary', () => openAction(page)));
    actions.append(button('Terug naar klantbediening', 'btn', () => openPage('overview')));
    const next = shell.querySelector('.workflow-actions-wrap');
    const keys = Object.keys(pages); const index = keys.indexOf(key);
    [keys[index - 1], keys[index + 1]].filter(Boolean).forEach((nextKey) => next.append(pageLink(nextKey, pages[nextKey].title)));
    return shell;
  };
  const renderOverview = () => {
    const shell = document.createElement('div'); shell.className = 'workflow-page';
    shell.innerHTML = `<div class="workflow-breadcrumb"><span>Dagelijkse klantbediening</span><b> / Klantoverzicht</b></div><div class="workflow-heading"><div><div class="eyebrow">ACCOUNTMANAGER · ALLE PERSONAS</div><h1>Klantoverzicht</h1><p>Start bij de klantrelatie en navigeer vervolgens naar onboarding, wijzigingen, review of exports.</p></div><span class="workflow-status">Startpunt</span></div><section class="workflow-card workflow-card-primary"><div class="workflow-card-kicker">Actieve klantbediening</div><h2>Werk vanuit de klantrelatie</h2><p>Dezelfde klantcontext loopt door alle fases heen. Kies een klant in het bestaande overzicht of start een nieuwe wijziging.</p><div class="workflow-actions" id="overviewActions"></div></section><div class="workflow-grid workflow-grid-three"><section class="workflow-card"><div class="workflow-card-kicker">1 · Onboarding</div><h2>Nieuwe klant door de keten</h2><p>Doorloop het volledige onboardingspad met één gezamenlijke workflow.</p><div class="workflow-actions" id="overviewOnboarding"></div></section><section class="workflow-card"><div class="workflow-card-kicker">2 · Dagelijkse bediening</div><h2>Wijziging beheren</h2><p>Bekijk impact, review en activeer gecontroleerde configuratie.</p><div class="workflow-actions" id="overviewChanges"></div></section><section class="workflow-card"><div class="workflow-card-kicker">3 · Verantwoording</div><h2>Bewijs & delen</h2><p>Controleer audit en deel versiegebonden exports.</p><div class="workflow-actions" id="overviewReview"></div></section></div>`;
    shell.querySelector('#overviewActions').append(button('Bestaand dashboard openen', 'btn primary', () => { content.innerHTML = homeMarkup; setActive('overview'); window.loadAll?.(); }));
    shell.querySelector('#overviewOnboarding').append(button('Start onboarding', 'btn', () => openPage('onboarding')));
    shell.querySelector('#overviewChanges').append(button('Wijziging beheren', 'btn', () => openPage('changes')));
    shell.querySelector('#overviewReview').append(button('Review & audit', 'btn', () => openPage('review')));
    return shell;
  };
  const onboardingSteps = [
    ['prospect','Prospect & sales','Leg klantcontext en aanleiding vast.'],
    ['requirements','Afspraken & vereisten','Bevestig diensten, SLA, rapportage en klantvoorwaarden.'],
    ['chain','Keten & partijen','Breng fonds, fiduciair, managers en custodian in kaart.'],
    ['outsourcing','Uitbesteding & risico','Leg uitbestedingsscope, risico’s en reviewpunten vast.'],
    ['policy','Beleid & afspraken','Bevestig controls, uitzonderingen en overdracht naar bediening.']
  ];
  const renderOnboarding = () => {
    const shell = document.createElement('div'); shell.className = 'workflow-page';
    shell.innerHTML = `<div class="workflow-breadcrumb"><span>Onboarden als klant</span><b> / Klantdossier</b></div><div class="workflow-heading"><div><div class="eyebrow">ACCOUNTMANAGER · SAMENWERKEND TEAM</div><h1>Klant onboarding</h1><p>Een doorlopende workflow voor de overgang van prospect naar actieve klantbediening. Rollen zijn in deze fase niet gescheiden.</p></div><span class="workflow-status">Prototype</span></div><section class="workflow-card onboarding-card"><div class="workflow-card-kicker">Onboarding in 5 stappen</div><div class="onboarding-stepper"></div><div class="onboarding-detail"></div><div class="workflow-actions onboarding-actions"></div></section><section class="workflow-next"><div><div class="workflow-card-kicker">Overdracht</div><h2>Gereed voor dagelijkse bediening?</h2><p>Na de laatste stap is de klantcontext klaar voor wijzigingen, review en exports. Open functies blijven vanuit het menu beschikbaar.</p></div><div class="workflow-actions"><button class="btn" type="button" data-open="overview">Ga naar klantoverzicht</button></div></section>`;
    let current = 0;
    const stepper = shell.querySelector('.onboarding-stepper'), detail = shell.querySelector('.onboarding-detail'), actions = shell.querySelector('.onboarding-actions');
    const draw = () => { stepper.innerHTML = onboardingSteps.map((step, i) => `<button type="button" class="onboarding-step ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}" data-step="${i}"><span>${i + 1}</span><b>${step[1]}</b></button>`).join(''); const step = onboardingSteps[current]; detail.innerHTML = `<div class="workflow-card-kicker">Stap ${current + 1} van ${onboardingSteps.length}</div><h2>${step[1]}</h2><p>${step[2]}</p><div class="workflow-persona">Gezamenlijke werkstap · geen rolbeperking</div>`; actions.innerHTML = ''; if (current > 0) actions.append(button('Vorige stap', 'btn', () => { current -= 1; draw(); })); actions.append(button(current === onboardingSteps.length - 1 ? 'Onboarding afronden' : 'Volgende stap', 'btn primary', () => { if (current < onboardingSteps.length - 1) { current += 1; draw(); } else window.showToast?.('Onboarding is klaar voor overdracht naar dagelijkse klantbediening.'); })); stepper.querySelectorAll('[data-step]').forEach((el) => el.addEventListener('click', () => { current = Number(el.dataset.step); draw(); })); };
    draw(); shell.querySelector('[data-open="overview"]').addEventListener('click', () => openPage('overview')); return shell;
  };
  function openPage(key, updateHash = true) { const page = pages[key] || pages.overview; setActive(key); content.innerHTML = ''; content.append(key === 'overview' ? renderOverview() : key === 'onboarding' ? renderOnboarding() : renderStandard(key, page)); if (updateHash) history.pushState({page:key}, '', `#${key}`); window.scrollTo({top:0, behavior:'smooth'}); }
  nav.querySelectorAll('.nav-item').forEach((item) => { const label = item.querySelector('.nav-item-label')?.textContent.trim(); const key = pageKeyFor(label); if (key) { item.dataset.page = key; item.onclick = () => openPage(key); } });
  document.addEventListener('click', (event) => { const trigger = event.target.closest('[data-open]'); if (trigger) openPage(trigger.dataset.open); });
  window.addEventListener('popstate', () => openPage(location.hash.slice(1) || 'overview', false));
  const initial = location.hash.slice(1); if (initial && pages[initial]) setTimeout(() => openPage(initial, false), 700);
})();
