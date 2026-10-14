"""Local configuration and consistent backups. Does not start the website."""

import argparse
from contextlib import closing
from datetime import datetime
from getpass import getpass
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import zipfile

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parent
INSTANCE = Path(os.environ.get('GOTOGETHER_INSTANCE', ROOT / 'instance')).resolve()


def write_config(config):
    INSTANCE.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=INSTANCE, delete=False, suffix='.tmp') as output:
            temporary = Path(output.name)
            json.dump(config, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.replace(temporary, INSTANCE / 'config.json')
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def configure(reset=False):
    path = INSTANCE / 'config.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if config and not reset:
        print('已有配置，账号和数据保持不变。修改管理员请运行 manage.py reset-admin。')
        return
    default = config.get('ADMIN_USERNAME', 'admin')
    username = input(f'管理员账号 [{default}]：').strip() or default
    if not 1 <= len(username) <= 80:
        raise ValueError('管理员账号需为 1–80 个字符。')
    password = getpass('设置管理员密码（至少 8 个字符）：')
    if len(password) < 8:
        raise ValueError('密码至少需要 8 个字符。')
    if password != getpass('再次输入密码：'):
        raise ValueError('两次输入的密码不一致。')
    config.setdefault('SECRET_KEY', secrets.token_hex(32))
    config.setdefault('HOST', '0.0.0.0')
    config.setdefault('PORT', 8080)
    config['ADMIN_USERNAME'] = username
    config['ADMIN_PASSWORD_HASH'] = generate_password_hash(password)
    write_config(config)
    print(f'配置已保存到 {path}。')
    if reset:
        print('请重启网站，新密码将在重启后生效，原管理员登录会失效。')


def backup():
    source = INSTANCE / 'gotogether.sqlite3'
    configuration = INSTANCE / 'config.json'
    if not source.is_file() or not configuration.is_file():
        raise ValueError('未找到完整的网站数据和配置，请先配置并启动过网站。')
    destination = INSTANCE / 'backups'
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f'gotogether-{datetime.now():%Y%m%d-%H%M%S-%f}.zip'
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        snapshot = Path(temporary) / 'gotogether.sqlite3'
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original, closing(sqlite3.connect(snapshot)) as copied:
            original.backup(copied)
        staged = Path(temporary) / 'backup.zip'
        with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(snapshot, 'gotogether.sqlite3')
            bundle.write(configuration, 'config.json')
        os.replace(staged, archive)
    print(f'备份已保存：{archive}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GoTogether 管理工具')
    parser.add_argument('action', choices=('setup', 'reset-admin', 'backup'))
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            backup()
        else:
            configure(reset=args.action == 'reset-admin')
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f'操作未完成：{exc}\n')
