// DSAT Audit Tool — Google Apps Script Backend
// Paste this in Google Apps Script and deploy as Web App

const SHEET_NAME = 'Audits';
const HEADERS = [
  'ID','Auditor Name','Advisor Name','Partner','Calling Number',
  'Call Date','Audit Date','Call ID','Campaign','Issue Type','Sub Issue Type',
  'Disposed Correctly','Call Summary','Areas of Improvement',
  'ACPT','Reason for ACPT','D-Sat Reason','Actionable Items','Submitted At'
];

function doGet(e) {
  const action = e.parameter.action;
  if (action === 'getAudits') return getAudits(e);
  return ContentService.createTextOutput(JSON.stringify({status:'ok'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    if (data.action === 'saveAudit') return saveAudit(data);
    if (data.action === 'deleteAudit') return deleteAudit(data);
    return ok({message:'unknown action'});
  } catch(err) {
    return error(err.toString());
  }
}

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold')
      .setBackground('#1a56db').setFontColor('#ffffff');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function saveAudit(data) {
  const sheet = getSheet();
  const id = data.id || Utilities.getUuid();

  // Check if audit already exists (for updates)
  const rows = sheet.getDataRange().getValues();
  let rowIndex = -1;
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] == data.id) { rowIndex = i + 1; break; }
  }

  const row = [
    id, data.auditorName, data.advisorName, data.partner, data.callingNo,
    data.callDate, data.auditDate, data.callId, data.campaign,
    data.issueType, data.subIssue, data.disposed, data.callSummary,
    data.areasImprovement, data.acpt, data.reasonAcpt, data.dsatReason,
    data.actionable, new Date().toLocaleString('en-IN')
  ];

  if (rowIndex > 0) {
    sheet.getRange(rowIndex, 1, 1, row.length).setValues([row]);
  } else {
    sheet.appendRow(row);
  }

  return ok({id: id, message: 'Audit saved'});
}

function deleteAudit(data) {
  const sheet = getSheet();
  const rows = sheet.getDataRange().getValues();
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] == data.id) {
      sheet.deleteRow(i + 1);
      return ok({message: 'Deleted'});
    }
  }
  return ok({message: 'Not found'});
}

function getAudits(e) {
  const sheet = getSheet();
  const rows = sheet.getDataRange().getValues();
  if (rows.length <= 1) return jsonResponse([]);

  const auditorFilter = e.parameter.auditor || '';
  const audits = [];

  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (auditorFilter && row[1] !== auditorFilter) continue;
    audits.push({
      id: row[0], auditorName: row[1], advisorName: row[2],
      partner: row[3], callingNo: row[4], callDate: row[5],
      auditDate: row[6], callId: row[7], campaign: row[8],
      issueType: row[9], subIssue: row[10], disposed: row[11],
      callSummary: row[12], areasImprovement: row[13],
      acpt: row[14], reasonAcpt: row[15], dsatReason: row[16],
      actionable: row[17], createdAt: row[18]
    });
  }

  return jsonResponse(audits.reverse());
}

function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function ok(data) {
  return ContentService
    .createTextOutput(JSON.stringify({status:'ok', ...data}))
    .setMimeType(ContentService.MimeType.JSON);
}

function error(msg) {
  return ContentService
    .createTextOutput(JSON.stringify({status:'error', message:msg}))
    .setMimeType(ContentService.MimeType.JSON);
}
