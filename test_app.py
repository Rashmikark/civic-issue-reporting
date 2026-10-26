import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import init_db, get_db
from ai_engine import categorize, detect_priority, check_duplicate, chatbot_response


class TestSetup(unittest.TestCase):
    """Setup and teardown for all tests"""

    def setUp(self):
        app.config['TESTING']       = True
        app.config['SECRET_KEY']    = 'test_secret'
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            init_db()
            self._create_test_user()

    def _create_test_user(self):
        from werkzeug.security import generate_password_hash
        conn = get_db()
        conn.execute('DELETE FROM complaints')
        conn.execute("DELETE FROM users WHERE username='testuser'")
        conn.execute('''
            INSERT OR IGNORE INTO users
            (username, email, password, is_admin)
            VALUES (?,?,?,0)
        ''', ('testuser', 'test@test.com',
              generate_password_hash('test123')))
        conn.commit()
        conn.close()

    def _login(self, username='testuser', password='test123'):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def _login_admin(self):
        return self.client.post('/admin-login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)


# ══════════════════════════════════════════════════
# 1. AI ENGINE TESTS
# ══════════════════════════════════════════════════
class TestAIEngine(TestSetup):

    # --- Categorization ---
    def test_cat_water(self):
        self.assertEqual(categorize('water pipe is leaking badly'), 'Water')

    def test_cat_road(self):
        self.assertEqual(categorize('large pothole on the road'), 'Road')

    def test_cat_electricity(self):
        self.assertEqual(categorize('electricity outage since morning'), 'Electricity')

    def test_cat_sanitation(self):
        self.assertEqual(categorize('garbage not collected for days'), 'Sanitation')

    def test_cat_building(self):
        self.assertEqual(categorize('building wall has collapsed'), 'Building')

    def test_cat_noise(self):
        self.assertEqual(categorize('loud noise from construction'), 'Noise')

    def test_cat_general(self):
        self.assertEqual(categorize('something happened today'), 'General')

    # --- Priority Detection ---
    def test_priority_high(self):
        self.assertEqual(detect_priority('urgent emergency flood danger'), 'High')

    def test_priority_medium(self):
        self.assertEqual(detect_priority('road is broken and damaged'), 'Medium')

    def test_priority_low(self):
        self.assertEqual(detect_priority('street light is dim today'), 'Low')

    def test_priority_critical(self):
        self.assertEqual(detect_priority('critical collapse danger'), 'High')

    # --- Chatbot ---
    def test_chatbot_hello(self):
        reply = chatbot_response('hello')
        self.assertIn('Hello', reply)

    def test_chatbot_help(self):
        reply = chatbot_response('help')
        self.assertIn('help', reply.lower())

    def test_chatbot_status(self):
        reply = chatbot_response('check status')
        self.assertIn('Dashboard', reply)

    def test_chatbot_unknown(self):
        reply = chatbot_response('xyzabcunknown')
        self.assertIn('not sure', reply.lower())


# ══════════════════════════════════════════════════
# 2. AUTHENTICATION TESTS
# ══════════════════════════════════════════════════
class TestAuth(TestSetup):

    def test_home_page_loads(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_login_page_loads(self):
        r = self.client.get('/login')
        self.assertEqual(r.status_code, 200)

    def test_register_page_loads(self):
        r = self.client.get('/register')
        self.assertEqual(r.status_code, 200)

    def test_valid_login(self):
        r = self._login()
        self.assertEqual(r.status_code, 200)

    def test_invalid_login(self):
        r = self.client.post('/login', data={
            'username': 'wronguser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        self.assertIn(b'Invalid', r.data)

    def test_register_new_user(self):
        r = self.client.post('/register', data={
            'username': 'newuser99',
            'email'   : 'newuser99@test.com',
            'password': 'pass123'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_logout(self):
        self._login()
        r = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_admin_login_valid(self):
        r = self._login_admin()
        self.assertEqual(r.status_code, 200)

    def test_admin_login_invalid(self):
        r = self.client.post('/admin-login', data={
            'username': 'admin',
            'password': 'wrongpass'
        }, follow_redirects=True)
        self.assertIn(b'Invalid', r.data)


# ══════════════════════════════════════════════════
# 3. COMPLAINT TESTS
# ══════════════════════════════════════════════════
class TestComplaints(TestSetup):

    def test_submit_page_requires_login(self):
        r = self.client.get('/submit', follow_redirects=True)
        self.assertIn(b'login', r.data.lower())

    def test_submit_complaint(self):
        self._login()
        r = self.client.post('/submit', data={
            'complaint_text': 'Water pipe is leaking urgently',
            'location'      : '13.0827,80.2707'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_complaint_ai_category_in_response(self):
        self._login()
        r = self.client.post('/submit', data={
            'complaint_text': 'Road has a dangerous pothole',
            'location'      : ''
        }, follow_redirects=True)
        self.assertIn(b'Road', r.data)

    def test_complaint_ai_priority_in_response(self):
        self._login()
        r = self.client.post('/submit', data={
            'complaint_text': 'Urgent emergency water burst',
            'location'      : ''
        }, follow_redirects=True)
        self.assertIn(b'High', r.data)

    def test_dashboard_loads(self):
        self._login()
        r = self.client.get('/dashboard')
        self.assertEqual(r.status_code, 200)

    def test_empty_complaint_rejected(self):
        self._login()
        r = self.client.post('/submit', data={
            'complaint_text': '',
            'location'      : ''
        }, follow_redirects=True)
        self.assertIn(b'required', r.data.lower())


# ══════════════════════════════════════════════════
# 4. ADMIN TESTS
# ══════════════════════════════════════════════════
class TestAdmin(TestSetup):

    def test_admin_panel_blocked_for_users(self):
        self._login()
        r = self.client.get('/admin', follow_redirects=True)
        self.assertIn(b'Admin access only', r.data)

    def test_admin_panel_accessible_for_admin(self):
        self._login_admin()
        r = self.client.get('/admin')
        self.assertEqual(r.status_code, 200)

    def test_status_update_by_admin(self):
        # Submit a complaint first as user
        self._login()
        self.client.post('/submit', data={
            'complaint_text': 'Test complaint for status update',
            'location'      : ''
        })
        self.client.get('/logout')

        # Login as admin and update status
        self._login_admin()
        conn = get_db()
        c = conn.execute(
            'SELECT id FROM complaints ORDER BY id DESC LIMIT 1'
        ).fetchone()
        conn.close()

        if c:
            r = self.client.post(
                f'/update-status/{c["id"]}',
                data={'status': 'Resolved'},
                follow_redirects=True
            )
            self.assertEqual(r.status_code, 200)


# ══════════════════════════════════════════════════
# 5. API TESTS
# ══════════════════════════════════════════════════
class TestAPIs(TestSetup):

    def test_chatbot_api(self):
        r = self.client.post('/chatbot',
            data        = json.dumps({'message': 'hello'}),
            content_type= 'application/json'
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('reply', data)

    def test_stats_api_requires_login(self):
        r = self.client.get('/api/stats', follow_redirects=True)
        self.assertIn(b'login', r.data.lower())

    def test_stats_api_with_login(self):
        self._login()
        r = self.client.get('/api/stats')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIn('status', data)
        self.assertIn('categories', data)

    def test_map_data_api_with_login(self):
        self._login()
        r = self.client.get('/api/map-data')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
