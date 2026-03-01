#!/usr/bin/env python3
"""Fetch a Firebase ID token using credentials from test_auth.json."""
import json
import urllib.request

with open("test_auth.json") as f:
    creds = json.load(f)

url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={creds['web_api_key']}"
payload = json.dumps({
    "email": creds["email"],
    "password": creds["password"],
    "returnSecureToken": True,
}).encode()

req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    data = json.load(resp)

print(data["idToken"])
