import subprocess
result = subprocess.run(['node', 'static/app.js'], capture_output=True, text=True, cwd='D:\\SBC_Tool', timeout=10)
print('Return code:', result.returncode)
print('STDOUT:', result.stdout[:500] if result.stdout else '')
print('STDERR:', result.stderr[:1000] if result.stderr else '')