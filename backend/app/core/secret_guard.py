"""Keep model API keys from being sent anywhere but the vendor they belong to.

An administrator chooses, per model, a base URL and either types the key on the page (stored
encrypted, app/core/secret_box.py) or names the environment variable that holds it. Without limits, that admin (or anyone holding an admin session) could point
``base_url`` at their own server and pick ``VIP_OPENAI_API_KEY`` -- or even ``VIP_SMTP_PASSWORD``
-- and the platform would send the secret there on the next call. So:

* the variable must look like a model key (``VIP_…_KEY``) and never be another secret
  (in particular not the master key ``VIP_SECRET_KEY`` / ``VIP_SECRET_KEY_PREVIOUS``);
* the URL must be HTTPS and its host must be on the allowlist: the vendor hosts in
  ``config/*.json`` plus whatever the server operator adds in ``VIP_LLM_ALLOWED_HOSTS``.
  Only someone who can edit the server environment can widen it, not the web admin.

The same check runs when a key is read (page-saved or env), so a row saved before this guard
existed is inert.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.core.paths import REPO_ROOT as ROOT
KEY_ENV_RE = re.compile(r'^VIP_[A-Z0-9_]+_KEY$')
FORBIDDEN_PREFIXES = ('VIP_DB', 'VIP_SMTP', 'VIP_SESSION', 'VIP_AUTH', 'VIP_ADMIN', 'VIP_POSTGRES', 'VIP_SECRET')


def _config_hosts() -> set[str]:
    hosts: set[str] = set()
    for name in ('news-collector-v1.json', 'news-radar-v1.json'):
        try:
            data = json.loads((ROOT / 'config' / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rows = list(data.get('provider_presets') or [])
        if data.get('default_llm_provider'):
            rows.append(data['default_llm_provider'])
        for row in rows:
            host = urlsplit(row.get('base_url') or '').hostname
            if host:
                hosts.add(host.lower())
    return hosts


def allowed_llm_hosts() -> set[str]:
    extra = {h.strip().lower() for h in os.environ.get('VIP_LLM_ALLOWED_HOSTS', '').split(',') if h.strip()}
    return _config_hosts() | extra


def key_env_problem(name: str) -> str | None:
    if not KEY_ENV_RE.match(name or ''):
        return '密钥环境变量名必须形如 VIP_XXX_API_KEY'
    if name.startswith(FORBIDDEN_PREFIXES):
        return '这个环境变量不是模型密钥，不能用于模型配置'
    return None


def base_url_problem(url: str) -> str | None:
    parts = urlsplit(url or '')
    if parts.scheme != 'https' or not parts.hostname:
        return '模型接口地址必须是 https:// 开头'
    if parts.username or parts.password:
        return '模型接口地址不能包含账号密码'
    host = parts.hostname.lower()
    if host not in allowed_llm_hosts():
        return f'接口域名 {host} 不在允许列表；如确需使用代理接口，请运维在服务器环境变量 VIP_LLM_ALLOWED_HOSTS 中加入该域名'
    return None


def provider_problem(base_url: str, key_env: str) -> str | None:
    return key_env_problem(key_env) or base_url_problem(base_url)


# ------------------------------------------------------------------ outbound fetches (RSS)

def _public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            return False
    return True


class PublicOnlyTransport(httpx.HTTPTransport):
    """Refuse requests (including redirects) to loopback, private, link-local or metadata
    addresses, so a feed URL cannot be used to probe the server's own network."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme not in ('http', 'https') or not _public(request.url.host):
            raise httpx.ConnectError('目标地址不是公网地址，已拒绝', request=request)
        return super().handle_request(request)
