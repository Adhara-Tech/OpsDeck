import secrets
import string

def generate_secure_password(length=12):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for i in range(length))
