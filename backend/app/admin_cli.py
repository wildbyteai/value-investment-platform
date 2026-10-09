"""Account administration from the server shell (there is no self sign-up).

    python -m app.admin_cli create-workspace "价值投资研究"
    python -m app.admin_cli create-user alice@example.com "Alice" --workspace "价值投资研究" --role system_admin
    python -m app.admin_cli set-password alice@example.com          # prompts twice, never echoes
    python -m app.admin_cli disable-user alice@example.com          # also signs out every browser
    python -m app.admin_cli list-users

Passwords are read with getpass (or one line from stdin with --stdin), never from argv, so they
do not end up in shell history or the process list.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.domains.identity import passwords, sessions
from app.db import SessionLocal
from app.models.identity import Membership, User, Workspace
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
    args = p.parse_args(argv)
    with SessionLocal() as db:
        if args.cmd == 'create-workspace':
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
