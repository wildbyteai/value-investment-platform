"""Password hashing with the standard library's scrypt (no extra dependency)."""
import base64
import hashlib
import hmac
import secrets

N, R, P = 2 ** 15, 8, 1
MIN_LENGTH = 12


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, maxmem=64 * 1024 * 1024, dklen=32)
    return f'scrypt${N}${R}${P}${_b64(salt)}${_b64(digest)}'


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        hash_password(password)  # same cost whether or not the account exists
        return False
    try:
        algo, n, r, p, salt, digest = stored.split('$')
        if algo != 'scrypt':
            return False
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             maxmem=64 * 1024 * 1024, dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, base64.b64decode(digest))


def password_problem(password: str) -> str | None:
    if len(password) < MIN_LENGTH:
        return f'密码至少 {MIN_LENGTH} 位'
    if len(set(password)) < 6:
        return '密码太简单'
    return None
