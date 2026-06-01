"""Agent package init.

Inject the operating system's certificate trust store into Python's SSL stack
before any network call (Groq API, Hugging Face model download). In corporate
environments that intercept TLS, the proxy's root CA lives in the OS store but
not in Python's bundled certifi bundle, which otherwise causes
CERTIFICATE_VERIFY_FAILED. This keeps verification ON (no insecure downgrade).
"""

try:  # truststore is optional; ignore if unavailable.
    import truststore

    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001 — best-effort; fall back to default certs.
    pass
