import os
import re

TEMPLATE_DIR = r"d:\Projects\helpdesk_eng\app\templates"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find <form ...> tags and add the CSRF hidden input right after them
    if 'csrf_token' not in content and '<form' in content:
        def add_csrf(match):
            return match.group(0) + '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>'
            
        new_content = re.sub(r'<form[^>]*>', add_csrf, content)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Added CSRF to {filepath}")

for root, _, files in os.walk(TEMPLATE_DIR):
    for file in files:
        if file.endswith('.html'):
            process_file(os.path.join(root, file))

print("Done injecting CSRF.")
