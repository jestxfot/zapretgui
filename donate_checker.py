import hashlib

uuid = "43bbf3ac-4248-54dc-99c7-1cc4750d51cd"
salt = "premium_salt_2025_zapret"
signature = hashlib.sha256(f"{uuid}{salt}premium".encode()).hexdigest()

print(f"UUID: {uuid}")
print(f"Salt: {salt}")
print(f"Signature: {signature}")