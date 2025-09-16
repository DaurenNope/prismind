#!/usr/bin/env python3
"""
Set all GitHub secrets from .env file
"""
import subprocess
import sys

print("🔐 Setting GitHub Secrets from .env file...")

# Read .env file and set GitHub secrets
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            # Remove quotes if present
            value = value.strip().strip('"').strip("'")
            if value and value != 'your_perplexity_api_key_here' and not value.startswith('/path/to/'):
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
print('Now you can test the workflow.')