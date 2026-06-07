#!/usr/bin/env python3
# security/generate_keys.py
# Run ONCE on first deployment to generate RSA key pair.
# In production, generate inside Vault and never write private key to disk.
# Usage: python -m security.generate_keys

import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

KEYS_DIR = Path("keys")


def generate_rsa_keypair(bits: int = 4096):
    """
    Generate a 4096-bit RSA key pair.
    4096-bit is NIST-recommended for long-lived government signing keys.
    """
    KEYS_DIR.mkdir(mode=0o700, exist_ok=True)  # owner read/write only

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=bits,
        backend=default_backend()
    )

    # Write private key — PEM, no passphrase here (passphrase managed by Vault)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    priv_path = KEYS_DIR / "private.pem"
    priv_path.write_bytes(private_pem)
    priv_path.chmod(0o600)  # owner read-only

    # Write public key — safe to distribute to any verifying service
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pub_path = KEYS_DIR / "public.pem"
    pub_path.write_bytes(public_pem)
    pub_path.chmod(0o644)  # readable by all

    print(f"✅ RSA-4096 key pair generated")
    print(f"   Private key: {priv_path} (600 permissions — never commit this)")
    print(f"   Public key:  {pub_path}  (644 permissions — safe to distribute)")
    print(f"⚠️  Add keys/ to .gitignore immediately if not already there")


if __name__ == "__main__":
    if (KEYS_DIR / "private.pem").exists():
        confirm = input("Keys already exist. Overwrite? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            exit(0)
    generate_rsa_keypair()
