import shutil

shutil.copy('fix_database.py', 'fix_database_backup.py')
with open('fix_database.py', 'r') as f:
    content = f.read()
content = content.replace("with open('high_end_ws_lounge/database.py', 'w', encoding='utf-8') as f:", "with open('database.py', 'w', encoding='utf-8') as f:")
with open('fix_database.py', 'w') as f:
    f.write(content)
print("Fixed path in fix_database.py")
