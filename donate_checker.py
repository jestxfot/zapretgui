import hashlib

uuid = "b8d6d910-47fa-5f5c-82ae-7968c0d6935d"
salt = "premium_salt_2025_zapret"
signature = hashlib.sha256(f"{uuid}{salt}premium".encode()).hexdigest()

print(f"UUID: {uuid}")
print(f"Salt: {salt}")
print(f"Signature: {signature}")