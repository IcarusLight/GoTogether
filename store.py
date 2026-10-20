"""SQLite storage and the shared travel rules used by public and admin routes."""

from contextlib import contextmanager
from datetime import date, time
from pathlib import Path
import secrets
import sqlite3
import unicodedata


VEHICLE_APPEARANCES = {
    'phantom': '劳斯莱斯幻影', 'tricycle': '农用三蹦子', 'su7': '小米 SU7',
    'v800': '尊界 V800', 'kart': '卡丁车', 'yadea': '雅迪电动车', 'horse-carriage': '宝马马车',
    'wuling': '五菱宏光', 'dayun': '大运卡车', 'mega': '理想 MEGA', 'ct5': '凯迪拉克 CT5 · 黑色',
}
DEFAULT_VEHICLE_APPEARANCE = 'su7'
VEHICLE_COLORS = {
    'su7': {'default': '卡布里蓝', 'sunset-purple': '霞光紫', 'elegant-gray': '雅灰',
            'pearl-white': '珍珠白', 'obsidian-black': '曜石黑'},
    'yadea': {'default': '原版', 'meituan': '美团外卖 · 黄色外卖箱'},
}


def vehicle_image(appearance, color='default'):
    color = color if color in VEHICLE_COLORS.get(appearance, {}) else 'default'
    return f'vehicles/{appearance}/{color}.webp'


class UserError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def connect(path):
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = connect(path)
    try:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version == 0:
            sql = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
            db.executescript('BEGIN IMMEDIATE;\n' + sql + '\nCOMMIT;')
        elif version in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            if sqlite3.sqlite_version_info < (3, 35, 0):
                raise RuntimeError('升级旧数据库需要 SQLite 3.35 或更新版本，请更新 Python 使用的 SQLite 后重试。')
            sql = '\n'.join((Path(__file__).parent / 'migrations' / f'migration_{target}.sql').read_text(encoding='utf-8')
                            for target in range(version + 1, 11))
            db.executescript('BEGIN IMMEDIATE;\n' + sql + '\nCOMMIT;')
        elif version != 10:
            raise RuntimeError('数据库版本不匹配，请使用与数据版本对应的程序。')
    finally:
        db.close()


@contextmanager
def transaction(db, write=True):
    # SQLite serializes writers; capacity is checked after acquiring the write lock.
    db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def text(value, label, limit, required=False):
    value = unicodedata.normalize('NFC', str(value or '')).strip()
    if (required and not value) or len(value) > limit or '\x00' in value:
        raise UserError(f'{label}请填写 1–{limit} 个字符。' if required else f'{label}不能超过 {limit} 个字符。')
    return value


def name(value):
    result = text(value, '姓名', 40, True)
    if any(unicodedata.category(c).startswith('C') for c in result):
        raise UserError('姓名中不能包含控制字符。')
    return result


def event_fields(values):
    title = text(values.get('title'), '活动名称', 80, True)
    raw_date = str(values.get('event_date', ''))
    try:
        day = date.fromisoformat(raw_date).isoformat()
    except ValueError:
        raise UserError('请选择有效的活动日期。') from None
    return title, day, text(values.get('description'), '活动说明', 1000)


def get_event(db, event_id):
    row = db.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if row is None:
        raise UserError('找不到这场活动，请检查活动链接。', 404)
    return dict(row)


def require_editor(event, actor, admin):
    if not admin and event['creator'] != actor:
        raise UserError('只有活动创建者或管理员可以修改活动。', 403)


def require_open(event, admin):
    if not event['is_open'] and not admin:
        raise UserError('登记已关闭，如需调整请联系管理员。', 409)


def create_event(db, actor, values):
    fields = event_fields(values)
    event_id = secrets.token_urlsafe(12)
    with transaction(db):
        db.execute('INSERT INTO events(id, title, event_date, description, creator) VALUES (?, ?, ?, ?, ?)',
                   (event_id, *fields, name(actor)))
    return event_id


