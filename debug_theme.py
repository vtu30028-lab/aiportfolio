"""
Debug script: Renders the theme editor page and checks all key elements.
Run: python debug_theme.py
"""
import sys, os
sys.path.insert(0, 'C:/portfolio')

# Use test conftest fixtures approach
os.environ['FLASK_ENV'] = 'testing'
from app import create_app
from app.extensions import db as _db

app = create_app('testing')

with app.app_context():
    _db.create_all()

    # Use same fixture data as tests
    from app.models import User, Portfolio
    import json

    u = User(name='Alex Mercer', email='alex@example.com')
    u.set_password('SecurePass123!')
    _db.session.add(u)
    _db.session.flush()

    p = Portfolio(
        user_id=u.id,
        title='Senior Engineer Showcase',
        full_name='Alex Mercer',
        headline='Principal Distributed Systems Architect',
        about='Experienced engineer with 12+ years building scalable systems.',
        email='alex.mercer@example.com',
        location='San Francisco, CA',
        theme='modern-dark',
        accent_color='#6366f1',
        font_family='plus-jakarta-sans',
        layout_style='standard',
        skills='Python,Go,Rust,Kubernetes,Kafka',
        section_visibility=json.dumps({
            'about': True, 'skills': True, 'projects': True,
            'experience': True, 'education': True, 'certifications': True, 'contact': True
        })
    )
    _db.session.add(p)
    _db.session.commit()
    pid = p.id
    uid = u.id

client = app.test_client()
with client.session_transaction() as sess:
    sess['_user_id'] = str(uid)
    sess['_fresh'] = True

resp = client.get('/portfolios/' + str(pid) + '/theme')
html = resp.data.decode('utf-8')

print("=" * 60)
print("HTTP Status:", resp.status_code)
print("=" * 60)

checks = {
    'livePreviewPanel': 'Preview panel div exists',
    'theme-choice-card': 'Theme cards exist',
    'data-theme="modern-dark"': 'Dark Developer card',
    'data-theme="terminal-hacker"': 'Terminal Hacker card',
    'data-theme="student-starter"': 'Student Starter card',
    'fontSelect': 'Font selector',
    'layoutSelect': 'Layout selector',
    'section-toggle-input': 'Section toggles',
    'theme_editor.js': 'JS file loaded',
    'INITIAL_THEME_CONFIG': 'Config injected',
    'portfolio_themes.css': 'CSS file loaded',
    'preview-root': 'Preview root class',
    'preview-hero': 'Hero section',
    'data-section="about"': 'About section toggle target',
    'data-section="skills"': 'Skills section toggle target',
    'btnSaveTheme': 'Save button',
    'btnResetDefaults': 'Reset button',
    'activeThemeBadge': 'Theme badge',
    'activeColorHex': 'Color hex display',
    'color-swatch': 'Color swatches',
}

all_ok = True
for key, desc in checks.items():
    found = key in html
    if not found:
        all_ok = False
    print(('OK     ' if found else 'MISSING') + ' | ' + desc + ' (' + key + ')')

print()
if all_ok:
    print("ALL CHECKS PASSED!")
else:
    print("SOME ELEMENTS MISSING - see above")

print()
print("--- CSS links in page ---")
import re
links = re.findall(r'<link[^>]+>', html)
for l in links:
    if 'css' in l.lower():
        print(l)

print()
print("--- Script tags in page ---")
scripts = re.findall(r'<script[^>]*>', html)
for s in scripts:
    print(s)
