import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/Preeti Naval/OneDrive/Desktop/Dsat Tool/DSAT_Audit_Tool.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the block to replace (lines 978-1076)
START = '// ALL AUDITS TABLE\n// ═══════════════════════════════════════════════════════════\nfunction getVisibleAudits() {'
END_MARKER = '  `).join(\'\');\n}\n'

start_idx = content.find(START)
end_idx = content.find(END_MARKER, start_idx) + len(END_MARKER)

if start_idx == -1:
    print('ERROR: start marker not found')
    exit(1)

NEW_CODE = '''// ALL AUDITS TABLE
// ═══════════════════════════════════════════════════════════
let _adminAuditCache = null;

function getVisibleAudits() {
  let audits = getData('audits', []);
  if (currentUser && currentUser.role !== 'admin') audits = audits.filter(a=>a.auditorId===currentUser.id);
  return audits;
}

function filterAudits(audits) {
  const fa   = (document.getElementById('filterAdvisor')?.value||'').toLowerCase();
  const fau  = document.getElementById('filterAuditor')?.value||'';
  const fcam = document.getElementById('filterCampaign')?.value||'';
  const fi   = document.getElementById('filterIssue')?.value||'';
  const fac  = document.getElementById('filterAcpt')?.value||'';
  const fdis = document.getElementById('filterDisposed')?.value||'';
  const fCF  = document.getElementById('filterCallFrom')?.value||'';
  const fCT  = document.getElementById('filterCallTo')?.value||'';
  const fAF  = document.getElementById('filterAuditFrom')?.value||'';
  const fAT  = document.getElementById('filterAuditTo')?.value||'';
  return audits.filter(a => {
    if (fa   && !(a.advisorName||'').toLowerCase().includes(fa)) return false;
    if (fau  && a.auditorName !== fau)  return false;
    if (fcam && a.campaign    !== fcam) return false;
    if (fi   && a.issueType   !== fi)   return false;
    if (fac  && a.acpt        !== fac)  return false;
    if (fdis && a.disposed    !== fdis) return false;
    if (fCF  && a.callDate  && a.callDate  < fCF) return false;
    if (fCT  && a.callDate  && a.callDate  > fCT) return false;
    if (fAF  && a.auditDate && a.auditDate < fAF) return false;
    if (fAT  && a.auditDate && a.auditDate > fAT) return false;
    return true;
  });
}

function populateFilterDropdowns(audits) {
  const set = (id, vals, label) => {
    const el = document.getElementById(id); if (!el) return;
    const cur = el.value;
    el.innerHTML = `<option value="">${label}</option>` +
      [...new Set(vals.filter(Boolean))].sort().map(v=>`<option ${v===cur?'selected':''}>${v}</option>`).join('');
  };
  set('filterAuditor',  audits.map(a=>a.auditorName), 'All Auditors');
  set('filterCampaign', audits.map(a=>a.campaign),    'All Campaigns');
  set('filterIssue',    audits.map(a=>a.issueType),   'All Issues');
  set('filterAcpt',     audits.map(a=>a.acpt),        'All ACPT');
}

function applyFilters() {
  if (_adminAuditCache) {
    const filtered = filterAudits(_adminAuditCache);
    document.getElementById('auditCount').textContent = filtered.length + ' of ' + _adminAuditCache.length;
    renderAuditsRows(filtered);
  } else {
    renderAuditsLocal();
  }
}

function clearFilters() {
  ['filterAdvisor','filterAuditor','filterCampaign','filterIssue','filterAcpt',
   'filterDisposed','filterCallFrom','filterCallTo','filterAuditFrom','filterAuditTo']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  applyFilters();
}

function renderAuditsTable() {
  const body = document.getElementById('auditsBody');
  if (!body) return;
  if (currentUser && currentUser.role === 'admin' && getScriptUrl()) {
    body.innerHTML = '<tr><td colspan="14" style="text-align:center;padding:40px;color:#64748b;font-size:13px;">⏳ Loading all QA audits from Google Sheets...</td></tr>';
    document.getElementById('auditsEmpty').classList.add('hidden');
    fetchAllAuditsFromSheets().then(data => {
      if (data && Array.isArray(data)) {
        _adminAuditCache = data;
        populateFilterDropdowns(data);
        const filtered = filterAudits(data);
        document.getElementById('auditCount').textContent = filtered.length + ' of ' + data.length;
        renderAuditsRows(filtered);
        renderDashboardCharts(data);
      } else {
        _adminAuditCache = null;
        renderAuditsLocal();
      }
    });
    return;
  }
  _adminAuditCache = null;
  renderAuditsLocal();
}

function renderAuditsLocal() {
  const allAudits = getVisibleAudits();
  populateFilterDropdowns(allAudits);
  const audits = filterAudits(allAudits);
  const countEl = document.getElementById('auditCount');
  if (countEl) countEl.textContent = audits.length + (allAudits.length !== audits.length ? ' of ' + allAudits.length : '');
  renderAuditsRows(audits);
}

function exportCurrentAudits() {
  const src = _adminAuditCache ? filterAudits(_adminAuditCache) : filterAudits(getVisibleAudits());
  const headers = ['Advisor Name','Partner','Calling Number','Auditor','Call Date','Audit Date',
    'Call ID','Campaign','Issue Type','Sub Issue','Disposed','ACPT','Reason for ACPT','DSAT Reason','Actionable Items'];
  const rows = src.map(a=>[a.advisorName,a.partner,a.callingNo,a.auditorName,a.callDate,a.auditDate,
    a.callId,a.campaign,a.issueType,a.subIssue,a.disposed,a.acpt,a.reasonAcpt,a.dsatReason,a.actionable]
    .map(v=>`"${(v||'').replace(/"/g,'""')}"`));
  const csv = '\\ufeff' + [headers,...rows].map(r=>r.join(',')).join('\\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
  link.download = `dsat_audits_${new Date().toISOString().split('T')[0]}.csv`;
  link.click();
}

'''

content = content[:start_idx] + NEW_CODE + content[end_idx:]

with open('C:/Users/Preeti Naval/OneDrive/Desktop/Dsat Tool/DSAT_Audit_Tool.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done! File patched successfully.')
print(f'Replaced from index {start_idx} to {end_idx}')