def update_event(db, event_id, actor, values, admin=False, toggle=False):
    fields = None if toggle else event_fields(values)
    with transaction(db):
        event = get_event(db, event_id)
        require_editor(event, actor, admin)
        if str(event['version']) != str(values.get('version', '')):
            raise UserError('活动信息已被更新，请刷新页面后再修改。', 409)
        if toggle:
            opened = values.get('is_open')
            if opened not in ('0', '1'):
                raise UserError('无效的登记状态。')
            db.execute('UPDATE events SET is_open = ?, version = version + 1 WHERE id = ?', (int(opened), event_id))
        else:
            db.execute('UPDATE events SET title = ?, event_date = ?, description = ?, version = version + 1 WHERE id = ?',
                       (*fields, event_id))


def event_list(db):
    return [dict(row) for row in db.execute('''
        SELECT e.*, (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS people_count,
        (SELECT COUNT(*) FROM vehicles v WHERE v.event_id = e.id) AS vehicle_count
        FROM events e ORDER BY e.is_open DESC, e.event_date DESC, e.created_at DESC
    ''')]


def snapshot(db, event_id, private=False):
    with transaction(db, write=False):
        event = get_event(db, event_id)
        records = [dict(row) for row in db.execute('SELECT * FROM registrations WHERE event_id = ? ORDER BY name', (event_id,))]
        cars = [dict(row) for row in db.execute('SELECT * FROM vehicles WHERE event_id = ? ORDER BY id', (event_id,))]
        for car in cars:
            car['passengers'] = [r for r in records if r['vehicle_id'] == car['id'] and r['mode'] == 'ride']
            car['remaining'] = car['capacity'] - len(car['passengers'])
        reminders = []
        if private:
            reminders = [dict(row) for row in db.execute('''
                SELECT m.*, r.mode AS current_mode FROM reminders m
                LEFT JOIN registrations r ON r.event_id = m.event_id AND r.name = m.name
                WHERE m.event_id = ? ORDER BY (m.resolved_at IS NOT NULL), m.id DESC
            ''', (event_id,))]
    return {'event': event, 'records': records, 'cars': cars, 'reminders': reminders,
            'waiting': [r for r in records if r['mode'] == 'wait'],
            'remaining': sum(car['remaining'] for car in cars)}


def registration(db, event_id, person):
    row = db.execute('SELECT * FROM registrations WHERE event_id = ? AND name = ?', (event_id, person)).fetchone()
    return dict(row) if row else None


def check_revision(old, values):
    expected = str(values.get('revision', ''))
    actual = old['revision'] if old else ''
    if expected != actual:
        raise UserError('这份登记已发生变化，请刷新页面查看最新安排后再操作。', 409)


def remind(db, event_id, person, reason):
    db.execute('''INSERT INTO reminders(event_id, name, reason) VALUES (?, ?, ?)
        ON CONFLICT(event_id, name) WHERE resolved_at IS NULL
        DO UPDATE SET reason = excluded.reason, created_at = CURRENT_TIMESTAMP''', (event_id, person, reason))


def detach(db, event_id, person, old):
    if old and old['mode'] == 'drive':
        passengers = db.execute("SELECT name FROM registrations WHERE event_id = ? AND vehicle_id = ? AND mode = 'ride'",
                                (event_id, old['vehicle_id'])).fetchall()
        for passenger in passengers:
            db.execute("""UPDATE registrations SET mode = 'wait', vehicle_id = NULL, revision = ?
                WHERE event_id = ? AND name = ?""", (secrets.token_hex(16), event_id, passenger['name']))
        # Riders are detached first so the vehicle cascade only removes its driver.
        db.execute('DELETE FROM vehicles WHERE event_id = ? AND id = ?', (event_id, old['vehicle_id']))
    else:
        db.execute('DELETE FROM registrations WHERE event_id = ? AND name = ?', (event_id, person))


