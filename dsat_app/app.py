from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import sqlite3, hashlib, os, io, csv
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dsat_wiom_secret_2024')

# Support both PostgreSQL (cloud) and SQLite (local)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

DB = os.path.join(os.path.dirname(__file__), 'dsat.db')

def get_db():
    if DATABASE_URL:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def is_pg():
    return bool(DATABASE_URL)

def ph(n):
    return '%s' if is_pg() else '?'

def q(sql):
    if is_pg():
        return sql.replace('?', '%s').replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY').replace('CURRENT_TIMESTAMP', 'NOW()')
    return sql

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

def db_execute(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    try:
        if is_pg():
            cur = conn.cursor()
            cur.execute(q(sql), params)
            result = None
            if fetchone:
                result = cur.fetchone()
                result = dict(result) if result else None
            elif fetchall:
                result = [dict(r) for r in cur.fetchall()]
            if commit:
                conn.commit()
            return result
        else:
            cur = conn.execute(sql, params)
            if fetchone:
                r = cur.fetchone()
                return dict(r) if r else None
            elif fetchall:
                return [dict(r) for r in cur.fetchall()]
            if commit:
                conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def init_db():
    conn = get_db()
    c = conn.cursor()
    sep = ';' if not is_pg() else None

    tables = [
        '''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'auditor',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT 'NOW()'
        )''',
        '''CREATE TABLE IF NOT EXISTS dispositions (
            id SERIAL PRIMARY KEY,
            issue_type TEXT NOT NULL,
            sub_issue_type TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS dsat_reasons (
            id SERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            reason TEXT NOT NULL,
            description TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS acpt_options (
            id SERIAL PRIMARY KEY,
            label TEXT NOT NULL UNIQUE
        )''',
        '''CREATE TABLE IF NOT EXISTS partner_options (
            id SERIAL PRIMARY KEY,
            label TEXT NOT NULL UNIQUE
        )''',
        '''CREATE TABLE IF NOT EXISTS campaign_options (
            id SERIAL PRIMARY KEY,
            label TEXT NOT NULL UNIQUE
        )''',
        '''CREATE TABLE IF NOT EXISTS audits (
            id SERIAL PRIMARY KEY,
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
            created_at TEXT
        )'''
    ]

    if is_pg():
        for t in tables:
            c.execute(t)
        conn.commit()
    else:
        # SQLite — use original schema
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
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
                advisor_name TEXT, partner TEXT, calling_number TEXT,
                auditor_id INTEGER, call_date TEXT, audit_date TEXT,
                call_id TEXT, campaign TEXT, issue_type TEXT,
                sub_issue_type TEXT, disposed_correctly TEXT,
                call_summary TEXT, areas_of_improvement TEXT,
                acpt TEXT, reason_for_acpt TEXT, dsat_reason TEXT,
                actionable_items TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(auditor_id) REFERENCES users(id)
            );
        ''')
        conn.commit()
    conn.close()

    # Seed admin
    existing = db_execute("SELECT id FROM users WHERE role='admin'", fetchone=True)
    if not existing:
        db_execute("INSERT INTO users (username, name, password, role) VALUES (?,?,?,?)",
                   ('admin', 'Admin', hash_pw('admin123'), 'admin'), commit=True)

    # Seed auditors
    auditors = [
        ('sanjana','Sanjana'),('rehmat','Rehmat'),('rohan','Rohan'),
        ('avakash','Avakash'),('deepakshi','Deepakshi'),('rashi','Rashi'),
        ('sajal','Sajal'),('ankita','Ankita'),('anita','Anita'),
        ('nisha','Nisha'),('vikas','Vikas'),('lalit','Lalit'),
    ]
    for uname, name in auditors:
        ex = db_execute("SELECT id FROM users WHERE username=?", (uname,), fetchone=True)
        if not ex:
            db_execute("INSERT INTO users (username, name, password, role) VALUES (?,?,?,?)",
                       (uname, name, hash_pw('Wiom@123'), 'auditor'), commit=True)

    # Seed dispositions
    cnt = db_execute("SELECT COUNT(*) as c FROM dispositions", fetchone=True)
    if (cnt or {}).get('c', cnt.get('COUNT(*)') if cnt else 0) == 0 if cnt else True:
        dispositions = [
            ('Internet Issues','Internet Supply Down'),('Internet Issues','Recharge done but internet not working'),
            ('Internet Issues','Frequent Disconnection'),('Internet Issues','Slow Speed/Range Issues'),
            ('Internet Issues','Optical Power Out of Range'),('Cash Collection','No online payment method available'),
            ('Cash Collection','Trust issue'),('Cash Collection','Customer Requests (App)'),
            ('Shifting','Inquiry'),('Shifting','Within Premises'),('Shifting','Outside Premises - Same Partner'),
            ('Shifting','Outside Premises - Different Partner'),('Shifting','Outside Premises - No Partner'),
            ('Others','TV/Camera issue'),('Others','Adapter issue'),('Others','Improper installation'),
            ('Others','Other'),('Others','Invoice requested'),('Others','Router Issue and replacement'),
            ('Partner Misbehavior','Trying to install non-Wiom connection'),('Partner Misbehavior','Took extra cash'),
            ('Partner Misbehavior','Rude behavior/threats'),('Partner Misbehavior','Unauthorized router collection'),
            ('Payment Issues','Demand coupons/compensation'),('Payment Issues','Autopay issue'),
            ('Payment Issues','Unable to Pay via App'),('Payment Issues','Payment not reflecting'),
            ('Payment Issues','Help in renewal'),('Remove Connection - Talk to Customer','Wiom Service Issue'),
            ('Remove Connection - Talk to Customer','Other reasons'),('Refund','Service Issue'),
            ('Refund','Double payment'),('Refund','Service not available in new area (shifting)'),
            ('Change Request','Change Name or Mobile Number'),('Change Request','Change Plan'),
            ('Change Request','Wifi Name/Password'),('Router Pickup','Due to Service Issue'),
            ('Router Pickup','Moving to a different city'),('Router Pickup','Service not available in new area (shifting)'),
            ('Router Pickup','Disconnect / Discontinue Service (system)'),
            ('Product Explanation','What is Wiom / Recharge-wala ghar ka net'),
            ('Product Explanation','How it is different (recharge vs monthly)'),
            ('Serviceability / Area Check','Area serviceable check'),('Serviceability / Area Check','Non-serviceable area'),
            ('Recharge & Pricing','Recharge Options / Price'),('Recharge & Pricing','Recharge Duration'),
            ('Booking Process & Charges','How to book / process?'),
            ('Booking Process & Charges','Booking fee (Rs.100) & Security deposit (Rs.300)'),
            ('Booking Process & Charges','Payment Options'),('Speed, Range & Devices','Speed'),
            ('Speed, Range & Devices','Range / Coverage'),('Speed, Range & Devices','Devices / usage'),
            ('Installation Timeline Enquiry','Setup timeline (pre-booking info)'),
            ('App Issues','App not loading / blank (log page+issue)'),
            ('Booking Interest (Warm Lead)','Wants help to book / interested'),
            ('Incomplete Calls','Voice Issue'),('Incomplete Calls','Disconnected by CX'),
            ('Other (Out of scope)','Misc not in above (iPhone, OTT, old plan)'),
        ]
        for d in dispositions:
            db_execute("INSERT INTO dispositions (issue_type, sub_issue_type) VALUES (?,?)", d, commit=True)

    cnt2 = db_execute("SELECT COUNT(*) as c FROM dsat_reasons", fetchone=True)
    if (cnt2 or {}).get('c', 0) == 0:
        reasons = [
            ('Agent Quality','Accurate resolution provided',"Agent shared correct information — customer remained dissatisfied for other reasons."),
            ('Agent Quality','Incorrect information provided',"Agent shared wrong details about Wiom's product, plan, process, or TAT."),
            ('Agent Quality','Incomplete information provided',"Agent provided partial or missing details — customer was not fully informed."),
            ('Agent Quality','Query not fully addressed',"One or more customer concerns were left unresolved or unacknowledged."),
            ('Agent Quality','Irrelevant response given',"Agent's response did not address the customer's actual concern."),
            ('Agent Quality','Expectation mismatch',"Agent followed correct SOP but customer was dissatisfied due to unmet personal expectations."),
            ('Agent Behaviour','Proactive assistance missing',"Agent did not take initiative — failed to raise a ticket or service request when needed."),
            ('Agent Behaviour','Rude or unprofessional behaviour',"Agent was impolite, dismissive, or used inappropriate language."),
            ('Agent Behaviour','Closure check not done',"Agent ended the interaction without confirming if customer had further concerns."),
            ('Agent Behaviour','Language preference not followed',"Communication in a language other than the customer's stated preference."),
            ('Agent Behaviour','Unnecessary probing',"Agent asked repetitive or irrelevant questions — causing friction."),
            ('Agent Behaviour','Poor attentiveness',"Agent was inattentive — missed key customer inputs or repeated questions already answered."),
            ('Agent Behaviour','Poor call handling',"Call managed poorly — unnecessary holds, abrupt disconnections."),
            ('Agent Behaviour','Unnecessary team transfer',"Customer transferred without valid reason, causing delays."),
            ('Process Gaps','Escalation not done',"Case required escalation but agent failed to escalate."),
            ('Process Gaps','Incorrect ticket handling',"Ticket raised incorrectly or not updated — leading to delays."),
            ('Process Gaps','ISD marked resolved without fix',"ISD ticket closed by technician without resolving the issue."),
            ('Process Gaps','No loop closure for installation delay',"Customer not kept informed about delayed installation."),
            ('Service & Network Issues','Network supply down',"Internet unavailable due to outage, maintenance, or infrastructure failure."),
            ('Service & Network Issues','Non-serviceable area',"Customer location outside Wiom's current service coverage."),
            ('Service & Network Issues','Service access failure – active plan',"Internet not working despite an active or recently recharged plan."),
            ('Service & Network Issues','Recharge done – service still down (RDNI)',"Customer recharged but internet service was not restored."),
            ('Service & Network Issues','Service inactive – no recharge',"Internet not working because the customer's plan has expired."),
            ('Service & Network Issues','Wiom app not working',"Customer unable to access or use the Wiom app."),
            ('Service & Network Issues','Installation date breached',"Committed installation date passed without completion."),
            ('Service & Network Issues','Service delay – resolution overdue',"Ongoing service issue not resolved within committed TAT."),
            ('Service & Network Issues','Agent response delay',"Customer experienced significant delay in receiving a response."),
            ('Billing & Payments','AutoPay issue',"Auto-payment failed, incorrectly charged, or setup/cancellation not handled."),
            ('Billing & Payments','Refund initiation delayed',"Eligible refund not initiated within committed TAT."),
        ]
        for r in reasons:
            db_execute("INSERT INTO dsat_reasons (category, reason, description) VALUES (?,?,?)", r, commit=True)

    cnt3 = db_execute("SELECT COUNT(*) as c FROM acpt_options", fetchone=True)
    if (cnt3 or {}).get('c', 0) == 0:
        for opt in ['Agent','Customer','Process / Product','Technology','Service']:
            db_execute("INSERT OR IGNORE INTO acpt_options (label) VALUES (?)", (opt,), commit=True)

    cnt4 = db_execute("SELECT COUNT(*) as c FROM partner_options", fetchone=True)
    if (cnt4 or {}).get('c', 0) == 0:
        for p in ['Stefto','Cyfuture']:
            db_execute("INSERT OR IGNORE INTO partner_options (label) VALUES (?)", (p,), commit=True)

    cnt5 = db_execute("SELECT COUNT(*) as c FROM campaign_options", fetchone=True)
    if (cnt5 or {}).get('c', 0) == 0:
        for cmp in ['Sales Queue','Service High Pain','Service Low Pain','Service Ticket','Status Queue']:
            db_execute("INSERT OR IGNORE INTO campaign_options (label) VALUES (?)", (cmp,), commit=True)

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        pw = request.form['password']
        user = db_execute("SELECT * FROM users WHERE LOWER(username)=? AND password=? AND active=1",
                          (username, hash_pw(pw)), fetchone=True)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total = db_execute("SELECT COUNT(*) as c FROM audits", fetchone=True)['c']
    my_audits = db_execute("SELECT COUNT(*) as c FROM audits WHERE auditor_id=?",
                           (session['user_id'],), fetchone=True)['c']
    reason_data = db_execute("""SELECT dsat_reason, COUNT(*) as cnt FROM audits
        WHERE dsat_reason IS NOT NULL AND dsat_reason != ''
        GROUP BY dsat_reason ORDER BY cnt DESC LIMIT 10""", fetchall=True)
    acpt_data = db_execute("""SELECT acpt, COUNT(*) as cnt FROM audits
        WHERE acpt IS NOT NULL AND acpt != '' GROUP BY acpt""", fetchall=True)
    issue_data = db_execute("""SELECT issue_type, COUNT(*) as cnt FROM audits
        WHERE issue_type IS NOT NULL AND issue_type != ''
        GROUP BY issue_type ORDER BY cnt DESC""", fetchall=True)
    trend_data = db_execute("""SELECT substr(audit_date,1,7) as month, COUNT(*) as cnt
        FROM audits WHERE audit_date IS NOT NULL
        GROUP BY month ORDER BY month DESC LIMIT 6""", fetchall=True)
    disposed_data = db_execute("SELECT disposed_correctly, COUNT(*) as cnt FROM audits GROUP BY disposed_correctly", fetchall=True)
    auditor_data = db_execute("""SELECT u.name, COUNT(a.id) as cnt FROM audits a
        JOIN users u ON a.auditor_id = u.id GROUP BY u.id, u.name ORDER BY cnt DESC""", fetchall=True)
    recent = db_execute("""SELECT a.*, u.name as auditor_name FROM audits a
        JOIN users u ON a.auditor_id = u.id ORDER BY a.created_at DESC LIMIT 10""", fetchall=True)
    return render_template('dashboard.html', total=total, my_audits=my_audits,
        reason_data=reason_data, acpt_data=acpt_data, issue_data=issue_data,
        trend_data=trend_data, disposed_data=disposed_data,
        auditor_data=auditor_data, recent=recent)

# ─── AUDIT FORM ──────────────────────────────────────────────────────────────

@app.route('/audit/new', methods=['GET', 'POST'])
@login_required
def new_audit():
    if request.method == 'POST':
        f = request.form
        audit_dt = f.get('audit_date') or date.today().isoformat()
        db_execute("""INSERT INTO audits (advisor_name, partner, calling_number, auditor_id,
            call_date, audit_date, call_id, campaign, issue_type, sub_issue_type,
            disposed_correctly, call_summary, areas_of_improvement, acpt,
            reason_for_acpt, dsat_reason, actionable_items, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f.get('advisor_name'), f.get('partner'), f.get('calling_number'), session['user_id'],
             f.get('call_date'), audit_dt, f.get('call_id'), f.get('campaign'),
             f.get('issue_type'), f.get('sub_issue_type'), f.get('disposed_correctly'),
             f.get('call_summary'), f.get('areas_of_improvement'), f.get('acpt'),
             f.get('reason_for_acpt'), f.get('dsat_reason'), f.get('actionable_items'),
             date.today().isoformat()), commit=True)
        flash('Audit submitted successfully!', 'success')
        return redirect(url_for('all_audits'))

    issue_types = db_execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type", fetchall=True)
    dsat_reasons = db_execute("SELECT * FROM dsat_reasons ORDER BY category, reason", fetchall=True)
    acpt_options = db_execute("SELECT * FROM acpt_options ORDER BY label", fetchall=True)
    partner_options = db_execute("SELECT * FROM partner_options ORDER BY label", fetchall=True)
    campaign_options = db_execute("SELECT * FROM campaign_options ORDER BY label", fetchall=True)
    return render_template('audit_form.html', issue_types=issue_types, dsat_reasons=dsat_reasons,
        acpt_options=acpt_options, partner_options=partner_options,
        campaign_options=campaign_options, audit=None, today=date.today().isoformat())

@app.route('/audit/<int:audit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_audit(audit_id):
    audit = db_execute("SELECT * FROM audits WHERE id=?", (audit_id,), fetchone=True)
    if not audit:
        flash('Audit not found.', 'error')
        return redirect(url_for('all_audits'))
    if session['role'] != 'admin' and audit['auditor_id'] != session['user_id']:
        flash('Access denied.', 'error')
        return redirect(url_for('all_audits'))
    if request.method == 'POST':
        f = request.form
        db_execute("""UPDATE audits SET advisor_name=?, partner=?, calling_number=?,
            call_date=?, audit_date=?, call_id=?, campaign=?, issue_type=?, sub_issue_type=?,
            disposed_correctly=?, call_summary=?, areas_of_improvement=?,
            acpt=?, reason_for_acpt=?, dsat_reason=?, actionable_items=? WHERE id=?""",
            (f.get('advisor_name'), f.get('partner'), f.get('calling_number'),
             f.get('call_date'), f.get('audit_date'), f.get('call_id'), f.get('campaign'),
             f.get('issue_type'), f.get('sub_issue_type'), f.get('disposed_correctly'),
             f.get('call_summary'), f.get('areas_of_improvement'), f.get('acpt'),
             f.get('reason_for_acpt'), f.get('dsat_reason'), f.get('actionable_items'), audit_id), commit=True)
        flash('Audit updated.', 'success')
        return redirect(url_for('all_audits'))

    issue_types = db_execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type", fetchall=True)
    dsat_reasons = db_execute("SELECT * FROM dsat_reasons ORDER BY category, reason", fetchall=True)
    acpt_options = db_execute("SELECT * FROM acpt_options ORDER BY label", fetchall=True)
    partner_options = db_execute("SELECT * FROM partner_options ORDER BY label", fetchall=True)
    campaign_options = db_execute("SELECT * FROM campaign_options ORDER BY label", fetchall=True)
    return render_template('audit_form.html', issue_types=issue_types, dsat_reasons=dsat_reasons,
        acpt_options=acpt_options, partner_options=partner_options,
        campaign_options=campaign_options, audit=audit, today=date.today().isoformat())

@app.route('/audit/<int:audit_id>/delete', methods=['POST'])
@admin_required
def delete_audit(audit_id):
    db_execute("DELETE FROM audits WHERE id=?", (audit_id,), commit=True)
    flash('Audit deleted.', 'success')
    return redirect(url_for('all_audits'))

# ─── ALL AUDITS ───────────────────────────────────────────────────────────────

@app.route('/all-audits')
@login_required
def all_audits():
    auditor_f = request.args.get('auditor', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    issue_f = request.args.get('issue_type', '')

    sql = "SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id = u.id WHERE 1=1"
    params = []
    if session['role'] != 'admin':
        sql += " AND a.auditor_id=?"; params.append(session['user_id'])
    if auditor_f and session['role'] == 'admin':
        sql += " AND a.auditor_id=?"; params.append(auditor_f)
    if date_from:
        sql += " AND a.audit_date>=?"; params.append(date_from)
    if date_to:
        sql += " AND a.audit_date<=?"; params.append(date_to)
    if issue_f:
        sql += " AND a.issue_type=?"; params.append(issue_f)
    sql += " ORDER BY a.created_at DESC"

    audits = db_execute(sql, params, fetchall=True)
    auditors = db_execute("SELECT id, name FROM users WHERE active=1 ORDER BY name", fetchall=True)
    issue_types = db_execute("SELECT DISTINCT issue_type FROM dispositions ORDER BY issue_type", fetchall=True)
    return render_template('audits_list.html', audits=audits, title='All Audits',
                           auditors=auditors, issue_types=issue_types,
                           filters={'auditor': auditor_f, 'date_from': date_from,
                                    'date_to': date_to, 'issue_type': issue_f})

# ─── API ─────────────────────────────────────────────────────────────────────

@app.route('/api/sub-dispositions')
@login_required
def api_sub_dispositions():
    issue_type = request.args.get('issue_type', '')
    rows = db_execute("SELECT sub_issue_type FROM dispositions WHERE issue_type=? ORDER BY sub_issue_type",
                      (issue_type,), fetchall=True)
    return jsonify([r['sub_issue_type'] for r in rows])

@app.route('/api/audits-feed')
@login_required
def api_audits_feed():
    if session['role'] == 'admin':
        rows = db_execute("SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id=u.id ORDER BY a.created_at DESC LIMIT 200", fetchall=True)
    else:
        rows = db_execute("SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id=u.id WHERE a.auditor_id=? ORDER BY a.created_at DESC LIMIT 200",
                          (session['user_id'],), fetchall=True)
    return jsonify(rows)

# ─── REPORT EXPORT ────────────────────────────────────────────────────────────

@app.route('/report/export')
@login_required
def export_report():
    if session['role'] == 'admin':
        audits = db_execute("SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id=u.id ORDER BY a.created_at DESC", fetchall=True)
    else:
        audits = db_execute("SELECT a.*, u.name as auditor_name FROM audits a JOIN users u ON a.auditor_id=u.id WHERE a.auditor_id=? ORDER BY a.created_at DESC",
                            (session['user_id'],), fetchall=True)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Advisor Name','Partner','Calling Number','Auditor Name','Call Date',
                     'Audit Date','Call ID','Campaign','Issue Type','Sub Issue Type',
                     'Disposed Correctly','Call Summary','Areas of Improvement',
                     'ACPT','Reason for ACPT','D-Sat Reason','Actionable Items'])
    for a in audits:
        writer.writerow([a.get('advisor_name'), a.get('partner'), a.get('calling_number'),
                         a.get('auditor_name'), a.get('call_date'), a.get('audit_date'),
                         a.get('call_id'), a.get('campaign'), a.get('issue_type'),
                         a.get('sub_issue_type'), a.get('disposed_correctly'),
                         a.get('call_summary'), a.get('areas_of_improvement'), a.get('acpt'),
                         a.get('reason_for_acpt'), a.get('dsat_reason'), a.get('actionable_items')])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv', as_attachment=True,
                     download_name=f'dsat_report_{date.today()}.csv')

# ─── ADMIN: USERS ────────────────────────────────────────────────────────────

@app.route('/admin/users')
@admin_required
def admin_users():
    users = db_execute("SELECT * FROM users ORDER BY role, name", fetchall=True)
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def admin_add_user():
    username = request.form['username'].strip().lower()
    name = request.form['name'].strip()
    pw = request.form['password']
    role = request.form.get('role', 'auditor')
    try:
        db_execute("INSERT INTO users (username, name, password, role) VALUES (?,?,?,?)",
                   (username, name, hash_pw(pw), role), commit=True)
        flash(f'User "{username}" added successfully.', 'success')
    except Exception:
        flash('Username already exists.', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def admin_toggle_user(uid):
    user = db_execute("SELECT * FROM users WHERE id=?", (uid,), fetchone=True)
    if user and user['role'] != 'admin':
        db_execute("UPDATE users SET active=? WHERE id=?",
                   (0 if user['active'] else 1, uid), commit=True)
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(uid):
    db_execute("UPDATE users SET password=? WHERE id=?",
               (hash_pw(request.form['new_password']), uid), commit=True)
    flash('Password reset successfully.', 'success')
    return redirect(url_for('admin_users'))

# ─── ADMIN: DISPOSITIONS ─────────────────────────────────────────────────────

@app.route('/admin/dispositions')
@admin_required
def admin_dispositions():
    rows = db_execute("SELECT * FROM dispositions ORDER BY issue_type, sub_issue_type", fetchall=True)
    return render_template('admin_dispositions.html', dispositions=rows)

@app.route('/admin/dispositions/add', methods=['POST'])
@admin_required
def admin_add_disposition():
    issue = request.form['issue_type'].strip()
    sub = request.form['sub_issue_type'].strip()
    if issue and sub:
        db_execute("INSERT INTO dispositions (issue_type, sub_issue_type) VALUES (?,?)", (issue, sub), commit=True)
        flash('Disposition added.', 'success')
    return redirect(url_for('admin_dispositions'))

@app.route('/admin/dispositions/<int:did>/delete', methods=['POST'])
@admin_required
def admin_delete_disposition(did):
    db_execute("DELETE FROM dispositions WHERE id=?", (did,), commit=True)
    flash('Disposition deleted.', 'success')
    return redirect(url_for('admin_dispositions'))

# ─── ADMIN: DSAT REASONS ─────────────────────────────────────────────────────

@app.route('/admin/dsat-reasons')
@admin_required
def admin_dsat_reasons():
    rows = db_execute("SELECT * FROM dsat_reasons ORDER BY category, reason", fetchall=True)
    return render_template('admin_dsat_reasons.html', reasons=rows)

@app.route('/admin/dsat-reasons/add', methods=['POST'])
@admin_required
def admin_add_dsat_reason():
    db_execute("INSERT INTO dsat_reasons (category, reason, description) VALUES (?,?,?)",
               (request.form['category'].strip(), request.form['reason'].strip(),
                request.form['description'].strip()), commit=True)
    flash('DSAT reason added.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

@app.route('/admin/dsat-reasons/<int:rid>/edit', methods=['POST'])
@admin_required
def admin_edit_dsat_reason(rid):
    db_execute("UPDATE dsat_reasons SET category=?, reason=?, description=? WHERE id=?",
               (request.form['category'].strip(), request.form['reason'].strip(),
                request.form['description'].strip(), rid), commit=True)
    flash('DSAT reason updated.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

@app.route('/admin/dsat-reasons/<int:rid>/delete', methods=['POST'])
@admin_required
def admin_delete_dsat_reason(rid):
    db_execute("DELETE FROM dsat_reasons WHERE id=?", (rid,), commit=True)
    flash('DSAT reason deleted.', 'success')
    return redirect(url_for('admin_dsat_reasons'))

# ─── ADMIN: ACPT / PARTNERS / CAMPAIGNS ──────────────────────────────────────

@app.route('/admin/acpt')
@admin_required
def admin_acpt():
    return render_template('admin_acpt.html', options=db_execute("SELECT * FROM acpt_options ORDER BY label", fetchall=True))

@app.route('/admin/acpt/add', methods=['POST'])
@admin_required
def admin_add_acpt():
    try:
        db_execute("INSERT INTO acpt_options (label) VALUES (?)", (request.form['label'].strip(),), commit=True)
        flash('ACPT option added.', 'success')
    except Exception:
        flash('Already exists.', 'error')
    return redirect(url_for('admin_acpt'))

@app.route('/admin/acpt/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_acpt(oid):
    db_execute("DELETE FROM acpt_options WHERE id=?", (oid,), commit=True)
    flash('Deleted.', 'success')
    return redirect(url_for('admin_acpt'))

@app.route('/admin/partners')
@admin_required
def admin_partners():
    return render_template('admin_simple_list.html', title='Manage Partners',
        subtitle='Partner dropdown options', items=db_execute("SELECT * FROM partner_options ORDER BY label", fetchall=True),
        add_url=url_for('admin_add_partner'), delete_url_name='admin_delete_partner', placeholder='e.g. Cyfuture')

@app.route('/admin/partners/add', methods=['POST'])
@admin_required
def admin_add_partner():
    try:
        db_execute("INSERT INTO partner_options (label) VALUES (?)", (request.form['label'].strip(),), commit=True)
        flash('Partner added.', 'success')
    except Exception:
        flash('Already exists.', 'error')
    return redirect(url_for('admin_partners'))

@app.route('/admin/partners/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_partner(oid):
    db_execute("DELETE FROM partner_options WHERE id=?", (oid,), commit=True)
    flash('Deleted.', 'success')
    return redirect(url_for('admin_partners'))

@app.route('/admin/campaigns')
@admin_required
def admin_campaigns():
    return render_template('admin_simple_list.html', title='Manage Campaigns',
        subtitle='Campaign dropdown options', items=db_execute("SELECT * FROM campaign_options ORDER BY label", fetchall=True),
        add_url=url_for('admin_add_campaign'), delete_url_name='admin_delete_campaign', placeholder='e.g. Sales Queue')

@app.route('/admin/campaigns/add', methods=['POST'])
@admin_required
def admin_add_campaign():
    try:
        db_execute("INSERT INTO campaign_options (label) VALUES (?)", (request.form['label'].strip(),), commit=True)
        flash('Campaign added.', 'success')
    except Exception:
        flash('Already exists.', 'error')
    return redirect(url_for('admin_campaigns'))

@app.route('/admin/campaigns/<int:oid>/delete', methods=['POST'])
@admin_required
def admin_delete_campaign(oid):
    db_execute("DELETE FROM campaign_options WHERE id=?", (oid,), commit=True)
    flash('Deleted.', 'success')
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
        user = db_execute("SELECT * FROM users WHERE id=? AND password=?",
                          (session['user_id'], hash_pw(current)), fetchone=True)
        if not user:
            flash('Current password incorrect.', 'error')
            return redirect(url_for('change_password'))
        db_execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), session['user_id']), commit=True)
        flash('Password changed.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('change_password.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
