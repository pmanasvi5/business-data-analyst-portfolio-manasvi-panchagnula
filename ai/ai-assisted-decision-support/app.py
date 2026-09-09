"""Small, local software vendor decision support demo."""
import json
import os
import secrets
import sqlite3
from pathlib import Path

from anthropic import Anthropic, APIError
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
app = Flask(__name__)
# A restart clears old sessions unless SECRET_KEY is configured in .env.
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['DATABASE'] = BASE_DIR / 'vendors.db'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CRITERIA = {
    'price': ('Price', 'price_score'),
    'ease': ('Ease of Use', 'ease_of_use_score'),
    'integration': ('Integrations', 'integration_score'),
    'analytics': ('Analytics', 'analytics_score'),
    'support': ('Customer Support', 'support_score'),
}
VENDORS = [
    (1, 'BudgetBridge', 49, 10, 8, 5, 4, 6),
    (2, 'TeamFlow', 99, 8, 10, 7, 6, 8),
    (3, 'ConnectSuite', 149, 6, 7, 10, 8, 7),
    (4, 'InsightWorks', 199, 4, 6, 8, 10, 8),
    (5, 'CareCloud', 179, 5, 8, 7, 7, 10),
]


def get_db():
    connection = sqlite3.connect(app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                monthly_cost REAL NOT NULL CHECK (monthly_cost >= 0),
                price_score INTEGER NOT NULL CHECK (price_score BETWEEN 1 AND 10),
                ease_of_use_score INTEGER NOT NULL CHECK (ease_of_use_score BETWEEN 1 AND 10),
                integration_score INTEGER NOT NULL CHECK (integration_score BETWEEN 1 AND 10),
                analytics_score INTEGER NOT NULL CHECK (analytics_score BETWEEN 1 AND 10),
                support_score INTEGER NOT NULL CHECK (support_score BETWEEN 1 AND 10)
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                vendor_name TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('approved', 'needs_review')),
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        if db.execute('SELECT COUNT(*) FROM vendors').fetchone()[0] == 0:
            db.executemany('INSERT INTO vendors VALUES (?, ?, ?, ?, ?, ?, ?, ?)', VENDORS)
    db.close()


def parse_weights(form):
    weights = {}
    for key in CRITERIA:
        value = form.get(key, '')
        if value not in ('1', '2', '3', '4', '5'):
            raise ValueError('Please select a whole-number weight from 1 to 5 for every criterion.')
        weights[key] = int(value)
    return weights


def rank_vendors(vendors, weights):
    """Weighted mean on a 1–10 scale; ties use lower cost then vendor ID."""
    total_weight = sum(weights.values())
    ranked = []
    for vendor in vendors:
        item = dict(vendor)
        item['weighted_score'] = sum(
            item[column] * weights[key] for key, (_, column) in CRITERIA.items()
        ) / total_weight
        ranked.append(item)
    return sorted(ranked, key=lambda v: (-v['weighted_score'], v['monthly_cost'], v['id']))


def current_ranking(weights):
    with get_db() as db:
        vendors = db.execute('SELECT * FROM vendors').fetchall()
    db.close()
    return rank_vendors(vendors, weights)


def explain_ranking(weights, ranked):
    if not os.getenv('ANTHROPIC_API_KEY', '').strip():
        return 'AI explanation unavailable: no ANTHROPIC_API_KEY is configured.'
    payload = {'user_weights': weights, 'top_3_in_fixed_rank_order': ranked[:3]}
    try:
        with Anthropic(timeout=20.0, max_retries=0) as client:
            message = client.messages.create(
                model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-5'),
                max_tokens=450,
                system=(
                    'Explain a fixed software vendor ranking in at most 160 words of plain text. '
                    'Do not choose a vendor or change the supplied ranking. Use only the supplied '
                    'fictional data; do not invent capabilities. Cover why #1 scored highest, one '
                    'strength, one trade-off, and why #2 might still be considered. The score is '
                    'sum(criterion score * weight) / sum(weights); price uses price_score, not cost. '
                    'Ties favor lower monthly cost, then lower ID. This is a draft for human review.'
                ),
                messages=[{'role': 'user', 'content': json.dumps(payload)}],
            )
        explanation = '\n'.join(block.text for block in message.content if block.type == 'text')
        if message.stop_reason == 'max_tokens' or len(explanation) > 2000 or not explanation.strip():
            return 'AI explanation unavailable: Claude returned an incomplete explanation. Please try again.'
        return explanation
    except APIError:
        app.logger.warning('Claude request failed; deterministic ranking remains available.')
        return 'AI explanation unavailable: the Claude request failed. Check your API key, model, and connection.'


@app.route('/', methods=['GET', 'POST'])
def index():
    session.setdefault('csrf_token', secrets.token_hex(24))
    if request.method == 'POST':
        if not secrets.compare_digest(request.form.get('csrf_token', ''), session['csrf_token']):
            return 'Invalid form token. Reload the page and try again.', 400
        try:
            weights = parse_weights(request.form)
        except ValueError as error:
            return render_template('index.html', criteria=CRITERIA,
                                   weights={key: 3 for key in CRITERIA}, ranked=[], error=str(error)), 400
        ranked = current_ranking(weights)
        session['weights'] = weights
        session['explanation'] = explain_ranking(weights, ranked)
        session['pending_vendor_id'] = ranked[0]['id']
        return redirect(url_for('index'))
    weights = session.get('weights', {key: 3 for key in CRITERIA})
    ranked = current_ranking(weights) if 'weights' in session else []
    return render_template('index.html', criteria=CRITERIA, weights=weights,
                           ranked=ranked, explanation=session.get('explanation'))


@app.post('/feedback')
def feedback():
    if not secrets.compare_digest(request.form.get('csrf_token', ''), session.get('csrf_token', 'missing')):
        return 'Invalid form token. Reload the page and try again.', 400
    decision = request.form.get('decision')
    if decision not in ('approved', 'needs_review'):
        return 'Invalid feedback decision.', 400
    if 'weights' not in session or 'pending_vendor_id' not in session:
        flash('Generate a new recommendation before recording feedback.')
        return redirect(url_for('index'))
    top = current_ranking(session['weights'])[0]
    if top['id'] != session['pending_vendor_id']:
        flash('Vendor data changed. Generate a new recommendation before reviewing.')
        return redirect(url_for('index'))
    with get_db() as db:
        db.execute('INSERT INTO feedback (vendor_name, decision) VALUES (?, ?)', (top['name'], decision))
    db.close()
    session.pop('pending_vendor_id')
    flash(f"Feedback recorded for {top['name']}: {'Approved' if decision == 'approved' else 'Needs review'}.")
    return redirect(url_for('index'))


init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
