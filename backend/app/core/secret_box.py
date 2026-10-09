"""Encrypt model API keys entered on the 模型配置 page before they reach the database.

* Algorithm: AES-256-GCM (``cryptography``), a fresh 12-byte nonce per value, and the owning
  row as associated data (``llm_provider:<id>``), so a ciphertext copied onto another row does
  not decrypt.
* Master key: ``VIP_SECRET_KEY`` in the server environment, 32 random bytes in base64
  (``openssl rand -base64 32``). It never lives in the database, so a database backup alone
  cannot decrypt the keys.
* Rotation: put the new key in ``VIP_SECRET_KEY`` and the old one in ``VIP_SECRET_KEY_PREVIOUS``,
  run ``python -m app.admin_cli rotate-secret-key`` (re-encrypts every saved key with the new
  master key), then remove ``VIP_SECRET_KEY_PREVIOUS``.

Plain values never leave this module except through ``decrypt``; errors never contain them.
"""
from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.errors import Invalid

PREFIX = 'v1:'
MISSING = '系统未配置 VIP_SECRET_KEY（服务器主密钥），不能在页面保存 API Key。请运维在服务器环境变量中设置后重启；在此之前仍可使用环境变量里的密钥。'
BAD_FORMAT = 'VIP_SECRET_KEY 格式不对：应为 32 字节随机数的 base64（生成：openssl rand -base64 32）'


class SecretBoxError(Exception):
    """Raised for configuration/decryption problems. The message is safe to show and log."""


def _decode(raw: str) -> bytes:
    text = raw.strip().replace('-', '+').replace('_', '/')
    text += '=' * (-len(text) % 4)
    try:
        key = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        raise SecretBoxError(BAD_FORMAT)
    if len(key) != 32:
        raise SecretBoxError(BAD_FORMAT)
    return key


def _keys() -> list[bytes]:
    """Current key first, then the previous one (only during a rotation)."""
    current = os.environ.get('VIP_SECRET_KEY', '').strip()
    if not current:
        return []
    keys = [_decode(current)]
    previous = os.environ.get('VIP_SECRET_KEY_PREVIOUS', '').strip()
    if previous:
        keys.append(_decode(previous))
    return keys


def available() -> bool:
    try:
        return bool(_keys())
    except SecretBoxError:
        return False


def problem() -> str | None:
    """Why page-saved keys cannot be used right now (None when they can)."""
    try:
        return None if _keys() else MISSING
    except SecretBoxError as exc:
        return str(exc)


def encrypt(plain: str, context: str) -> str:
    """Encrypt with the current master key; raises ``Invalid`` (HTTP 422) when it is missing."""
    try:
        keys = _keys()
    except SecretBoxError as exc:
        raise Invalid(str(exc))
    if not keys:
        raise Invalid(MISSING)
    nonce = os.urandom(12)
    sealed = AESGCM(keys[0]).encrypt(nonce, plain.encode('utf-8'), context.encode('utf-8'))
    return PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode('ascii')


def decrypt(token: str, context: str) -> str:
    keys = _keys()
    if not keys:
        raise SecretBoxError(MISSING)
    if not token.startswith(PREFIX):
        raise SecretBoxError('已保存的 Key 格式无法识别')
    try:
        blob = base64.urlsafe_b64decode(token[len(PREFIX):].encode('ascii'))
    except (binascii.Error, ValueError):
        raise SecretBoxError('已保存的 Key 格式无法识别')
    nonce, sealed = blob[:12], blob[12:]
    for key in keys:
        try:
            return AESGCM(key).decrypt(nonce, sealed, context.encode('utf-8')).decode('utf-8')
        except InvalidTag:
            continue
    raise SecretBoxError('已保存的 Key 无法用当前 VIP_SECRET_KEY 解密（主密钥被更换？请重新填写 Key）')


def reencrypt(token: str, context: str) -> str:
    """Decrypt with any known key and encrypt again with the current one (rotation)."""
    return encrypt(decrypt(token, context), context)
