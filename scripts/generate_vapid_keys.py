"""Generate a VAPID keypair for Web Push.

Run once:
    python scripts/generate_vapid_keys.py

Then copy the three printed lines into your .env file:

    VAPID_PRIVATE_KEY=...
    VAPID_PUBLIC_KEY=...
    VAPID_SUBJECT=mailto:you@example.com

Both keys are base64url-encoded strings (safe for single-line .env).
Regenerating these invalidates all existing browser subscriptions —
users will need to re-enable reminders. Keep them stable.
"""
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid.utils import b64urlencode


def main():
    pk = ec.generate_private_key(ec.SECP256R1(), default_backend())

    # Raw 32-byte private scalar → base64url. pywebpush accepts this form
    # directly as `vapid_private_key`, so the .env stays single-line.
    priv_int = pk.private_numbers().private_value
    priv_bytes = priv_int.to_bytes(32, byteorder="big")
    private_b64 = b64urlencode(priv_bytes)

    # Uncompressed public point (0x04 || X(32) || Y(32)) → base64url.
    raw_public = pk.public_key().public_numbers()
    public_bytes = (
        b"\x04"
        + raw_public.x.to_bytes(32, byteorder="big")
        + raw_public.y.to_bytes(32, byteorder="big")
    )
    public_b64 = b64urlencode(public_bytes)

    print("# Copy these three lines into your .env file:")
    print()
    print(f"VAPID_PRIVATE_KEY={private_b64}")
    print(f"VAPID_PUBLIC_KEY={public_b64}")
    print("VAPID_SUBJECT=mailto:you@example.com")


if __name__ == "__main__":
    main()
