"""Account administration from the server shell (there is no self sign-up).

    python -m app.admin_cli create-workspace "价值投资研究"
    python -m app.admin_cli create-user alice@example.com "Alice" --workspace "价值投资研究" --role system_admin
    python -m app.admin_cli set-password alice@example.com          # prompts twice, never echoes
    python -m app.admin_cli disable-user alice@example.com          # also signs out every browser
    python -m app.admin_cli list-users
    python -m app.admin_cli install-collector-presets --workspace "价值投资研究" --provider qwen   # 预置采集定时器，可重复执行

Passwords are read with getpass (or one line from stdin with --stdin), never from argv, so they
do not end up in shell history or the process list.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.errors import DomainError
from app.domains.identity import passwords, sessions
from app.db import SessionLocal
from app.models.identity import Membership, User, Workspace
from app.models.news import LlmProvider
from app.domains.identity.permissions import VALID_ROLES


def _workspace(db, ref: str) -> Workspace:
    ws = db.get(Workspace, ref) or db.scalar(select(Workspace).where(Workspace.name == ref))
    if ws is None:
        sys.exit(f'没有工作区：{ref}')
    return ws


def _user(db, login: str) -> User:
    user = db.scalar(select(User).where(User.login == login.strip().lower()))
    if user is None:
        sys.exit(f'没有账号：{login}')
    return user


def _read_password(stdin: bool) -> str:
    if stdin:
        pw = sys.stdin.readline().rstrip('\n')
    else:
        pw = getpass.getpass('新密码：')
        if getpass.getpass('再输一次：') != pw:
            sys.exit('两次输入不一致')
    problem = passwords.password_problem(pw)
    if problem:
        sys.exit(problem)
    return pw


def _provider(db, ws: Workspace, ref: str) -> LlmProvider:
    row = db.get(LlmProvider, ref) if len(ref) == 36 else None
    row = row or db.scalar(select(LlmProvider).where(LlmProvider.workspace_id == ws.id, LlmProvider.provider_key == ref))
    if row is None or row.workspace_id != ws.id:
        sys.exit(f'工作区 {ws.name} 里没有模型：{ref}（先在 后台设置 › 模型配置 添加，可用 id 或标识）')
    return row


def _install_presets(db, args) -> None:
    from app.domains.news import collector_presets
    ws = _workspace(db, args.workspace)
    provider = _provider(db, ws, args.provider)
    actor = _user(db, args.actor).id if args.actor else None
    try:
        result = collector_presets.install(db, ws.id, actor, provider.id, args.only or None)
    except DomainError as exc:
        db.rollback()
        sys.exit(exc.detail)
    db.commit()
    print(f"Skill「{collector_presets.presets()['skill']['name']}」：{'新建' if result['skill_created'] else '已存在'}")
    for c in result['created']:
        print(f"新建：{c['name']}")
    for c in result['skipped']:
        print(f"已存在，跳过：{c['name']}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog='python -m app.admin_cli')
    sub = p.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('create-workspace'); w.add_argument('name')
    c = sub.add_parser('create-user'); c.add_argument('login'); c.add_argument('display_name')
    c.add_argument('--workspace', required=True); c.add_argument('--role', action='append', required=True, choices=sorted(VALID_ROLES))
    s = sub.add_parser('set-password'); s.add_argument('login'); s.add_argument('--stdin', action='store_true')
    d = sub.add_parser('disable-user'); d.add_argument('login')
    e = sub.add_parser('enable-user'); e.add_argument('login')
    sub.add_parser('list-users')
    ip = sub.add_parser('install-collector-presets', help='导入预置采集定时器（config/collector-presets-v1.json），已有的跳过')
    ip.add_argument('--workspace', required=True); ip.add_argument('--provider', required=True, help='能联网的模型：id 或标识（如 qwen）')
    ip.add_argument('--only', action='append', help='只导入某个预置任务的 key，可多次'); ip.add_argument('--actor', help='记在审计里的账号')
    args = p.parse_args(argv)
    with SessionLocal() as db:
        if args.cmd == 'install-collector-presets':
            _install_presets(db, args)
        elif args.cmd == 'create-workspace':
            ws = Workspace(name=args.name); db.add(ws); db.commit(); print(ws.id)
        elif args.cmd == 'create-user':
            ws = _workspace(db, args.workspace)
            login = args.login.strip().lower()
            user = db.scalar(select(User).where(User.login == login))
            if user is None:
                user = User(login=login, display_name=args.display_name); db.add(user); db.flush()
            for role in args.role:
                if not db.scalar(select(Membership.id).where(Membership.user_id == user.id, Membership.workspace_id == ws.id, Membership.role == role)):
                    db.add(Membership(user_id=user.id, workspace_id=ws.id, role=role))
            db.commit(); print(f'{login} → {ws.name}：{", ".join(args.role)}。下一步：python -m app.admin_cli set-password {login}')
        elif args.cmd == 'set-password':
            user = _user(db, args.login)
            user.password_hash = passwords.hash_password(_read_password(args.stdin))
            sessions.revoke_user(db, user.id)
            db.commit(); print('已设置，并退出了该账号所有已登录的浏览器')
        elif args.cmd in ('disable-user', 'enable-user'):
            user = _user(db, args.login)
            user.disabled = args.cmd == 'disable-user'
            if user.disabled:
                sessions.revoke_user(db, user.id)
            db.commit(); print('已停用' if user.disabled else '已启用')
        else:
            for u in db.scalars(select(User).order_by(User.login)).all():
                roles = db.execute(select(Workspace.name, Membership.role).join(Workspace, Workspace.id == Membership.workspace_id)
                                   .where(Membership.user_id == u.id)).all()
                print(f"{u.login}\t{u.display_name}\t{'停用' if u.disabled else ('有密码' if u.password_hash else '无密码')}\t"
                      + '；'.join(f'{n}:{r}' for n, r in roles))


if __name__ == '__main__':
    main()
