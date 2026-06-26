import sqlite3, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = 'C:/Users/Preeti Naval/OneDrive/Desktop/Dsat Tool/dsat_app/dsat.db'
conn = sqlite3.connect(DB)

try:
    conn.execute('ALTER TABLE users ADD COLUMN username TEXT')
    conn.commit()
except:
    pass

conn.execute("UPDATE users SET username = LOWER(REPLACE(name,' ','')) WHERE username IS NULL OR username = ''")
conn.commit()

try:
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_username ON users(username)')
    conn.commit()
except:
    pass

pw = hashlib.sha256('Wiom@123'.encode()).hexdigest()

auditors = [
    ('sanjana','Sanjana'),('rehmat','Rehmat'),('rohan','Rohan'),
    ('avakash','Avakash'),('deepakshi','Deepakshi'),('rashi','Rashi'),
    ('sajal','Sajal'),('ankita','Ankita'),('anita','Anita'),
    ('nisha','Nisha'),('vikas','Vikas'),('lalit','Lalit'),
]

for username, name in auditors:
    existing = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
    if existing:
        conn.execute('UPDATE users SET name=?, password=?, role=?, active=1 WHERE username=?',
                     (name, pw, 'auditor', username))
    else:
        conn.execute('INSERT INTO users (username, name, email, password, role, active) VALUES (?,?,?,?,?,?)',
                     (username, name, username+'@wiom.in', pw, 'auditor', 1))

conn.commit()

print('All users:')
print(f'{"Username":<15} {"Name":<15} {"Role":<10} {"Status"}')
print('-' * 50)
rows = conn.execute('SELECT username, name, role, active FROM users ORDER BY role DESC, name').fetchall()
for r in rows:
    status = 'Active' if r[3] else 'Inactive'
    print(f'{r[0]:<15} {r[1]:<15} {r[2]:<10} {status}')

conn.close()
