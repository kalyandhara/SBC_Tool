import subprocess
import sys

result = subprocess.run(['node', '--check', 'static/app.js'], capture_output=True, text=True, cwd='D:\\SBC_Tool')
print('Return code:', result.returncode)
print('STDERR:')
print(result.stderr)
print('STDOUT:', result.stdout)