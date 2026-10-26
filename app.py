import os
from flask import (Flask, render_template, request,
                   redirect, url_for, flash,
                   session, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db
from ai_engine import categorize, detect_priority, check_duplicate, chatbot_response

app = Flask(__name__)
app.secret_key = 'civic_secret_key_2024'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Helper ──────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── Home ─────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

# ── Register ─────────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        dob        = request.form.get('dob', '').strip()
        phone      = request.form.get('phone', '').strip()
        username   = request.form['username'].strip()
        email      = request.form['email'].strip()
        password   = request.form['password']

        if not username or not email or not password or not first_name:
            flash('Please fill all required fields.', 'danger')
            return redirect(url_for('register'))

        conn = get_db()
        existing = conn.execute(
            'SELECT id FROM users WHERE email=? OR username=?',
            (email, username)
        ).fetchone()
        if existing:
            flash('Username or email already exists.', 'danger')
            conn.close()
            return redirect(url_for('register'))

        conn.execute('''
            INSERT INTO users
            (first_name, last_name, dob, phone, username, email, password)
            VALUES (?,?,?,?,?,?,?)
        ''', (first_name, last_name, dob, phone,
              username, email, generate_password_hash(password)))
        conn.commit()
        conn.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')
# ── Login ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username=?', (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            flash(f"Welcome {user['username']}!", 'success')
            if user['is_admin']:
                return redirect(url_for('admin'))
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

# ── Logout ────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# ── Dashboard ─────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    complaints = conn.execute(
        'SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('dashboard.html', complaints=complaints)

# ── Submit Complaint ──────────────────────────────────────────────────
@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        text     = request.form['complaint_text'].strip()
        location = request.form.get('location', '')
        if not text:
            flash('Complaint text is required.', 'danger')
            return redirect(url_for('submit'))

        # AI processing
        category    = categorize(text)
        priority    = detect_priority(text)
        is_dup, dup_id = check_duplicate(text)

        # Image upload
        image_path = ''
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename   = secure_filename(file.filename)
                image_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], filename
                )
                file.save(image_path)

        # Handle camera capture (base64)
        if not image_path:
            captured = request.form.get('captured_image', '')
            if captured and captured.startswith('data:image'):
                import base64, re
                match = re.search(r'data:image/\w+;base64,(.+)', captured)
                if match:
                    img_data    = base64.b64decode(match.group(1))
                    unique_name = f"{int(time.time())}_capture.jpg"
                    save_path   = os.path.join(
                        app.config['UPLOAD_FOLDER'], unique_name
                    )
                    with open(save_path, 'wb') as f:
                        f.write(img_data)
                    image_path = save_path


        conn = get_db()
        conn.execute('''
            INSERT INTO complaints
            (user_id,complaint_text,category,priority,
             location,image_path,is_duplicate)
            VALUES (?,?,?,?,?,?,?)
        ''', (session['user_id'], text, category, priority,
              location, image_path, int(is_dup)))
        conn.commit()
        conn.close()

        msg = f'Complaint submitted! Category: {category} | Priority: {priority}'
        if is_dup:
            msg += f' | Note: Similar complaint #{dup_id} already exists.'
        flash(msg, 'success')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

# ── Admin Panel ───────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    complaints = conn.execute('''
        SELECT c.*, u.username FROM complaints c
        JOIN users u ON c.user_id = u.id
        ORDER BY
            CASE c.priority
                WHEN 'High'   THEN 1
                WHEN 'Medium' THEN 2
                ELSE 3
            END,
            c.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin.html', complaints=complaints)

# ── Update Status ─────────────────────────────────────────────────────
@app.route('/update-status/<int:complaint_id>', methods=['POST'])
@admin_required
def update_status(complaint_id):
    new_status = request.form['status']
    conn       = get_db()
    old        = conn.execute(
        'SELECT status FROM complaints WHERE id=?', (complaint_id,)
    ).fetchone()
    if old:
        conn.execute(
            'UPDATE complaints SET status=? WHERE id=?',
            (new_status, complaint_id)
        )
        conn.execute('''
            INSERT INTO status_history
            (complaint_id, old_status, new_status, changed_by)
            VALUES (?,?,?,?)
        ''', (complaint_id, old['status'],
              new_status, session['user_id']))
        conn.commit()
        flash('Status updated successfully!', 'success')
    conn.close()
    return redirect(url_for('admin'))

# ── Chatbot API ───────────────────────────────────────────────────────
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data    = request.get_json()
    msg     = data.get('message', '')
    reply   = chatbot_response(msg)
    return jsonify({'reply': reply})

