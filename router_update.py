import re

with open('/root/agenticseek/router.py', 'r') as f:
    content = f.read()

# Replace the requests.get line
old_line = 'response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=30)'
new_code = '''try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=30)
        except:
            http_url = url.replace("https://", "http://")
            response = requests.get(http_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)'''

content = content.replace(old_line, new_code)

with open('/root/agenticseek/router.py', 'w') as f:
    f.write(content)

print('Updated!')
