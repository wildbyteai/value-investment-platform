"""Chat with a model that can search the web by itself (no separate search key).

Each search mode uses the vendor's own search with the same API key as the chat:

* ``qwen_enable_search``  通义千问 OpenAI 兼容接口的 ``enable_search`` + ``search_options``
* ``zhipu_web_search``    智谱 GLM 的 ``tools: [{"type": "web_search", ...}]``
* ``kimi_search``         Kimi：模型以函数调用发起搜索，平台用同一个 Key 调用
                          Kimi 官方 ``POST /v1/tools/search_pro``，结果回传给模型
                          （``$web_search`` 内置工具预计 2026-10-20 下线，因此不用它）
* ``openai_web_search``   OpenAI Responses 接口（``POST {base_url}/responses``）的托管
                          ``web_search`` 工具，搜索由 OpenAI 服务端执行
* ``none``                不联网

The key is read from the environment variable named on the provider; it never reaches
the database, the logs or the run record.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

from app.domains.news.collector_policy import policy
from app.domains.news.llm import LlmError, ProviderConfig

SEARCH_MODES = ('none', 'qwen_enable_search', 'zhipu_web_search', 'kimi_search', 'openai_web_search')

KIMI_TOOL = {
    'type': 'function',
    'function': {
        'name': 'web_search',
        'description': '联网搜索最新网页内容。一次只搜一个信息需求；查询词要具体（公司名、事件、日期）。',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': '搜索词'},
                'sites': {'type': 'array', 'items': {'type': 'string'}, 'description': '可选，限定站点（最多 5 个）'},
                'start_date': {'type': 'string', 'description': '可选，发布时间起，YYYY-MM-DD'},
                'end_date': {'type': 'string', 'description': '可选，发布时间止，YYYY-MM-DD'},
            },
            'required': ['query'],
        },
    },
}


@dataclass
class ChatResult:
    content: str
    searches: list[str] = field(default_factory=list)
    rounds: int = 0


def _post(client: httpx.Client, url: str, key: str, body: dict) -> dict:
    try:
        r = client.post(url, json=body, headers={'Authorization': f'Bearer {key}'})
    except httpx.HTTPError as exc:
        raise LlmError(f'模型请求失败：{type(exc).__name__}')
    if r.status_code != 200:
        detail = ''
        try:
            detail = str((r.json().get('error') or {}).get('message') or '')[:200]
        except (ValueError, AttributeError):
            pass
        raise LlmError(f'模型返回 HTTP {r.status_code}' + (f'：{detail}' if detail else ''))
    try:
        return r.json()
    except ValueError:
        raise LlmError('模型响应不是 JSON')


def _message(data: dict) -> tuple[dict, str | None]:
    try:
        choice = data['choices'][0]
        return choice['message'], choice.get('finish_reason')
    except (KeyError, IndexError, TypeError):
        raise LlmError('模型响应格式不符合 OpenAI 兼容接口')


def _kimi_search(client: httpx.Client, provider: ProviderConfig, args: dict) -> dict:
    cfg = policy()['search_modes']['kimi_search']
    body = {'text_query': str(args.get('query') or '')[:200], 'limit': cfg['limit'], 'timeout_seconds': cfg['timeout_seconds']}
    if args.get('sites'):
        body['sites'] = [str(s) for s in args['sites']][:5]
    if args.get('start_date') or args.get('end_date'):
        body['time_window'] = {k: str(args[a]) for k, a in (('start', 'start_date'), ('end', 'end_date')) if args.get(a)}
    try:
        data = _post(client, provider.base_url.rstrip('/') + cfg['endpoint'], provider.api_key, body)
    except LlmError as exc:
        return {'error': str(exc)}
    out = []
    for row in (data.get('search_results') or [])[:cfg['limit']]:
        out.append({'title': row.get('title'), 'url': row.get('url'), 'site': row.get('site_name'), 'date': row.get('date'),
                    'text': ' '.join(c.get('text', '') for c in (row.get('chunks') or [])[:3]) or row.get('snippet')})
    return {'results': out}


def _openai_responses(client: httpx.Client, provider: ProviderConfig, messages: list[dict]) -> ChatResult:
    cfg = policy()['search_modes']['openai_web_search']
    system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
    body: dict = {'model': provider.model, 'tools': [dict(cfg['tool'])], 'tool_choice': cfg['tool_choice'],
                  'input': [{'role': m['role'], 'content': m['content']} for m in messages if m['role'] != 'system']}
    if system:
        body['instructions'] = system
    temperature = (provider.options or {}).get('temperature')
    if temperature:  # reasoning models reject temperature; only send a non-default value
        body['temperature'] = temperature
    data = _post(client, provider.base_url.rstrip('/') + cfg['endpoint'], provider.api_key, body)
    if data.get('status') == 'failed':
        raise LlmError('模型返回失败：' + str((data.get('error') or {}).get('message') or '')[:200])
    result = ChatResult(content='', rounds=1)
    texts = []
    for item in data.get('output') or []:
        if item.get('type') == 'web_search_call':
            action = item.get('action') or {}
            result.searches.extend([q for q in ([action.get('query')] + list(action.get('queries') or [])) if q])
        elif item.get('type') == 'message':
            texts.extend(c.get('text', '') for c in item.get('content') or [] if c.get('type') == 'output_text')
    result.content = ''.join(texts) or str(data.get('output_text') or '')
    if not result.content:
        raise LlmError('模型没有返回文本' + ('（输出被截断）' if data.get('status') == 'incomplete' else ''))
    return result


def chat(provider: ProviderConfig, messages: list[dict], transport: httpx.BaseTransport | None = None,
         timeout: float | None = None, json_mode: bool = False) -> ChatResult:
    if not provider.configured:
        raise LlmError(f'未配置模型密钥（环境变量 {provider.api_key_env}）')
    mode = provider.search_mode or 'none'
    if mode not in SEARCH_MODES:
        raise LlmError(f'不支持的联网方式：{mode}')
    cfg = policy()
    if mode == 'openai_web_search':
        with httpx.Client(transport=transport, timeout=timeout or cfg['request_timeout_seconds']) as client:
            return _openai_responses(client, provider, messages)
    url = provider.base_url.rstrip('/') + '/chat/completions'
    body: dict = {'model': provider.model, 'messages': list(messages)}
    temperature = (provider.options or {}).get('temperature')
    if temperature is not None:
        body['temperature'] = temperature
    if json_mode and mode in ('none',):
        body['response_format'] = {'type': 'json_object'}
    if mode == 'qwen_enable_search':
        body['enable_search'] = True
        body['search_options'] = dict(cfg['search_modes'][mode]['search_options'])
    elif mode == 'zhipu_web_search':
        body['tools'] = [{'type': 'web_search', 'web_search': dict(cfg['search_modes'][mode]['web_search'])}]
    elif mode == 'kimi_search':
        body['tools'] = [KIMI_TOOL]
    result = ChatResult(content='')
    with httpx.Client(transport=transport, timeout=timeout or cfg['request_timeout_seconds']) as client:
        for _ in range(cfg['max_tool_rounds']):
            result.rounds += 1
            msg, finish = _message(_post(client, url, provider.api_key, body))
            calls = msg.get('tool_calls') or []
            if mode == 'kimi_search' and calls:
                body['messages'].append(msg)
                for call in calls:
                    fn = (call.get('function') or {})
                    try:
                        args = json.loads(fn.get('arguments') or '{}')
                    except ValueError:
                        args = {}
                    if fn.get('name') == 'web_search':
                        result.searches.append(str(args.get('query') or ''))
                        out = _kimi_search(client, provider, args)
                    else:
                        out = {'error': f"未知工具 {fn.get('name')}"}
                    body['messages'].append({'role': 'tool', 'tool_call_id': call.get('id'), 'name': fn.get('name'),
                                             'content': json.dumps(out, ensure_ascii=False)})
                continue
            result.content = msg.get('content') or ''
            return result
    raise LlmError(f"模型在 {cfg['max_tool_rounds']} 轮内没有给出结果")