def save_travel(db, event_id, person, values, admin=False):
    person = name(person)
    mode = values.get('mode')
    if mode not in ('drive', 'ride', 'public', 'other', 'wait', 'pending'):
        raise UserError('请选择有效的出行方式。')
    note = text(values.get('note'), '备注', 500)
    vehicle_id = None
    if mode == 'drive':
        appearance = values.get('appearance')
        if appearance is not None and appearance not in VEHICLE_APPEARANCES:
            raise UserError('请选择有效的车辆外观。')
        departure = text(values.get('departure'), '出发点', 100)
        plate = text(values.get('plate'), '车牌', 20)
        try:
            capacity = int(values.get('capacity', ''))
        except (TypeError, ValueError):
            raise UserError('可搭载人数必须是 0–99 之间的整数。') from None
        if not 0 <= capacity <= 99:
            raise UserError('可搭载人数必须是 0–99 之间的整数。')
        departure_time = str(values.get('departure_time', '')).strip()
        if departure_time:
            try:
                departure_time = time.fromisoformat(departure_time).strftime('%H:%M')
            except ValueError:
                raise UserError('请填写有效的出发时间。') from None
    elif mode == 'ride':
        try:
            vehicle_id = int(values.get('vehicle_id', ''))
        except (ValueError, TypeError):
            raise UserError('请选择要搭乘的车辆。') from None

    with transaction(db):
        require_open(get_event(db, event_id), admin)
        old = registration(db, event_id, person)
        check_revision(old, values)
        if 'note' not in values and old:
            note = old['note']
        pickup = text(values.get('pickup', old['pickup'] if old else ''), '上车地点', 100)
        earliest, latest = [str(values.get(key, old[key] if old else '')).strip() for key in ('earliest', 'latest')]
        try:
            earliest, latest = [time.fromisoformat(value).strftime('%H:%M') if value else '' for value in (earliest, latest)]
        except ValueError:
            raise UserError('请填写有效的可选时间。') from None
        if earliest and latest and earliest > latest:
            raise UserError('结束时间不能早于开始时间；只填一项表示一个时间点，两项都留空表示时间灵活。')
        if old and old['mode'] == 'drive' and mode != 'drive' and values.get('confirm_driver') != 'yes':
            raise UserError('更改出行方式会取消你管理的车辆，请勾选确认后再保存。')
        if mode == 'drive':
            previous = (db.execute('SELECT appearance, color FROM vehicles WHERE id = ?',
                                   (old['vehicle_id'],)).fetchone()
                        if old and old['mode'] == 'drive' else None)
            appearance = appearance or (previous['appearance'] if previous else DEFAULT_VEHICLE_APPEARANCE)
            if appearance == 'v800' and values.get('confirm_v800') != 'yes':
                raise UserError('请确认车辆选择声明后，再保存尊界 V800。')
            color = 'default'
            if appearance in VEHICLE_COLORS:
                # Skins share color storage; separate form names keep radio groups independent.
                option_field = 'skin' if appearance == 'yadea' else 'color'
                color = values.get(option_field, previous['color'] if previous and previous['appearance'] == appearance else 'default')
                if color not in VEHICLE_COLORS[appearance]:
                    raise UserError('请选择有效的车辆皮肤。' if appearance == 'yadea' else '请选择有效的车辆颜色。')
        if mode == 'ride':
            car = db.execute('SELECT * FROM vehicles WHERE id = ? AND event_id = ?', (vehicle_id, event_id)).fetchone()
            if car is None:
                raise UserError('这辆车已取消，请重新选择。', 409)
            if car['driver'] == person:
                raise UserError('你已经是这辆车的司机。')
            occupied = db.execute("SELECT COUNT(*) FROM registrations WHERE vehicle_id = ? AND mode = 'ride' AND name <> ?",
                                  (vehicle_id, person)).fetchone()[0]
            if occupied >= car['capacity']:
                raise UserError('这辆车已经满员，原安排已保留，请选择其他车辆。', 409)
        if mode == 'drive' and old and old['mode'] == 'drive':
            vehicle_id = old['vehicle_id']
            occupied = db.execute("SELECT COUNT(*) FROM registrations WHERE vehicle_id = ? AND mode = 'ride'", (vehicle_id,)).fetchone()[0]
            if capacity < occupied:
                raise UserError(f'已有 {occupied} 名乘客，请先协调换车后再减少座位。', 409)
            db.execute('UPDATE vehicles SET capacity = ?, departure = ?, departure_time = ?, plate = ?, note = ?, appearance = ?, color = ? WHERE id = ?',
                       (capacity, departure, departure_time, plate, note, appearance, color, vehicle_id))
            db.execute('DELETE FROM registrations WHERE event_id = ? AND name = ?', (event_id, person))
        else:
            detach(db, event_id, person, old)
            if mode == 'drive':
                vehicle_id = db.execute('INSERT INTO vehicles(event_id, driver, capacity, departure, departure_time, plate, note, appearance, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                        (event_id, person, capacity, departure, departure_time, plate, note,
                                         appearance, color)).lastrowid
        if mode == 'pending':
            remind(db, event_id, person, '本人申请协助安排出行')
        else:
            db.execute('''INSERT INTO registrations(event_id, name, mode, vehicle_id, note, revision, pickup, earliest, latest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (event_id, person, mode, vehicle_id, note, secrets.token_hex(16), pickup, earliest, latest))
    return vehicle_id


def collect_waiter(db, event_id, actor, values):
    person = name(values.get('name'))
    with transaction(db):
        require_open(get_event(db, event_id), False)
        car = db.execute('SELECT * FROM vehicles WHERE event_id = ? AND driver = ?', (event_id, actor)).fetchone()
        if car is None or str(car['id']) != str(values.get('vehicle_id', '')):
            raise UserError('只能把等车的人加入自己当前的车辆。', 403)
        old = registration(db, event_id, person)
        check_revision(old, values)
        if old is None or old['mode'] != 'wait':
            raise UserError('这位同事已离开等车区，请刷新页面。', 409)
        occupied = db.execute("SELECT COUNT(*) FROM registrations WHERE vehicle_id = ? AND mode = 'ride'", (car['id'],)).fetchone()[0]
        if occupied >= car['capacity']:
            raise UserError('你的车已满员，这位同事仍在等车区。', 409)
        db.execute("""UPDATE registrations SET mode = 'ride', vehicle_id = ?, revision = ?
            WHERE event_id = ? AND name = ?""", (car['id'], secrets.token_hex(16), event_id, person))
        return car['id']


def release_passenger(db, event_id, actor, values, admin=False):
    person = name(values.get('name'))
    with transaction(db):
        require_open(get_event(db, event_id), admin)
        car = db.execute('SELECT * FROM vehicles WHERE event_id = ? AND id = ?', (event_id, values.get('vehicle_id', ''))).fetchone()
        if car is None or (not admin and car['driver'] != actor and person != actor):
            raise UserError('找不到可管理的车辆，请刷新页面。' if admin else '只能退出自己乘坐的车辆，或管理自己车辆上的乘客。', 403)
        old = registration(db, event_id, person)
        check_revision(old, values)
        if old is None or old['mode'] != 'ride' or old['vehicle_id'] != car['id']:
            raise UserError('这位同事当前不在指定车辆上，请刷新页面。', 409)
        db.execute("""UPDATE registrations SET mode = 'wait', vehicle_id = NULL, revision = ?
            WHERE event_id = ? AND name = ?""", (secrets.token_hex(16), event_id, person))
        return car['id']


def leave_transport(db, event_id, person, values):
    with transaction(db):
        require_open(get_event(db, event_id), False)
        old = registration(db, event_id, person)
        check_revision(old, values)
        if old is None or old['mode'] not in ('public', 'other') or old['mode'] != values.get('mode'):
            raise UserError('出行方式已变化，请刷新页面后再操作。', 409)
        db.execute("""UPDATE registrations SET mode = 'wait', vehicle_id = NULL, revision = ?
            WHERE event_id = ? AND name = ?""", (secrets.token_hex(16), event_id, person))


def remove_travel(db, event_id, person, values, admin=False):
    with transaction(db):
        require_open(get_event(db, event_id), admin)
        old = registration(db, event_id, person)
        check_revision(old, values)
        if old is None:
            raise UserError('这份登记已经撤销。', 409)
        detach(db, event_id, person, old)


def resolve_reminder(db, event_id, reminder_id):
    with transaction(db):
        get_event(db, event_id)
        cursor = db.execute('UPDATE reminders SET resolved_at = CURRENT_TIMESTAMP WHERE id = ? AND event_id = ? AND resolved_at IS NULL',
                            (reminder_id, event_id))
        if not cursor.rowcount:
            raise UserError('提醒已经处理或不存在，请刷新页面。', 409)
