"""OpenAI-compatible chat client used to link events to companies.

Works with DeepSeek (default), OpenAI, Qwen/DashScope, Moonshot, Zhipu, local vLLM or
Ollama: anything that serves ``POST {base_url}/chat/completions``. The key is read from
the environment variable named on the provider; it never touches the database or logs.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx

from app.domains.news.policy import policy

SYSTEM_PROMPT = """你是价值投资研究助手。给你一条资讯事件和一份关注公司名单。
判断这条事件与哪些上市公司有关，返回严格 JSON：
{"links":[{"company":"公司名","ticker":"代码或空","relevance":0到1,"impact":-1到1,"rationale":"一句话理由"}]}
relevance=事件与该公司的关联度（1=事件主角，0.5=产业链直接相关，<0.3=不要返回）。
impact=对该公司长期内在价值的影响（1=重大利好，0=中性，-1=重大利空）。
优先使用名单里的公司；名单外的上市公司只有在事件主角时才返回。没有相关公司就返回 {"links":[]}。"""


@dataclass
class ProviderConfig:
    provider_key: str
    name: str
    base_url: str
    model: str
    api_key_env: str
    options: dict | None = None
    search_mode: str = 'none'

    @property
    def blocked(self) -> str | None:
        from app.core.secret_guard import provider_problem
        return provider_problem(self.base_url, self.api_key_env)

    @property
    def api_key(self) -> str:
        # Never hand a key to a URL or variable that fails the guard (see app/core/secret_guard.py).
        return '' if self.blocked else os.environ.get(self.api_key_env, '')

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class ProposedLink:
    company: str
    ticker: str | None
    relevance: Decimal
    impact: Decimal
    rationale: str


class LlmError(Exception):
    pass


def default_provider() -> ProviderConfig:
    d = policy()['default_llm_provider']
    return ProviderConfig(d['provider_key'], d['name'], d['base_url'], d['model'], d['api_key_env'], {})


def _clamp(value, low, high) -> Decimal:
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise LlmError('模型返回的分数不是数字')
    if not v.is_finite():
        raise LlmError('模型返回的分数不是有限数')
    return max(Decimal(low), min(Decimal(high), v)).quantize(Decimal('0.0001'))


def parse_links(content: str) -> list[ProposedLink]:
    text = content.strip()
    if text.startswith('```'):
        text = text.strip('`')
        text = text[text.find('{'):]
    try:
        data = json.loads(text[text.find('{'):text.rfind('}') + 1])
    except ValueError:
        raise LlmError('模型返回的不是 JSON')
    cfg = policy()['linking']
    out = []
    for row in (data.get('links') or [])[:cfg['max_companies_per_event']]:
        name = str(row.get('company') or '').strip()
        if not name:
            continue
        relevance = _clamp(row.get('relevance', 0), *cfg['relevance_range'])
        if relevance < Decimal(cfg['relevance_minimum_to_keep']):
            continue
        out.append(ProposedLink(name[:200], (str(row.get('ticker') or '').strip() or None),
                                relevance, _clamp(row.get('impact', 0), *cfg['impact_range']),
                                str(row.get('rationale') or '')[:1000]))
    return out


def propose_links(provider: ProviderConfig, event_text: str, watchlist: list[str],
                  transport: httpx.BaseTransport | None = None, timeout: float = 60) -> list[ProposedLink]:
    if provider.blocked:
        raise LlmError(f'模型配置未通过安全检查：{provider.blocked}')
    if not provider.configured:
        raise LlmError(f'未配置模型密钥（环境变量 {provider.api_key_env}）')
    body = {
        'model': provider.model,
        'temperature': (provider.options or {}).get('temperature', 0),
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': '关注公司名单：\n' + '\n'.join(watchlist or ['（暂无）']) + '\n\n事件：\n' + event_text},
        ],
    }
    url = provider.base_url.rstrip('/') + '/chat/completions'
    try:
        with httpx.Client(transport=transport, timeout=timeout) as client:
            r = client.post(url, json=body, headers={'Authorization': f'Bearer {provider.api_key}'})
    except httpx.HTTPError as exc:
        raise LlmError(f'模型请求失败：{type(exc).__name__}')
    if r.status_code != 200:
        raise LlmError(f'模型返回 HTTP {r.status_code}')
    try:
        content = r.json()['choices'][0]['message']['content']
    except (ValueError, KeyError, IndexError, TypeError):
        raise LlmError('模型响应格式不符合 OpenAI 兼容接口')
    return parse_links(content)
