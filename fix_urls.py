import os
import re

TEMPLATE_DIR = r"d:\Projects\helpdesk_eng\app\templates"

MAPPINGS = {
    r"url_for\('login'\)": r"url_for('auth.login')",
    r"url_for\('register'\)": r"url_for('auth.register')",
    r"url_for\('logout'\)": r"url_for('auth.logout')",
    r"url_for\('dashboard'\)": r"url_for('main.dashboard')",
    r"url_for\('tickets'\)": r"url_for('main.tickets')",
    r"url_for\('ticket_new'\)": r"url_for('main.ticket_new')",
    r"url_for\('ticket_detail'": r"url_for('main.ticket_detail'",
    r"url_for\('admin_defects'\)": r"url_for('admin.defects')",
    r"url_for\('admin_defect_edit'": r"url_for('admin.defect_edit'",
    r"url_for\('admin_defect_toggle'": r"url_for('admin.defect_toggle'",
    r"url_for\('admin_solutions'\)": r"url_for('admin.solutions')",
    r"url_for\('admin_solution_edit'": r"url_for('admin.solution_edit'",
    r"url_for\('admin_solution_toggle'": r"url_for('admin.solution_toggle'",
    r"url_for\('admin_users'\)": r"url_for('admin.users')",
    r"url_for\('admin_user_new'\)": r"url_for('admin.user_new')",
    r"url_for\('admin_user_edit'": r"url_for('admin.user_edit'",
    r"url_for\('admin_user_reset_password'": r"url_for('admin.user_reset_password'"
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False
    for old, new in MAPPINGS.items():
        if re.search(old, content):
            content = re.sub(old, new, content)
            changed = True

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(TEMPLATE_DIR):
    for file in files:
        if file.endswith('.html'):
            process_file(os.path.join(root, file))

print("Done replacing url_for.")
