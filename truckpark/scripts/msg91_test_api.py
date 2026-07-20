import os

import httpx


authkey = os.environ.get("MSG91_AUTHKEY")
if not authkey:
    raise SystemExit("Set MSG91_AUTHKEY before running this script.")

headers = {"accept": "application/json", "authkey": authkey}
urls = [
    "https://api.msg91.com/api/v5/whatsapp/whatsapp-activation/",
    "https://api.msg91.com/api/v5/whatsapp/client-panel-template/",
    "https://api.msg91.com/api/v5/whatsapp/get-templates/",
]

for url in urls:
    print("\nGET", url)
    try:
        response = httpx.get(url, headers=headers, timeout=15)
        print("STATUS", response.status_code)
        print(response.text[:2000])
    except Exception as exc:
        print("EXC", exc)
