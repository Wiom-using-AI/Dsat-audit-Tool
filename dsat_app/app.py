from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import sqlite3, hashlib, os, io, csv
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'dsat_tool_secret_2024'
DB = os.path.join(os.path.dirname(__file__), 'dsat.db')

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'auditor',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dispositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT NOT NULL,
            sub_issue_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dsat_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            reason TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS acpt_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS partner_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS campaign_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_name TEXT,
            partner TEXT,
            calling_number TEXT,
            auditor_id INTEGER,
            call_date TEXT,
            audit_date TEXT,
            call_id TEXT,
            campaign TEXT,
            issue_type TEXT,
            sub_issue_type TEXT,
            disposed_correctly TEXT,
            call_summary TEXT,
            areas_of_improvement TEXT,
            acpt TEXT,
            reason_for_acpt TEXT,
            dsat_reason TEXT,
            actionable_items TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(auditor_id) REFERENCES users(id)
        );
    ''')

    # Seed admin
    c.execute("SELECT id FROM users WHERE role='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                  ('Admin', 'admin@wiom.in', hash_pw('admin123'), 'admin'))

    # Seed dispositions
    c.execute("SELECT COUNT(*) FROM dispositions")
    if c.fetchone()[0] == 0:
        dispositions = [
            ('Internet Issues', 'Internet Supply Down'),
            ('Internet Issues', 'Recharge done but internet not working'),
            ('Internet Issues', 'Frequent Disconnection'),
            ('Internet Issues', 'Slow Speed/Range Issues'),
            ('Internet Issues', 'Optical Power Out of Range'),
            ('Cash Collection', 'No online payment method available'),
            ('Cash Collection', 'Trust issue'),
            ('Cash Collection', 'Customer Requests (App)'),
            ('Shifting', 'Inquiry'),
            ('Shifting', 'Within Premises'),
            ('Shifting', 'Outside Premises - Same Partner'),
            ('Shifting', 'Outside Premises - Different Partner'),
            ('Shifting', 'Outside Premises - No Partner'),
            ('Others', 'TV/Camera issue'),
            ('Others', 'Adapter issue'),
            ('Others', 'Improper installation'),
            ('Others', 'Other'),
            ('Others', 'Invoice requested'),
            ('Others', 'Router Issue and replacement'),
            ('Partner Misbehavior', 'Trying to install non-Wiom connection'),
            ('Partner Misbehavior', 'Took extra cash'),
            ('Partner Misbehavior', 'Rude behavior/threats'),
            ('Partner Misbehavior', 'Unauthorized router collection'),
            ('Payment Issues', 'Demand coupons/compensation'),
            ('Payment Issues', 'Autopay issue'),
            ('Payment Issues', 'Unable to Pay via App'),
            ('Payment Issues', 'Payment not reflecting'),
            ('Payment Issues', 'Help in renewal'),
            ('Remove Connection - Talk to Customer', 'Wiom Service Issue'),
            ('Remove Connection - Talk to Customer', 'Other reasons'),
            ('Refund', 'Service Issue'),
            ('Refund', 'Double payment'),
            ('Refund', 'Service not available in new area (shifting)'),
            ('Change Request', 'Change Name or Mobile Number'),
            ('Change Request', 'Change Plan'),
            ('Change Request', 'Wifi Name/Password'),
            ('Router Pickup', 'Due to Service Issue'),
            ('Router Pickup', 'Moving to a different city'),
            ('Router Pickup', 'Service not available in new area (shifting)'),
            ('Router Pickup', 'Disconnect / Discontinue Service (system)'),
            ('Product Explanation', 'What is Wiom / Recharge-wala ghar ka net'),
            ('Product Explanation', 'How it is different (recharge vs monthly)'),
            ('Serviceability / Area Check', 'Area serviceable check'),
            ('Serviceability / Area Check', 'Non-serviceable area'),
            ('Recharge & Pricing', 'Recharge Options / Price'),
            ('Recharge & Pricing', 'Recharge Duration'),
            ('Booking Process & Charges', 'How to book / process?'),
            ('Booking Process & Charges', 'Booking fee (Rs.100) & Security deposit (Rs.300)'),
            ('Booking Process & Charges', 'Payment Options'),
            ('Speed, Range & Devices', 'Speed'),
            ('Speed, Range & Devices', 'Range / Coverage'),
            ('Speed, Range & Devices', 'Devices / usage'),
            ('Installation Timeline Enquiry', 'Setup timeline (pre-booking info)'),
            ('App Issues', 'App not loading / blank (log page+issue)'),
            ('Booking Interest (Warm Lead)', 'Wants help to book / interested'),
            ('Incompete Calls', 'Voice Issue'),
            ('Incompete Calls', 'Disconnected by CX'),
            ('Other (Out of scope)', 'Misc not in above (iPhone, OTT, old plan)'),
        ]
        c.executemany("INSERT INTO dispositions (issue_type, sub_issue_type) VALUES (?,?)", dispositions)

    # Seed DSAT reasons
    c.execute("SELECT COUNT(*) FROM dsat_reasons")
    if c.fetchone()[0] == 0:
        reasons = [
            ('Agent Quality', 'Accurate resolution provided', 'Agent shared correct information or resolution related to the customer\'s query — customer remained dissatisfied for other reasons.'),
            ('Agent Quality', 'Incorrect information provided', 'Agent shared wrong details about Wiom\'s product, plan, process, or TAT, leading to customer dissatisfaction.'),
            ('Agent Quality', 'Incomplete information provided', 'Agent provided partial or missing details about a product, process, or resolution timeline — customer was not fully informed.'),
            ('Agent Quality', 'Query not fully addressed', 'For contacts with multiple queries, one or more concerns were left unresolved or unacknowledged.'),
            ('Agent Quality', 'Irrelevant response given', 'Agent\'s response did not address the customer\'s actual concern — off-topic or mismatched reply.'),
            ('Agent Quality', 'Expectation mismatch', 'Agent followed correct SOP and provided accurate information, but customer was dissatisfied due to unmet personal expectations.'),
            ('Agent Behaviour', 'Proactive assistance missing', 'Agent did not take initiative — e.g., failed to raise a ticket or service request on the customer\'s behalf when needed.'),
            ('Agent Behaviour', 'Rude or unprofessional behaviour', 'Agent was impolite, dismissive, or used inappropriate language during the interaction.'),
            ('Agent Behaviour', 'Closure check not done', 'Agent ended the interaction without confirming if the customer had any further concerns or assistance needed.'),
            ('Agent Behaviour', 'Language preference not followed', 'Communication was carried out in a language other than the customer\'s stated or preferred language.'),
            ('Agent Behaviour', 'Unnecessary probing', 'Agent asked repetitive or irrelevant questions despite information being available in the system — causing friction.'),
            ('Agent Behaviour', 'Poor attentiveness', 'Agent was inattentive or distracted during the interaction — missed key customer inputs or repeated questions already answered.'),
            ('Agent Behaviour', 'Poor call handling', 'Call was managed poorly — included unnecessary holds, abrupt disconnections, or failure to follow call etiquette.'),
            ('Agent Behaviour', 'Unnecessary team transfer', 'Customer was transferred to another team/queue without valid reason, causing delays and repeated explanation of the issue.'),
            ('Process Gaps', 'Escalation not done', 'Case required escalation to a senior or specialist team, but agent failed to escalate despite customer request or SOP requirement.'),
            ('Process Gaps', 'Incorrect ticket handling', 'Ticket was raised incorrectly, under the wrong category, or not updated — leading to delays or incorrect routing.'),
            ('Process Gaps', 'ISD marked resolved without fix', 'Installation service dispatch (ISD) ticket was closed by the technician without actually resolving the issue at the customer\'s premises.'),
            ('Process Gaps', 'No loop closure for installation delay', 'Customer was not kept informed about the delayed installation — no follow-up, callback, or status update was shared.'),
            ('Service & Network Issues', 'Network supply down', 'Internet service was unavailable in the customer\'s area due to a network outage, maintenance, or infrastructure failure.'),
            ('Service & Network Issues', 'Non-serviceable area', 'Customer\'s location is outside Wiom\'s current service coverage — installation or service cannot be provided.'),
            ('Service & Network Issues', 'Service access failure – active plan', 'Internet not working despite an active or recently recharged Wiom plan — caused by a backend, provisioning, or technical issue.'),
            ('Service & Network Issues', 'Recharge done – service still down (RDNI)', 'Customer recharged the plan but internet service was not restored — requires backend activation or technical intervention.'),
            ('Service & Network Issues', 'Service inactive – no recharge', 'Internet not working because the customer\'s plan has expired and no recharge has been done.'),
            ('Service & Network Issues', 'Wiom app not working', 'Customer is unable to access or use the Wiom app — includes login failures, crashes, or feature-level issues.'),
            ('Service & Network Issues', 'Installation date breached', 'Committed installation date passed without completion or rescheduling communication to the customer.'),
            ('Service & Network Issues', 'Service delay – resolution overdue', 'An ongoing service issue was not resolved within the committed TAT — customer followed up without receiving a fix.'),
            ('Service & Network Issues', 'Agent response delay', 'Customer experienced significant delay in receiving a response or update from the agent during the interaction.'),
            ('Billing & Payments', 'AutoPay issue', 'Customer\'s auto-payment failed, was incorrectly charged, or the AutoPay setup/cancellation was not handled as requested.'),
            ('Billing & Payments', 'Refund initiation delayed', 'Eligible refund was not initiated within the committed TAT — customer had to follow up without resolution.'),
        ]
        c.executemany("INSERT INTO dsat_reasons (category, reason, description) VALUES (?,?,?)", reasons)

    # Seed ACPT options (updated set)
    c.execute("SELECT COUNT(*) FROM acpt_options")
    if c.fetchone()[0] == 0:
        for opt in ['Agent', 'Customer', 'Process / Product', 'Technology', 'Service']:
            c.execute("INSERT OR IGNORE INTO acpt_options (label) VALUES (?)", (opt,))

    # Seed partner options
    c.execute("SELECT COUNT(*) FROM partner_options")
    if c.fetchone()[0] == 0:
        for p in ['Stefto', 'Cyfuture']:
            c.execute("INSERT OR IGNORE INTO partner_options (label) VALUES (?)", (p,))

    # Seed campaign options
    c.execute("SELECT COUNT(*) FROM campaign_options")
    if c.fetchone()[0] == 0:
        for cmp in ['Sales Queue', 'Service High Pain', 'Service Low Pain', 'Service Ticket', 'Status Queue']:
            c.execute("INSERT OR IGNORE INTO campaign_options (label) VALUES (?)", (cmp,))

    conn.commit()
    conn.close()

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        pw = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=? AND active=1",
                            (email, hash_pw(pw))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM audits").fetchone()[0]
    my_audits = conn.execute("SELECT COUNT(*) FROM audits WHERE auditor_id=?", (session['user_id'],)).fetchone()[0]

    reason_data = conn.execute("""
        SELECT dsat_reason, COUNT(*) as cnt FROM audits
        WHERE dsat_reason IS NOT NULL AND dsat_reason != ''
        GROUP BY dsat_reason ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    acpt_data = conn.execute("""
        SELECT acpt, COUNT(*) as cnt FROM audits
        WHERE acpt IS NOT NULL AND acpt != ''
        GROUP BY acpt
    """).fetchall()

    issue_data = conn.execute("""
        SELECT issue_type, COUNT(*) as cnt FROM audits
        WHERE issue_type IS NOT NULL AND issue_type != ''
        GROUP BY issue_type ORDER BY cnt DESC
    """).fetchall()

    trend_data = conn.execute("""
        SELECT strftime('%Y-%m', audit_date) as month, COUNT(*) as cnt
        FROM audits WHERE audit_date IS NOT NULL
        GROUP BY month ORDER BY month DESC LIMIT 6
    """).fetchall()

    disposed_data = conn.execute("""
        SELECT disposed_correctly, COUNT(*) as cnt FROM audits GROUP BY disposed_correctly
    """).fetchall()

    auditor_data = conn.execute("""
        SELECT u.name, COUNT(a.id) as cnt FROM audits a
        JOIN users u ON a.auditor_id = u.id
        GROUP BY a.auditor_id ORDER BY cnt DESC
    """).fetchall()

    recent = conn.execute("""
        SELECT a.*, u.name as auditor_name FROM audits a
        JOIN users u ON a.auditor_id = u.id
        ORDER BY a.created_at DESC LIMIT 10
    """).fetchall()

    conn.close()
    return render_template('dashboard.html',
        total=total, my_audits=my_audits,
        reason_data=reason_data, acpt_data=acpt_data,
        issue_data=issue_data, trend_data=trend_data,
        disposed_data=disposed_data, auditor_data=auditor_data,
        recent=recent)

# ─── AUDIT FORM ──────────────────────────────────────────────────────────────

@app.route('/audit/new', methods=['GET', 'POST'])
@login_required
def new_audit():
    conn = get_db()
    if request.method == 'POST':
        f = request.form
        audit_dt = f.get('audit_date') or date.today().isoformat()
        conn.execute("""
            INSERT INTO audits (advisor_name, partner, calling_number, auditor_id,
            call_date, audit_date, call_id, campaign, issue_type, sub_issue_type,
            disposed_correctly, call_summary, areas_of_improvement, acpt,
            reason_for_acpt, dsat_reason, actionable_items)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            f.get('advisor_name'), f.get('partner'), f.get('calling_number'),
            session['user_id'],
            f.get('call_date'), audit_dt,
            f.get('call_id'), f.get('campaign'),
            f.get('issue_type'), f.get('sub_issue_type'),
            f.get('disposed_correctly'), f.get('call_summary'),
            f.get('areas_of_improvement'), f.get('acpt'),
            f.get('reason_for_acpt'), f.get('dsat_reason'),
            f.get('actionable_items')
        ))
        conn.commit()
        conn.close()
        flash('Audit submitted successfully!', 'success')
        return redirect(url_for('all_audits'))

    issue_types = conn.execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type").fetchall()
    dsat_reasons = conn.execute("SELECT * FROM dsat_reasons ORDER BY category, reason").fetchall()
    acpt_options = conn.execute("SELECT * FROM acpt_options ORDER BY label").fetchall()
    partner_options = conn.execute("SELECT * FROM partner_options ORDER BY label").fetchall()
    campaign_options = conn.execute("SELECT * FROM campaign_options ORDER BY label").fetchall()
    conn.close()
    return render_template('audit_form.html',
        issue_types=issue_types, dsat_reasons=dsat_reasons,
        acpt_options=acpt_options, partner_options=partner_options,
        campaign_options=campaign_options, audit=None,
        today=date.today().isoformat())

@app.route('/audit/<int:audit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_audit(audit_id):
    conn = get_db()
    audit = conn.execute("SELECT * FROM audits WHERE id=?", (audit_id,)).fetchone()
    if not audit:
        conn.close()
        flash('Audit not found.', 'error')
        return redirect(url_for('all_audits'))
    if session['role'] != 'admin' and audit['auditor_id'] != session['user_id']:
        conn.close()
        flash('Access denied.', 'error')
        return redirect(url_for('all_audits'))

    if request.method == 'POST':
        f = request.form
        conn.execute("""
            UPDATE audits SET advisor_name=?, partner=?, calling_number=?,
            call_date=?, audit_date=?, call_id=?, campaign=?, issue_type=?, sub_issue_type=?,
            disposed_correctly=?, call_summary=?, areas_of_improvement=?,
            acpt=?, reason_for_acpt=?, dsat_reason=?, actionable_items=?
            WHERE id=?
        """, (
            f.get('advisor_name'), f.get('partner'), f.get('calling_number'),
            f.get('call_date'), f.get('audit_date'),
            f.get('call_id'), f.get('campaign'),
            f.get('issue_type'), f.get('sub_issue_type'),
            f.get('disposed_correctly'), f.get('call_summary'),
            f.get('areas_of_improvement'), f.get('acpt'),
            f.get('reason_for_acpt'), f.get('dsat_reason'),
            f.get('actionable_items'), audit_id
        ))
        conn.commit()
        conn.close()
        flash('Audit updated.', 'success')
        return redirect(url_for('all_audits'))

    issue_types = conn.execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type").fetchall()
    dsat_reasons = conn.execute("SELECT * FROM dsat_reasons ORDER BY category, reason").fetchall()
    acpt_options = conn.execute("SELECT * FROM acpt_options ORDER BY label").fetchall()
    partner_options = conn.execute("SELECT * FROM partner_options ORDER BY label").fetchall()
    campaign_options = conn.execute("SELECT * FROM campaign_options ORDER BY label").fetchall()
    conn.close()
    return render_template('audit_form.html',
        issue_types=issue_types, dsat_reasons=dsat_reasons,
        acpt_options=acpt_options, partner_options=partner_options,
        campaign_options=campaign_options, audit=audit,
        today=date.today().isoformat())

@app.route('/audit/<int:audit_id>/delete', methods=['POST'])
@admin_required
def delete_audit(audit_id):
    conn = get_db()
    conn.execute("DELETE FROM audits WHERE id=?", (audit_id,))
    conn.commit()
    conn.close()
    flash('Audit deleted.', 'success')
    return redirect(url_for('all_audits'))

# ─── ALL AUDITS (unified view) ────────────────────────────────────────────────

@app.route('/all-audits')
@login_required
def all_audits():
    conn = get_db()
    auditor_f = request.args.get('auditor', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    issue_f = request.args.get('issue_type', '')

    if session['role'] == 'admin':
        query = "SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id = u.id WHERE 1=1"
        params = []
    else:
        query = "SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id = u.id WHERE a.auditor_id=?"
        params = [session['user_id']]

    if auditor_f and session['role'] == 'admin':
        query += " AND a.auditor_id=?"; params.append(auditor_f)
    if date_from:
        query += " AND a.audit_date>=?"; params.append(date_from)
    if date_to:
        query += " AND a.audit_date<=?"; params.append(date_to)
    if issue_f:
        query += " AND a.issue_type=?"; params.append(issue_f)
    query += " ORDER BY a.created_at DESC"

    audits = conn.execute(query, params).fetchall()
    auditors = conn.execute("SELECT id, name FROM users WHERE active=1 ORDER BY name").fetchall()
    issue_types = conn.execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type").fetchall()
    conn.close()
    return render_template('audits_list.html', audits=audits,
                           title='All Audits',
                           auditors=auditors, issue_types=issue_types,
                           filters={'auditor': auditor_f, 'date_from': date_from,
                                    'date_to': date_to, 'issue_type': issue_f})

# ─── API ─────────────────────────────────────────────────────────────────────

@app.route('/api/sub-dispositions')
@login_required
def api_sub_dispositions():
    issue_type = request.args.get('issue_type', '')
    conn = get_db()
    rows = conn.execute("SELECT sub_issue_type FROM dispositions WHERE issue_type=? ORDER BY sub_issue_type",
                        (issue_type,)).fetchall()
    conn.close()
    return jsonify([r['sub_issue_type'] for r in rows])

@app.route('/api/dsat-reason-info')
@login_required
def api_dsat_reason_info():
    reason = request.args.get('reason', '')
    conn = get_db()
    row = conn.execute("SELECT description, category FROM dsat_reasons WHERE reason=?", (reason,)).fetchone()
    conn.close()
    if row:
        return jsonify({'description': row['description'], 'category': row['category']})
    return jsonify({'description': '', 'category': ''})

@app.route('/api/audits-feed')
@login_required
def api_audits_feed():
    conn = get_db()
    if session['role'] == 'admin':
        rows = conn.execute("""
            SELECT a.id, a.advisor_name, a.partner, a.calling_number,
                   a.call_date, a.audit_date, a.issue_type, a.sub_issue_type,
                   a.disposed_correctly, a.acpt, a.dsat_reason, a.campaign,
                   a.call_summary, a.areas_of_improvement, a.reason_for_acpt, a.actionable_items,
                   u.name as auditor_name
            FROM audits a JOIN users u ON a.auditor_id = u.id
            ORDER BY a.created_at DESC LIMIT 200
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT a.id, a.advisor_name, a.partner, a.calling_number,
                   a.call_date, a.audit_date, a.issue_type, a.sub_issue_type,
                   a.disposed_correctly, a.acpt, a.dsat_reason, a.campaign,
                   a.call_summary, a.areas_of_improvement, a.reason_for_acpt, a.actionable_items,
                   u.name as auditor_name
            FROM audits a JOIN users u ON a.auditor_id = u.id
            WHERE a.auditor_id=?
            ORDER BY a.created_at DESC LIMIT 200
        """, (session['user_id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ─── REPORTS ─────────────────────────────────────────────────────────────────

@app.route('/report/export')
@login_required
def export_report():
    conn = get_db()
    auditor_f = request.args.get('auditor', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    if session['role'] == 'admin':
        query = "SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id = u.id WHERE 1=1"
        params = []
        if auditor_f:
            query += " AND a.auditor_id=?"; params.append(auditor_f)
        if date_from:
            query += " AND a.audit_date>=?"; params.append(date_from)
        if date_to:
            query += " AND a.audit_date<=?"; params.append(date_to)
    else:
        query = "SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id = u.id WHERE a.auditor_id=?"
        params = [session['user_id']]

    audits = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Advisor Name', 'Partner', 'Calling Number', 'Auditor Name', 'Call Date',
                     'Audit Date', 'Call ID', 'Campaign', 'Issue Type', 'Sub Issue Type',
                     'Disposed Correctly', 'Call Summary', 'Areas of Improvement',
                     'ACPT', 'Reason for ACPT', 'D-Sat Reason', 'Actionable Items'])
    for a in audits:
        writer.writerow([a['advisor_name'], a['partner'], a['calling_number'], a['auditor_name'],
                         a['call_date'], a['audit_date'], a['call_id'], a['campaign'],
                         a['issue_type'], a['sub_issue_type'], a['disposed_correctly'],
                         a['call_summary'], a['areas_of_improvement'], a['acpt'],
                         a['reason_for_acpt'], a['dsat_reason'], a['actionable_items']])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f'dsat_report_{date.today()}.csv')

# ─── ADMIN: USERS ────────────────────────────────────────────────────────────

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY role, name").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    pw = request.form['password']
    role = request.form.get('role', 'auditor')
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)",
                     (name, email, hash_pw(pw), role))
        conn.commit()
        flash(f'User {name} added.', 'success')
    except sqlite3.IntegrityError:
        flash('Email already exists.', 'error')
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(uid):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if user and user['role'] != 'admin':
        conn.execute("UPDATE users SET active=? WHERE id=?", (0 if user['active'] else 1, uid))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(uid):
    conn = get_db()
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(request.form['new_password']), uid))
    conn.commit()
    conn.close()
    flash('Password reset.', 'success')
    return redirect(url_for('admin_users'))

# ─── ADMIN: DISPOSITIONS ─────────────────────────────────────────────────────

@app.route('/admin/dispositions')
@admin_required
def admin_dispositions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM dispositions ORDER BY issue_type, sub_issue_type").fetchall()
    conn.close()
    return render_template('admin_dispositions.html', dispositions=rows)

@app.route('/admin/dispositions/add', methods=['POST'])
@admin_required
def admin_add_disposition():
    issue = request.form['issue_type'].strip()
    sub = request.form['sub_issue_type'].strip()
    if issue and sub:
        conn = get_db()
        conn.execute("INSERT INTO dispositions (issue_type, sub_issue_type) VALUES (?,?)", (issue, sub))
        conn.commit()
        conn.close()
        flash('Disposition added.', 'success')
    return redirect(url_for('admin_dispositions'))

@app.route('/admin/dispositions/<int:did>/delete', methods=['POST'])
@admin_required
def admin_delete_disposition(did):
    conn = get_db()
    conn.execute("DELETE FROM dispositions WHERE id=?", (did,))
    conn.commit()
    conn.close()
    flash('Disposition deleted.', 'success')
    return redirect(url_for('admin_dispositions'))

# ─── ADMIN: DSAT REASONS ─────────────────────────────────────────────────────

@app.route('/admin/dsat-reasons')
@admin_required
def admin_dsat_reasons():
    conn = get_db()
    rows = conn.execute("SELECT * FROM dsat_reasons ORDER BY category, reason").fetchall()
    conn.close()
    return render_template('admin_dsat_reasons.html', reasons=rows)

@app.route('/admin/dsat-reasons/add', methods=['POST'])
@admin_required
def admin_add_dsat_reason():
    category = request.form['category'].strip()
    reason = request.form['reason'].strip()
    description = request.form['description'].strip()
    if category and reason:
        conn = get_db()
        conn.execute("INSERT INTO dsat_reasons (category, reason, description) VALUES (?,?,?)",
                     (category, reason, description))
        conn.commit()
        conn.close()
        flash('DSAT reason added.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

@app.route('/admin/dsat-reasons/<int:rid>/edit', methods=['POST'])
@admin_required
def admin_edit_dsat_reason(rid):
    conn = get_db()
    conn.execute("UPDATE dsat_reasons SET category=?, reason=?, description=? WHERE id=?",
                 (request.form['category'].strip(), request.form['reason'].strip(),
                  request.form['description'].strip(), rid))
    conn.commit()
    conn.close()
    flash('DSAT reason updated.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

@app.route('/admin/dsat-reasons/<int:rid>/delete', methods=['POST'])
@admin_required
def admin_delete_dsat_reason(rid):
    conn = get_db()
    conn.execute("DELETE FROM dsat_reasons WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    flash('DSAT reason deleted.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

# ─── ADMIN: ACPT OPTIONS ─────────────────────────────────────────────────────

@app.route('/admin/acpt')
@admin_required
def admin_acpt():
    conn = get_db()
    rows = conn.execute("SELECT * FROM acpt_options ORDER BY label").fetchall()
    conn.close()
    return render_template('admin_acpt.html', options=rows)

@app.route('/admin/acpt/add', methods=['POST'])
@admin_required
def admin_add_acpt():
    label = request.form['label'].strip()
    if label:
        conn = get_db()
        try:
            conn.execute("INSERT INTO acpt_options (label) VALUES (?)", (label,))
            conn.commit()
            flash('ACPT option added.', 'success')
        except sqlite3.IntegrityError:
            flash('Already exists.', 'error')
        conn.close()
    return redirect(url_for('admin_acpt'))

@app.route('/admin/acpt/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_acpt(oid):
    conn = get_db()
    conn.execute("DELETE FROM acpt_options WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    flash('ACPT option deleted.', 'success')
    return redirect(url_for('admin_acpt'))

# ─── ADMIN: PARTNER OPTIONS ──────────────────────────────────────────────────

@app.route('/admin/partners')
@admin_required
def admin_partners():
    conn = get_db()
    rows = conn.execute("SELECT * FROM partner_options ORDER BY label").fetchall()
    conn.close()
    return render_template('admin_simple_list.html',
                           title='Manage Partners',
                           subtitle='Partner dropdown options shown in audit form',
                           items=rows,
                           add_url=url_for('admin_add_partner'),
                           delete_url_name='admin_delete_partner',
                           placeholder='e.g. Cyfuture')

@app.route('/admin/partners/add', methods=['POST'])
@admin_required
def admin_add_partner():
    label = request.form['label'].strip()
    if label:
        conn = get_db()
        try:
            conn.execute("INSERT INTO partner_options (label) VALUES (?)", (label,))
            conn.commit()
            flash('Partner added.', 'success')
        except sqlite3.IntegrityError:
            flash('Already exists.', 'error')
        conn.close()
    return redirect(url_for('admin_partners'))

@app.route('/admin/partners/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_partner(oid):
    conn = get_db()
    conn.execute("DELETE FROM partner_options WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    flash('Partner deleted.', 'success')
    return redirect(url_for('admin_partners'))

# ─── ADMIN: CAMPAIGN OPTIONS ─────────────────────────────────────────────────

@app.route('/admin/campaigns')
@admin_required
def admin_campaigns():
    conn = get_db()
    rows = conn.execute("SELECT * FROM campaign_options ORDER BY label").fetchall()
    conn.close()
    return render_template('admin_simple_list.html',
                           title='Manage Campaigns',
                           subtitle='Campaign dropdown options shown in audit form',
                           items=rows,
                           add_url=url_for('admin_add_campaign'),
                           delete_url_name='admin_delete_campaign',
                           placeholder='e.g. Sales Queue')

@app.route('/admin/campaigns/add', methods=['POST'])
@admin_required
def admin_add_campaign():
    label = request.form['label'].strip()
    if label:
        conn = get_db()
        try:
            conn.execute("INSERT INTO campaign_options (label) VALUES (?)", (label,))
            conn.commit()
            flash('Campaign added.', 'success')
        except sqlite3.IntegrityError:
            flash('Already exists.', 'error')
        conn.close()
    return redirect(url_for('admin_campaigns'))

@app.route('/admin/campaigns/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_campaign(oid):
    conn = get_db()
    conn.execute("DELETE FROM campaign_options WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    flash('Campaign deleted.', 'success')
    return redirect(url_for('admin_campaigns'))

# ─── CHANGE PASSWORD ─────────────────────────────────────────────────────────

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form['current_password']
        new_pw = request.form['new_password']
        if request.form['confirm_password'] != new_pw:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('change_password'))
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=? AND password=?",
                            (session['user_id'], hash_pw(current))).fetchone()
        if not user:
            conn.close()
            flash('Current password incorrect.', 'error')
            return redirect(url_for('change_password'))
        conn.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), session['user_id']))
        conn.commit()
        conn.close()
        flash('Password changed.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('change_password.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
