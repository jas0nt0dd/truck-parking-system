import httpx
import time


API = "http://localhost:8000/api/v1"
HEALTH = "http://localhost:8000/health"


def wait_for_health(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(HEALTH, timeout=5.0)
            if r.status_code == 200:
                print("health ok")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    if not wait_for_health(60):
        print("Backend did not become healthy")
        return 1

    # login as seeded root admin
    login = httpx.post(f"{API}/auth/login", json={"mobile": "7200775876", "password": "0000"})
    print("login status", login.status_code)
    print(login.text)
    token = login.json().get("access_token")
    if not token:
        print("login failed")
        return 2

    headers = {"Authorization": f"Bearer {token}"}

    # create a temporary user
    payload = {"name": "E2E Test", "mobile": "7777001122", "role": "gatekeeper", "password": "secret1"}
    r = httpx.post(f"{API}/users", json=payload, headers=headers)
    print("create status", r.status_code)
    print(r.text)
    if r.status_code != 201:
        return 3
    user = r.json()
    user_id = user.get("id")

    # delete the user
    dr = httpx.delete(f"{API}/users/{user_id}", headers=headers)
    print("delete status", dr.status_code)
    print(dr.text)

    # list users and confirm not present
    lr = httpx.get(f"{API}/users", headers=headers)
    print("list status", lr.status_code)
    users = lr.json()
    found = any(u.get("id") == user_id for u in users)
    print("found after delete?", found)
    return 0 if not found else 4


if __name__ == "__main__":
    raise SystemExit(main())
