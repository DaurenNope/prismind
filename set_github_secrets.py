#!/usr/bin/env python3
"""
Set all GitHub secrets from env.txt
"""
import subprocess
import sys

# Add TELEGRAM_CHAT_ID to env.txt if not present
with open('env.txt', 'r') as f:
    content = f.read()
    if 'TELEGRAM_CHAT_ID=319089661' not in content:
        with open('env.txt', 'a') as f:
            f.write('TELEGRAM_CHAT_ID=319089661\n')

print("🔐 Setting GitHub Secrets from env.txt...")

# Read env.txt and set GitHub secrets
with open('env.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            if value and value != 'your_perplexity_api_key_here':
                print(f'Setting {key}...')
                try:
                    result = subprocess.run(['gh', 'secret', 'set', key, '--body', value], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f'  ✅ {key} set')
                    else:
                        print(f'  ⚠️ {key} failed: {result.stderr.strip()}')
                except FileNotFoundError:
                    print(f'  ❌ gh CLI not found - install GitHub CLI first')
                    sys.exit(1)

print('✅ All secrets set!')
print('Now you can delete env.txt and test the workflow.')

