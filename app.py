"""GoTogether: name-based member access and a separate password-protected admin."""

from datetime import timedelta
from functools import wraps
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import store


def create_app(test_config=None):
    instance = Path(os.environ.get('GOTOGETHER_INSTANCE', Path(__file__).parent / 'instance')).resolve()
    app = Flask(__name__, instance_path=str(instance))
    app.config.update(
        DATABASE=str(instance / 'gotogether.sqlite3'),
        SESSION_COOKIE_NAME='gotogether_session',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config is not None:
        app.config.update(test_config)
    else:
        config_path = instance / 'config.json'
        if not config_path.exists():
            raise RuntimeError('尚未配置管理员，请先运行 setup.cmd。')
        config = json.loads(config_path.read_text(encoding='utf-8'))
        for key in ('SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH'):
            if not isinstance(config.get(key), str) or not config[key]:
                raise RuntimeError(f'配置缺少 {key}，请运行 manage.py setup。')
        if len(config['SECRET_KEY']) < 32:
            raise RuntimeError('SECRET_KEY 长度不足，请重新配置。')
        app.config.update(config)
    store.initialize(app.config['DATABASE'])

    def db():
        if 'db' not in g:
            g.db = store.connect(app.config['DATABASE'])
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()

    def admin_version():
        return hashlib.sha256(app.config['ADMIN_PASSWORD_HASH'].encode()).hexdigest()

    @app.before_request
    def prepare_request():
        g.person = session.get('person', '')
        g.admin = session.get('admin_version') == admin_version()
        session.setdefault('csrf', secrets.token_urlsafe(32))
        if request.method == 'POST':
            token = request.form.get('csrf', '')
            if not hmac.compare_digest(token.encode(), session['csrf'].encode()):
                abort(400, description='页面已过期，请刷新页面后重试。')

    @app.after_request
    def headers(response):
        # Windows may associate .js with text/plain; nosniff would block the script.
        if (request.endpoint == 'static' and response.status_code in (200, 206)
                and request.view_args.get('filename', '').endswith('.js')):
            response.mimetype = 'text/javascript'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.context_processor
    def template_helpers():
        return {'csrf_token': lambda: session['csrf'],
                'vehicle_appearances': store.VEHICLE_APPEARANCES,
                'vehicle_colors': store.VEHICLE_COLORS,
                'vehicle_image': store.vehicle_image,
                'default_vehicle_appearance': store.DEFAULT_VEHICLE_APPEARANCE,
                'mode_labels': {'drive': '自己开车', 'ride': '拼车', 'public': '公共交通', 'other': '其他自行前往', 'wait': '等车中'}}

    def member_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.person:
                return redirect(url_for('identity', next=request.full_path.rstrip('?')))
            return view(*args, **kwargs)
        return wrapped

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not g.admin:
                return redirect(url_for('admin_login', next=request.full_path.rstrip('?')))
            return view(*args, **kwargs)
        return wrapped

    def next_path(value, default):
        value = str(value or '')
        try:
            parts = urlsplit(value)
        except ValueError:
            return default
        if not value.startswith('/') or value.startswith('//') or '\\' in value or parts.netloc or parts.scheme or any(ord(c) < 32 for c in value):
            return default
        return value

    @app.route('/')
    def entry():
        return redirect(url_for('identity'))

    @app.route('/identity', methods=['GET', 'POST'])
    def identity():
        target = next_path(request.values.get('next'), url_for('events'))
        error = None
        if request.method == 'POST':
            try:
                session['person'] = store.name(request.form.get('name'))
                session['csrf'] = secrets.token_urlsafe(32)
                return redirect(target, code=303)
            except store.UserError as exc:
                error = str(exc)
        return render_template('identity.html', error=error, target=target), 400 if error else 200

    @app.route('/events')
    @member_required
    def events():
        return render_template('events.html', events=store.event_list(db()), admin=False)

    @app.route('/events/new', methods=['GET', 'POST'])
    @member_required
    def event_new():
        error, status = None, 200
        if request.method == 'POST':
            try:
                event_id = store.create_event(db(), g.person, request.form)
                flash('活动已创建，可以分享链接邀请同事登记。', 'success')
                return redirect(url_for('event_detail', event_id=event_id), code=303)
            except store.UserError as exc:
                error, status = str(exc), exc.status
        return render_template('event_form.html', event=None, values=request.form, error=error, admin=False), status

    def scene_context(event_id):
        data = store.snapshot(db(), event_id)
        for person in data['records']:
            person['key'] = hashlib.sha256(person['name'].encode()).hexdigest()
        mine = next((r for r in data['records'] if r['name'] == g.person), None)
        my_car = next((c for c in data['cars'] if c['driver'] == g.person), None)
        default = f"car-{mine['vehicle_id']}" if mine and mine['vehicle_id'] else mine['mode'] if mine else (f"car-{data['cars'][0]['id']}" if data['cars'] else 'public')
        focus = request.args.get('focus', default)
        valid = ['public', 'other', 'wait'] + [f"car-{c['id']}" for c in data['cars']] + [f"wait-{r['key']}" for r in data['waiting']]
        if focus not in valid:
            focus = default
        viewer = hashlib.sha256(json.dumps([g.person, g.admin, session['csrf']]).encode()).hexdigest()
        revision = hashlib.sha256(json.dumps([data, viewer], sort_keys=True).encode()).hexdigest()
        return dict(data, mine=mine, my_car=my_car, focus=focus, admin=g.admin,
                    sync_revision=revision, sync_viewer=viewer)

    @app.route('/events/<event_id>')
    def event_detail(event_id):
        if not g.person and not g.admin:
            return redirect(url_for('identity', next=request.full_path.rstrip('?')))
        context = scene_context(event_id)
        motion = session.pop('motion', None)
        if not motion or motion.get('event') != event_id:
            motion = None
        return render_template('event.html', **context, motion=motion, fragment=False)

    @app.get('/events/<event_id>/sync')
    def event_sync(event_id):
        if not g.person and not g.admin:
            return jsonify(error='identity_changed'), 401
        context = scene_context(event_id)
        if request.args.get('viewer') != context['sync_viewer']:
            return jsonify(error='identity_changed'), 409
        if request.args.get('revision') == context['sync_revision']:
            return jsonify(revision=context['sync_revision'])
        return jsonify(revision=context['sync_revision'],
                       html=render_template('event.html', **context, motion=None, fragment=True))

    def editor_destination(event_id, admin):
        return url_for('event_detail' if not admin or request.values.get('scene') == '1' else 'admin_event', event_id=event_id)

    @app.post('/events/<event_id>/collect')
    @member_required
    def collect(event_id):
        vehicle_id = store.collect_waiter(db(), event_id, g.person, request.form)
        session['motion'] = {'event': event_id, 'focus': f'car-{vehicle_id}', 'kind': 'board'}
        flash('乘客已加入你的车辆。', 'success')
        return redirect(url_for('event_detail', event_id=event_id, focus=f'car-{vehicle_id}'), code=303)

    @app.post('/events/<event_id>/release')
    @member_required
    def release(event_id):
        vehicle_id = store.release_passenger(db(), event_id, g.person, request.form)
        leaving = store.name(request.form.get('name')) == g.person
        flash('已退出车辆并回到等车区，上车需求已保留。' if leaving else '乘客已移回等车区，上车需求已保留。', 'success')
        return redirect(url_for('event_detail', event_id=event_id, focus='wait' if leaving else f'car-{vehicle_id}'), code=303)

    @app.post('/events/<event_id>/leave-mode')
    @member_required
    def leave_mode(event_id):
        store.leave_transport(db(), event_id, g.person, request.form)
        flash('已退出原出行方式并回到等车区，已有信息已保留。', 'success')
        return redirect(url_for('event_detail', event_id=event_id, focus='wait'), code=303)

    def edit_event(event_id, admin):
        event = store.get_event(db(), event_id)
        store.require_editor(event, g.person, admin)
        error, status = None, 200
        if request.method == 'POST':
            try:
                store.update_event(db(), event_id, g.person, request.form, admin=admin)
                flash('活动信息已更新。', 'success')
                return redirect(editor_destination(event_id, admin), code=303)
            except store.UserError as exc:
                error, status = str(exc), exc.status
        return render_template('event_form.html', event=event, values=request.form if request.method == 'POST' else event, error=error, admin=admin, back_url=editor_destination(event_id, admin)), status

    @app.route('/events/<event_id>/edit', methods=['GET', 'POST'])
    @member_required
    def event_edit(event_id):
        return edit_event(event_id, False)

    @app.post('/events/<event_id>/toggle')
    @member_required
    def event_toggle(event_id):
        store.update_event(db(), event_id, g.person, request.form, toggle=True)
        flash('登记状态已更新。', 'success')
        return redirect(url_for('event_detail', event_id=event_id), code=303)

    def travel_editor(event_id, admin=False):
        incoming = request.form if request.method == 'POST' else request.args
        person = str(incoming.get('name', '')) if admin else g.person
        error, status = None, 200
        if request.method == 'POST':
            try:
                person = store.name(person)
                vehicle_id = store.save_travel(db(), event_id, person, request.form, admin=admin)
                mode = request.form['mode']
                if admin:
                    flash('出行安排已保存。', 'success')
                    return redirect(editor_destination(event_id, admin), code=303)
                focus = f'car-{vehicle_id}' if vehicle_id else mode if mode in ('public', 'other', 'wait') else None
                session['motion'] = {'event': event_id, 'focus': focus, 'kind': 'arrive' if mode == 'drive' else 'board'}
                flash('已提交给管理员。' if mode == 'pending' else '出行安排已保存。', 'success')
                return redirect(url_for('event_detail', event_id=event_id, focus=focus), code=303)
            except store.UserError as exc:
                error, status = str(exc), exc.status
        data = store.snapshot(db(), event_id)
        if request.method == 'GET':
            store.require_open(data['event'], admin)
            if person:
                person = store.name(person)
        old = next((r for r in data['records'] if r['name'] == person), None)
        vehicle = next((c for c in data['cars'] if old and c['id'] == old['vehicle_id']), None)
        if request.method == 'POST':
            values = request.form
        else:
            values = {'mode': request.args.get('mode', old['mode'] if old else 'ride'), 'revision': old['revision'] if old else '',
                      'name': person, 'note': old['note'] if old else ''}
            if vehicle and old['mode'] == 'drive':
                values.update(vehicle)
            if old:
                values['vehicle_id'] = old['vehicle_id']
                values.update({key: old[key] for key in ('pickup', 'earliest', 'latest')})
            if request.args.get('vehicle_id'):
                values['vehicle_id'] = request.args['vehicle_id']
        return render_template('travel.html', **data, person=person, old=old, values=values, error=error, admin=admin,
                               back_url=editor_destination(event_id, admin)), status

    @app.route('/events/<event_id>/travel', methods=['GET', 'POST'])
    @member_required
    def travel(event_id):
        return travel_editor(event_id)

    def remove_editor(event_id, admin=False):
        person = store.name(request.values.get('name')) if admin else g.person
        data = store.snapshot(db(), event_id)
        store.require_open(data['event'], admin)
        old = next((r for r in data['records'] if r['name'] == person), None)
        if old is None:
            raise store.UserError('这份登记不存在或已经撤销。', 404)
        if request.method == 'POST':
            store.remove_travel(db(), event_id, person, request.form, admin=admin)
            flash('登记已撤销。', 'success')
            return redirect(editor_destination(event_id, admin), code=303)
        car = next((c for c in data['cars'] if c['id'] == old['vehicle_id']), None)
        return render_template('remove.html', event=data['event'], old=old, car=car, person=person, admin=admin, back_url=editor_destination(event_id, admin))

    @app.route('/events/<event_id>/remove', methods=['GET', 'POST'])
    @member_required
    def remove(event_id):
        return remove_editor(event_id)

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        error = None
        target = next_path(request.values.get('next'), url_for('admin_index'))
        if request.method == 'POST':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            password_ok = check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password)
            if hmac.compare_digest(username.encode(), app.config['ADMIN_USERNAME'].encode()) and password_ok:
                session['admin_version'] = admin_version()
                session['csrf'] = secrets.token_urlsafe(32)
                return redirect(target, code=303)
            error = '账号或密码不正确。'
        return render_template('admin_login.html', error=error, target=target), 401 if error else 200

    @app.post('/admin/logout')
    def admin_logout():
        session.pop('admin_version', None)
        session['csrf'] = secrets.token_urlsafe(32)
        return redirect(url_for('admin_login'), code=303)

    @app.route('/admin')
    @admin_required
    def admin_index():
        return render_template('events.html', events=store.event_list(db()), admin=True)

    @app.route('/admin/events/<event_id>')
    @admin_required
    def admin_event(event_id):
        return render_template('admin_event.html', **store.snapshot(db(), event_id, private=True))

    @app.post('/admin/events/<event_id>/assign')
    @admin_required
    def admin_assign(event_id):
        # The administrator identity comes only from the authenticated session.
        vehicle_id = store.save_travel(db(), event_id, request.form.get('name'),
                                      {'mode': 'ride', 'vehicle_id': request.form.get('vehicle_id'),
                                       'revision': request.form.get('revision', '')}, admin=True)
        session['motion'] = {'event': event_id, 'focus': f'car-{vehicle_id}', 'kind': 'board'}
        flash('人员已安排到指定车辆。', 'success')
        return redirect(url_for('event_detail', event_id=event_id, focus=f'car-{vehicle_id}'), code=303)

    @app.post('/admin/events/<event_id>/release')
    @admin_required
    def admin_release(event_id):
        vehicle_id = store.release_passenger(db(), event_id, g.person, request.form, admin=True)
        flash('乘客已移回等车区，上车需求已保留。', 'success')
        return redirect(url_for('event_detail', event_id=event_id, focus=f'car-{vehicle_id}'), code=303)

    @app.route('/admin/events/<event_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def admin_edit(event_id):
        return edit_event(event_id, True)

    @app.post('/admin/events/<event_id>/toggle')
    @admin_required
    def admin_toggle(event_id):
        store.update_event(db(), event_id, g.person, request.form, admin=True, toggle=True)
        return redirect(editor_destination(event_id, True), code=303)

    @app.route('/admin/events/<event_id>/travel', methods=['GET', 'POST'])
    @admin_required
    def admin_travel(event_id):
        return travel_editor(event_id, True)

    @app.route('/admin/events/<event_id>/remove', methods=['GET', 'POST'])
    @admin_required
    def admin_remove(event_id):
        return remove_editor(event_id, True)

    @app.post('/admin/events/<event_id>/reminders/<int:reminder_id>/resolve')
    @admin_required
    def admin_resolve(event_id, reminder_id):
        store.resolve_reminder(db(), event_id, reminder_id)
        flash('已标记为处理完成。', 'success')
        return redirect(url_for('admin_event', event_id=event_id), code=303)

    @app.errorhandler(store.UserError)
    def user_error(exc):
        return render_template('error.html', message=str(exc)), exc.status

    @app.errorhandler(sqlite3.Error)
    def database_error(exc):
        app.logger.exception('Database operation failed')
        if isinstance(exc, sqlite3.OperationalError) and ('locked' in str(exc) or 'busy' in str(exc)):
            return render_template('error.html', message='当前登记较多，请稍后刷新重试。你的原安排未改变。'), 503
        return render_template('error.html', message='保存数据失败，请联系管理员检查。'), 500

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def http_error(exc):
        messages = {404: '页面不存在，请检查链接。', 413: '提交内容过长，请缩短后重试。'}
        return render_template('error.html', message=messages.get(exc.code, exc.description)), exc.code

    return app
