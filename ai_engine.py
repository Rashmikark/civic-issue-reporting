from fuzzywuzzy import fuzz
from database import get_db

# ── 1. Auto Categorization ──────────────────────────────────────────
CATEGORIES = {
    'Water'      : ['water','pipe','leak','flood','drain','sewage',
                    'drainage','overflow','tap','bore'],
    'Road'       : ['road','pothole','street','footpath','bridge',
                    'traffic','signal','divider','highway'],
    'Electricity': ['electricity','power','light','electric','wire',
                    'transformer','streetlight','voltage','outage'],
    'Sanitation' : ['garbage','waste','trash','clean','toilet',
                    'sanitation','smell','dirty','dump','litter'],
    'Building'   : ['building','construction','collapse','crack',
                    'wall','roof','structure','dangerous'],
    'Noise'      : ['noise','sound','loud','music','horn','party'],
}

def categorize(text):
    text = text.lower()
    scores = {}
    for cat, keywords in CATEGORIES.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'General'

# ── 2. Priority Detection ───────────────────────────────────────────
HIGH_KEYWORDS   = ['urgent','emergency','dangerous','critical',
                   'immediate','serious','severe','life','death',
                   'accident','burst','collapse','fire']
MEDIUM_KEYWORDS = ['important','issue','problem','broken',
                   'not working','repair','fix','damaged']

def detect_priority(text):
    text = text.lower()
    if any(kw in text for kw in HIGH_KEYWORDS):
        return 'High'
    if any(kw in text for kw in MEDIUM_KEYWORDS):
        return 'Medium'
    return 'Low'

# ── 3. Duplicate Detection ──────────────────────────────────────────
def check_duplicate(new_text, threshold=75):
    conn = get_db()
    complaints = conn.execute(
        'SELECT id, complaint_text FROM complaints'
    ).fetchall()
    conn.close()
    for row in complaints:
        score = fuzz.token_sort_ratio(
            new_text.lower(), row['complaint_text'].lower()
        )
        if score >= threshold:
            return True, row['id']
    return False, None

# ── 4. Chatbot ──────────────────────────────────────────────────────
RESPONSES = {
    'how to report'    : 'Go to the Report page, enter your complaint text, upload an image if needed, and click Submit.',
    'check status'     : 'Login and go to your Dashboard to see all your complaints and their current status.',
    'categories'       : 'We handle Water, Road, Electricity, Sanitation, Building, and Noise complaints.',
    'contact'          : 'You can reach the admin through the Admin panel or email admin@civic.com.',
    'duplicate'        : 'If your complaint is similar to an existing one, the system will flag it automatically.',
    'priority'         : 'Priority is assigned automatically. Urgent issues are marked High priority.',
    'hello'            : 'Hello! I am the Civic Assistant. How can I help you today?',
    'hi'               : 'Hi there! How can I assist you?',
    'help'             : 'I can help you with: reporting issues, checking status, complaint categories, and more.',
}

def chatbot_response(user_msg):
    msg = user_msg.lower().strip()
    for key, reply in RESPONSES.items():
        if key in msg:
            return reply
    return "I am not sure about that. Please contact the admin or try rephrasing your question."