# ── Stats API (for charts) ────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def stats():
    conn = get_db()
    uid  = session['user_id']
    rows = conn.execute(
        'SELECT status, COUNT(*) as count FROM complaints '
        'WHERE user_id=? GROUP BY status', (uid,)
    ).fetchall()
    cats = conn.execute(
        'SELECT category, COUNT(*) as count FROM complaints '
        'WHERE user_id=? GROUP BY category', (uid,)
    ).fetchall()
    conn.close()
    return jsonify({
        'status'    : {r['status']: r['count'] for r in rows},
        'categories': {r['category']: r['count'] for r in cats},
    })

# ── Admin Login ───────────────────────────────────────────────────────
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username=? AND is_admin=1',
            (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['is_admin'] = True
            flash(f"Welcome Admin {user['username']}!", 'success')
            return redirect(url_for('admin'))
        flash('Invalid admin credentials.', 'danger')
    return render_template('admin_login.html')

# ── Map Data API ──────────────────────────────────────────────────────
@app.route('/api/map-data')
@login_required
def map_data():
    conn = get_db()
    if session.get('is_admin'):
        rows = conn.execute(
            'SELECT c.id, c.complaint_text, c.category, '
            'c.priority, c.status, c.location, u.username '
            'FROM complaints c JOIN users u ON c.user_id = u.id '
            'WHERE c.location != ""'
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT id, complaint_text, category, '
            'priority, status, location '
            'FROM complaints '
            'WHERE user_id=? AND location != ""',
            (session['user_id'],)
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        try:
            lat, lng = r['location'].split(',')
            result.append({
                'id'      : r['id'],
                'text'    : r['complaint_text'][:60],
                'category': r['category'],
                'priority': r['priority'],
                'status'  : r['status'],
                'lat'     : float(lat),
                'lng'     : float(lng)
            })
        except:
            pass
    return jsonify(result)

# ── Username Availability Check ───────────────────────────────────────
@app.route('/check-username')
def check_username():
    username = request.args.get('username', '').strip()
    if len(username) < 3:
        return jsonify({'available': None, 'message': 'Min 3 characters'})
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM users WHERE username=?', (username,)
    ).fetchone()
    conn.close()
    if existing:
        return jsonify({'available': False,
                        'message': 'Username already taken ❌'})
    return jsonify({'available': True,
                    'message': 'Username available ✅'})
# ── Complaint Detail ──────────────────────────────────────────────────
@app.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    conn = get_db()
    if session.get('is_admin'):
        complaint = conn.execute(
            '''SELECT c.*, u.username, u.email, u.first_name, u.last_name
               FROM complaints c
               JOIN users u ON c.user_id = u.id
               WHERE c.id = ?''',
            (complaint_id,)
        ).fetchone()
    else:
        complaint = conn.execute(
            '''SELECT c.*, u.username, u.email, u.first_name, u.last_name
               FROM complaints c
               JOIN users u ON c.user_id = u.id
               WHERE c.id = ? AND c.user_id = ?''',
            (complaint_id, session['user_id'])
        ).fetchone()
    conn.close()
    if not complaint:
        flash('Complaint not found or access denied.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('complaint_detail.html', c=complaint)
# ── Profile ───────────────────────────────────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        dob        = request.form.get('dob', '').strip()
        phone      = request.form.get('phone', '').strip()
        email      = request.form.get('email', '').strip()
        new_pass   = request.form.get('new_password', '').strip()

        # Check email not taken by another user
        existing = conn.execute(
            'SELECT id FROM users WHERE email=? AND id!=?',
            (email, session['user_id'])
        ).fetchone()
        if existing:
            flash('Email already in use by another account.', 'danger')
            return redirect(url_for('profile'))

        if new_pass:
            if len(new_pass) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return redirect(url_for('profile'))
            conn.execute('''
                UPDATE users SET first_name=?, last_name=?, dob=?,
                phone=?, email=?, password=? WHERE id=?
            ''', (first_name, last_name, dob, phone, email,
                  generate_password_hash(new_pass), session['user_id']))
        else:
            conn.execute('''
                UPDATE users SET first_name=?, last_name=?,
                dob=?, phone=?, email=? WHERE id=?
            ''', (first_name, last_name, dob, phone,
                  email, session['user_id']))

        conn.commit()
        session['username'] = conn.execute(
            'SELECT username FROM users WHERE id=?',
            (session['user_id'],)
        ).fetchone()['username']
        flash('Profile updated successfully! ✅', 'success')
        conn.close()
        return redirect(url_for('profile'))

    user = conn.execute(
        'SELECT * FROM users WHERE id=?', (session['user_id'],)
    ).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

# ── Run ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)