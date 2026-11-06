/* F01 discovery workbench: synthetic baseline, human gates, append-only decisions. */
(function () {
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const api = async (path, options = {}) => {
    const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Er ging iets mis');
    return data;
  };
  const style = document.createElement('style');
  style.textContent = `
    .f01-modal{position:fixed;inset:0;background:#102c3b70;z-index:4;display:none;align-items:center;justify-content:center;padding:20px}
    .f01-modal.open{display:flex}.f01-dialog{width:min(1120px,100%);max-height:92vh;overflow:auto;background:#fff;border-radius:10px;box-shadow:0 24px 80px #102c3b40}
    .f01-head{padding:20px 23px;border-bottom:1px solid #e4e9ec;display:flex;justify-content:space-between;gap:16px}.f01-head h2{font-size:17px;margin:0}.f01-head p{color:#6f8190;font-size:12px;margin:4px 0 0}.f01-close{border:0;background:none;font-size:22px;color:#79909a;min-width:44px;min-height:44px}.f01-body{padding:20px 23px;background:#fbfcfc}.f01-note{padding:12px 14px;border-left:4px solid #b27a32;background:#fff8eb;color:#5f471e;border-radius:6px;font-size:14px;line-height:1.5;margin-bottom:16px}.f01-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr);gap:16px}.f01-card{background:#fff;border:1px solid #e4e9ec;border-radius:9px;padding:16px}.f01-card h3{font-size:14px;margin:0}.f01-card p{font-size:12px;color:#6f8190;margin:5px 0 0}.f01-chain{display:grid;gap:8px;margin-top:12px}.f01-node{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:9px;align-items:center;padding:10px 11px;border:1px solid #e4e9ec;border-radius:7px}.f01-marker{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;background:#e5f3f1;color:#147d79;font-size:11px;font-weight:700}.f01-role{font-size:10px;color:#6f8190}.f01-name{font-size:12px;font-weight:650}.f01-table-wrap{overflow-x:auto;margin-top:10px}.f01-table{width:100%;border-collapse:collapse;font-size:12px}.f01-table th,.f01-table td{padding:10px 8px;border-bottom:1px solid #edf0f2;text-align:left;vertical-align:top}.f01-table th{font-size:10px;color:#6f8190;font-weight:650;text-transform:uppercase;letter-spacing:.04em}.f01-table tr:last-child td{border-bottom:0}.f01-pill{font-size:10px;border-radius:12px;padding:4px 7px;white-space:nowrap}.f01-open{background:#fff3de;color:#8b6628}.f01-confirmed{background:#e5f3f1;color:#216d68}.f01-blocked{background:#fbeaea;color:#8e3d3d}.f01-decisions{display:grid;gap:8px;margin-top:10px}.f01-decision{padding:10px 12px;background:#f7f9f9;border:1px solid #e4e9ec;border-radius:7px}.f01-decision strong{font-size:11px}.f01-decision small{display:block;color:#6f8190;margin-top:3px}.f01-form{margin-top:14px;padding-top:14px;border-top:1px solid #e4e9ec}.f01-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}.f01-field{display:grid;gap:5px}.f01-field.full{grid-column:1/-1}.f01-field label{font-size:11px;font-weight:600;color:#4b626d}.f01-field input,.f01-field select,.f01-field textarea{width:100%;border:1px solid #dce4e7;border-radius:5px;padding:9px 10px;color:#172b3a;background:#fff;font-size:12px}.f01-field textarea{min-height:66px;resize:vertical}.f01-field input:focus,.f01-field select:focus,.f01-field textarea:focus,.f01-close:focus-visible{outline:3px solid #cde7e2;outline-offset:2px}.f01-foot{border-top:1px solid #e4e9ec;padding:14px 23px;display:flex;justify-content:flex-end;gap:8px}.f01-btn{border:1px solid #e4e9ec;background:#fff;color:#29404c;border-radius:6px;padding:9px 13px;font-size:12px;font-weight:600;min-height:44px}.f01-btn.primary{background:#147d79;color:#fff;border-color:#147d79}.f01-btn.primary:hover{background:#0f6965}.f01-error{color:#ac4c4c;font-size:11px;margin-top:8px}.f01-success{color:#216d68;font-size:11px;margin-top:8px}@media(max-width:800px){.f01-grid{grid-template-columns:1fr}.f01-form-grid{grid-template-columns:1fr}.f01-field.full{grid-column:auto}.f01-body{padding:16px}.f01-head{padding:16px}}
  `;
  document.head.appendChild(style);

  const nav = document.querySelector('.sidebar');
  if (!nav) return;
  nav.setAttribute('role', 'navigation');
  nav.setAttribute('aria-label', 'Volledige klantbediening');
  const brandSubline = nav.querySelector('.brand small');
  if (brandSubline) brandSubline.textContent = 'Klantbediening';
  const sourceItems = [...nav.querySelectorAll('.nav-item')];
  const itemByIndex = (index, label, role, icon, action) => {
    const item = sourceItems[index] || document.createElement('button');
    item.className = 'nav-item'; item.type = 'button'; item.innerHTML = `<span class="ico">${icon}</span><span class="nav-item-label">${label}</span><span class="nav-role">${role}</span>`;
    if (index === 0) { item.classList.add('active'); item.setAttribute('aria-current', 'page'); }
    if (action) item.onclick = action;
    return item;
  };
  const futureItem = (label, role, icon, message, action) => {
    const item = document.createElement('button'); item.className = 'nav-item nav-item-roadmap'; item.type = 'button'; item.innerHTML = `<span class="ico">${icon}</span><span class="nav-item-label">${label}</span><span class="nav-role">${role}</span>`;
    item.onclick = action || (() => window.showToast?.(message));
    return item;
  };
  const items = [
    {group:'PROSPECT & SALES', entries:[
      futureItem('Prospectdossier', 'Sales', '◌', 'Prospectdossier is als workflow-slice gepland.'),
      futureItem('Voorstel & prijs', 'Sales · Fee', '€', 'Voorstel & prijs is als workflow-slice gepland.')
    ]},
    {group:'ONBOARDEN ALS KLANT', entries:[
      itemByIndex(1, 'Klantdossier', 'Accountmanager', '◉', () => scrollToSection('customers')),
      itemByIndex(3, 'Afspraken & vereisten', 'Accountmanager · Legal', '▧'),
      itemByIndex(5, 'Keten & partijen', 'Operations · Risk', '⌘'),
      itemByIndex(4, 'Uitbesteding & risico', 'Risk · Compliance', '◈'),
      itemByIndex(6, 'Beleid & afspraken', 'Compliance · Legal', '◇')
    ]},
    {group:'DAGELIJKSE KLANTBEDIENING', entries:[
      itemByIndex(0, 'Klantoverzicht', 'Accountmanager', '▦'),
      itemByIndex(2, 'Wijzigingen beheren', 'Accountmanager · Operations', '⇄'),
      itemByIndex(9, 'Review & audit', 'Reviewer · Risk', '▤'),
      itemByIndex(10, 'Exports delen', 'Operations · Partner', '⇧')
    ]},
    {group:'PLATFORM & GOVERNANCE', entries:[
      itemByIndex(7, 'Identiteit & toegang', 'Platform · Security', '◉', () => openIdentityReadiness()),
      itemByIndex(8, 'Schema & parameters', 'Platform · Data', '⌗', () => openConfigurationSchemas()),
      futureItem('Pilot & open besluiten', 'Product · Legal', '◎', '', () => openDiscovery())
    ]}
  ];
  const firstLabel = nav.querySelector('.nav-label');
  [...nav.querySelectorAll('.nav-label')].forEach((label) => label.remove());
  const sideBottom = nav.querySelector('.side-bottom');
  const environmentLabel = sideBottom?.querySelector('span[style*="color:#6e929d"]');
  if (environmentLabel) environmentLabel.textContent = 'Alle personas · MVP';
  [...nav.querySelectorAll('.nav-item')].forEach((item) => item.remove());
  const makeLabel = (text) => { const element = document.createElement('div'); element.className = 'nav-label nav-label-spaced'; element.textContent = text; return element; };
  if (sideBottom) items.forEach((section) => { nav.insertBefore(makeLabel(section.group), sideBottom); section.entries.forEach((item) => nav.insertBefore(item, sideBottom)); });

  const modal = document.createElement('div');
  modal.className = 'f01-modal'; modal.id = 'f01DiscoveryModal';
  modal.setAttribute('role', 'dialog'); modal.setAttribute('aria-modal', 'true'); modal.setAttribute('aria-labelledby', 'f01Title');
  modal.innerHTML = `<div class="f01-dialog"><div class="f01-head"><div><div class="eyebrow">F01 · P0 DISCOVERY</div><h2 id="f01Title">Domein- en legal discovery</h2><p>Bevestig de pilotrichting zonder open juridische interpretaties als harde blokkade te activeren.</p></div><button class="f01-close" type="button" aria-label="Sluiten">×</button></div><div class="f01-body"><div class="f01-note"><strong>Menselijke gate:</strong> de waarden hieronder zijn synthetische prototype-baselines. Pilotklant, keten, beleidseigenaren en ADR-keuzes blijven <strong>te valideren door Compliance/Legal</strong> waar dat juridisch of beleidsmatig is.</div><div id="f01Content">Discovery laden…</div></div><div class="f01-foot"><button class="f01-btn" type="button" id="f01CloseBottom">Sluiten</button></div></div>`;
  document.body.appendChild(modal);
  const content = modal.querySelector('#f01Content');
  const statusLabel = {open:'Open', confirmed:'Bevestigd', blocked:'Geblokkeerd'};
  const pill = (status) => `<span class="f01-pill f01-${esc(status)}">${esc(statusLabel[status] || status)}</span>`;
  const render = (payload) => {
    const c = payload.catalog;
    const decisions = payload.decisions || [];
    content.innerHTML = `<div class="f01-grid"><section class="f01-card"><div style="display:flex;justify-content:space-between;gap:10px;align-items:start"><div><h3>Pilotprofiel</h3><p>Uitgangspunt voor de eerste keten</p></div>${pill(c.pilot.status)}</div><div style="margin-top:12px;font-size:13px"><strong>${esc(c.pilot.name)}</strong><br><span style="color:#6f8190">${esc(c.pilot.profile)}</span></div><p style="margin-top:10px">${esc(c.pilot.note)}</p><div class="f01-chain" aria-label="Synthetische eerste service- en managerketen">${c.chain.map((node, i) => `<div class="f01-node"><span class="f01-marker">${i + 1}</span><div><div class="f01-role">${esc(node.role)}</div><div class="f01-name">${esc(node.name)}</div></div><span class="version">${esc(node.service)}</span></div>`).join('')}</div></section><section class="f01-card"><h3>Open beslissingen</h3><p>Elke wijziging wordt als nieuwe versie geregistreerd.</p><div class="f01-decisions">${c.adr_decisions.map(a => `<div class="f01-decision"><strong>${esc(a.id)} · ${esc(a.title)}</strong><small>${esc(a.open)}</small><small>Eigenaar: ${esc(a.owner)}</small></div>`).join('')}</div></section></div><section class="f01-card" style="margin-top:16px"><h3>Data dictionary · prototypedekking</h3><p>Bronnen, versioning en resterende taxonomie-/scopebesluiten.</p><div class="f01-table-wrap"><table class="f01-table"><thead><tr><th>Domein</th><th>Bron</th><th>Versioning</th><th>Status</th></tr></thead><tbody>${c.data_dictionary.map(row => `<tr><td>${esc(row.domain)}</td><td><code>${esc(row.source)}</code></td><td>${esc(row.versioning)}</td><td>${esc(row.status)}</td></tr>`).join('')}</tbody></table></div></section><section class="f01-card" style="margin-top:16px"><h3>Beleidseigenaren</h3><p>Prototype-toewijzingen; formele eigenaar, scope en uitzonderingsproces zijn nog open.</p><div class="f01-table-wrap"><table class="f01-table"><thead><tr><th>Control</th><th>Onderwerp</th><th>Prototype-eigenaar</th><th>Status</th></tr></thead><tbody>${c.policy_owners.map(row => `<tr><td><code>${esc(row.code)}</code></td><td>${esc(row.title)}</td><td>${esc(row.owner)}</td><td>${pill(row.status)}</td></tr>`).join('')}</tbody></table></div></section><section class="f01-card"><div style="display:flex;justify-content:space-between;gap:12px;align-items:start"><div><h3>Beslisnotitie vastleggen</h3><p>Gebruik voor jouw bevestiging, een open punt of een expliciete blocker.</p></div><span class="f01-pill f01-open">append-only</span></div><form class="f01-form" id="f01DecisionForm"><div class="f01-form-grid"><div class="f01-field"><label for="f01Key">Besluitonderwerp</label><select id="f01Key" required><option value="pilot.profile">Pilotprofiel</option><option value="pilot.chain">Eerste keten</option><option value="data.dictionary">Data dictionary</option><option value="policy.owners">Beleidseigenaren</option><option value="adr.0002">ADR-0002</option><option value="adr.0003">ADR-0003</option><option value="adr.0004">ADR-0004</option><option value="adr.0005">ADR-0005</option></select></div><div class="f01-field"><label for="f01Status">Status</label><select id="f01Status"><option value="open">Open</option><option value="confirmed">Bevestigd voor synthetische pilot</option><option value="blocked">Geblokkeerd</option></select></div><div class="f01-field full"><label for="f01Decision">Beslisnotitie</label><textarea id="f01Decision" required placeholder="Bijv. welke synthetische pilotrichting je voor de demo bevestigt…"></textarea></div><div class="f01-field"><label for="f01Owner">Eigenaar / volgende actie</label><input id="f01Owner" required placeholder="Rol of team, geen echte persoonsgegevens"></div><div class="f01-field"><label for="f01Actor">Actor (synthetisch)</label><input id="f01Actor" value="synthetic.discovery-reviewer" required></div><div class="f01-field full"><label for="f01Rationale">Reden en bewijs</label><textarea id="f01Rationale" required placeholder="Waarom is dit bevestigd, open of geblokkeerd? Verwijs naar synthetisch bewijs of markeer te valideren door Compliance/Legal."></textarea></div></div><div id="f01Error" class="f01-error" aria-live="polite"></div><div style="display:flex;justify-content:flex-end;margin-top:10px"><button class="f01-btn primary" type="submit">Beslisnotitie opslaan</button></div></form></section><section class="f01-card"><h3>Recente beslisnotities</h3><div class="f01-decisions" id="f01DecisionList">${decisions.length ? decisions.map(d => `<div class="f01-decision"><strong>${esc(d.decision_key)} · v${d.version} ${pill(d.status)}</strong><small>${esc(d.decision)}</small><small>${esc(d.recorded_at)} · ${esc(d.actor)} · eigenaar: ${esc(d.owner)}</small></div>`).join('') : '<p>Nog geen F01-beslisnotities.</p>'}</div></section>`;
    modal.querySelector('#f01DecisionForm').addEventListener('submit', saveDecision);
  };
  async function load() { content.textContent = 'Discovery laden…'; try { render(await api('/api/v1/discovery')); } catch (error) { content.textContent = error.message; } }
  async function saveDecision(event) { event.preventDefault(); const form = event.currentTarget; const error = form.querySelector('#f01Error'); error.textContent = ''; const data = {decision_key: form.querySelector('#f01Key').value, status: form.querySelector('#f01Status').value, decision: form.querySelector('#f01Decision').value, owner: form.querySelector('#f01Owner').value, actor: form.querySelector('#f01Actor').value, rationale: form.querySelector('#f01Rationale').value}; try { await api('/api/v1/discovery/decisions', {method:'POST', body:JSON.stringify(data)}); await load(); } catch (err) { error.textContent = err.message; } }
  function close() { modal.classList.remove('open'); }
  const openDiscovery = () => { modal.classList.add('open'); load(); };
  const heading = document.querySelector('.heading');
  const crumb = document.querySelector('.crumb');
  if (crumb) crumb.innerHTML = 'Klantbediening <span style="padding:0 8px;color:#b4c0c4">/</span><b>Werkbank</b>';
  const eyebrow = document.querySelector('.heading .eyebrow');
  const title = document.querySelector('.heading h1');
  const subtitle = document.querySelector('.heading p');
  if (eyebrow) eyebrow.textContent = 'CLIENT CONFIGURATION · VOLLEDIGE KLANTBEDIENING';
  if (title) title.textContent = 'Klantbediening';
  if (subtitle) subtitle.textContent = 'Werk samen aan prospect, sales, onboarding en dagelijkse bediening van institutionele klanten.';
  if (heading) {
    const launch = document.createElement('button');
    launch.id = 'f01DiscoveryLaunch'; launch.className = 'btn primary'; launch.innerHTML = '◎ Pilot & open besluiten';
    heading.appendChild(launch);
    launch.addEventListener('click', openDiscovery);
  }
  modal.querySelector('.f01-close').addEventListener('click', close); modal.querySelector('#f01CloseBottom').addEventListener('click', close);
  modal.addEventListener('click', (event) => { if (event.target === modal) close(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && modal.classList.contains('open')) close(); });
})();
