"""Run explicitly: python -m unittest discover -s tests -v.

Uses temporary databases only; never starts a network service.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sqlite3
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
import store


class TravelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = generate_password_hash('temporary-test-password')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'test.sqlite3')
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-' * 8, 'DATABASE': self.path,
                               'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD_HASH': self.password_hash})
        self.db = store.connect(self.path)
        self.addCleanup(self.db.close)
        self.event = store.create_event(self.db, '创建者', {'title': '部门活动', 'event_date': '2026-10-24'})

    def save(self, name, mode, **fields):
        old = store.registration(self.db, self.event, name)
        values = {'mode': mode, 'revision': old['revision'] if old else '', **fields}
        return store.save_travel(self.db, self.event, name, values)

    def car(self, name='司机', capacity=2):
        return self.save(name, 'drive', capacity=str(capacity), departure='公司南门')

    def login(self, client, name='成员'):
        response = client.get('/identity')
        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as session:
            token = session['csrf']
        response = client.post('/identity', data={'name': name, 'csrf': token})
        self.assertEqual(response.status_code, 303)

    def post(self, client, path, **data):
        with client.session_transaction() as session:
            data['csrf'] = session['csrf']
        return client.post(path, data=data)

    def admin(self, client):
        client.get('/admin/login')
        response = self.post(client, '/admin/login', username='admin', password='temporary-test-password')
        self.assertEqual(response.status_code, 303)

    def test_script_mime_type_ignores_windows_file_association(self):
        client = self.app.test_client()
        with patch('werkzeug.utils.mimetypes.guess_type', return_value=('text/plain', None)):
            with client.get('/static/app.js') as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'text/javascript')
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                self.assertTrue(response.get_data(as_text=True).strip())
        with client.get('/static/missing.js') as response:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.mimetype, 'text/html')

    def test_full_car_keeps_previous_registration_and_vehicle(self):
        occupied = self.car('甲', 1)
        self.save('乘客甲', 'ride', vehicle_id=str(occupied))
        original_car = self.car('乙', 2)
        self.save('乘客乙', 'ride', vehicle_id=str(original_car))
        with self.assertRaises(store.UserError):
            self.save('乘客乙', 'ride', vehicle_id=str(occupied))
        self.assertEqual(store.registration(self.db, self.event, '乘客乙')['vehicle_id'], original_car)
        with self.assertRaises(store.UserError):
            self.save('乙', 'ride', vehicle_id=str(occupied), confirm_driver='yes')
        self.assertEqual(store.registration(self.db, self.event, '乙')['mode'], 'drive')
        self.assertEqual(len(store.snapshot(self.db, self.event)['cars']), 2)

    def test_cancel_driver_returns_passengers_to_waiting(self):
        vehicle = self.car()
        self.save('需要确认的乘客', 'ride', vehicle_id=str(vehicle))
        driver = store.registration(self.db, self.event, '司机')
        store.remove_travel(self.db, self.event, '司机', {'revision': driver['revision']})
        public = store.snapshot(self.db, self.event)
        self.assertEqual([(r['name'], r['mode'], r['pickup']) for r in public['records']], [('需要确认的乘客', 'wait', '')])
        self.assertEqual(public['reminders'], [])
        private = store.snapshot(self.db, self.event, private=True)
        self.assertEqual(private['reminders'], [])
        self.save('需要确认的乘客', 'public')
        self.assertEqual(store.registration(self.db, self.event, '需要确认的乘客')['mode'], 'public')
        self.assertEqual(store.snapshot(self.db, self.event)['waiting'], [])

    def test_capacity_edits_keep_passengers(self):
        vehicle = self.car(capacity=2)
        self.save('甲', 'ride', vehicle_id=str(vehicle))
        self.save('乙', 'ride', vehicle_id=str(vehicle))
        with self.assertRaises(store.UserError):
            self.save('司机', 'drive', capacity='1', departure='新地点')
        self.save('司机', 'drive', capacity='3', departure='新地点')
        car = store.snapshot(self.db, self.event)['cars'][0]
        self.assertEqual(car['departure'], '新地点')
        self.assertEqual(len(car['passengers']), 2)
        self.assertEqual(car['remaining'], 1)

    def test_driver_change_requires_confirmation_and_returns_passengers_to_waiting(self):
        vehicle = self.car()
        self.save('原乘客', 'ride', vehicle_id=str(vehicle))
        with self.assertRaises(store.UserError):
            self.save('司机', 'public')
        self.assertEqual(len(store.snapshot(self.db, self.event)['cars']), 1)
        self.save('司机', 'public', confirm_driver='yes')
        state = store.snapshot(self.db, self.event, private=True)
        self.assertEqual(state['cars'], [])
        self.assertCountEqual([(r['name'], r['mode']) for r in state['records']], [('司机', 'public'), ('原乘客', 'wait')])
        self.assertEqual(state['reminders'], [])

    def test_collect_and_cancel_preserve_pickup_details(self):
        vehicle = self.car()
        self.save('乘客', 'wait', pickup='地铁站 B 口', earliest='08:00', latest='09:30', note='带背包')
        waiting = store.registration(self.db, self.event, '乘客')
        values = {'name': '乘客', 'revision': waiting['revision'], 'vehicle_id': str(vehicle)}
        self.assertEqual(store.collect_waiter(self.db, self.event, '司机', values), vehicle)
        rider = store.registration(self.db, self.event, '乘客')
        self.assertEqual(rider['mode'], 'ride')
        self.assertNotEqual(rider['revision'], waiting['revision'])
        for key in ('pickup', 'earliest', 'latest', 'note'):
            self.assertEqual(rider[key], waiting[key])
        with self.assertRaises(store.UserError):
            store.collect_waiter(self.db, self.event, '司机', values)
        driver = store.registration(self.db, self.event, '司机')
        store.remove_travel(self.db, self.event, '司机', {'revision': driver['revision']})
        returned = store.registration(self.db, self.event, '乘客')
        self.assertEqual(returned['mode'], 'wait')
        self.assertIsNone(returned['vehicle_id'])
        self.assertNotEqual(returned['revision'], rider['revision'])
        for key in ('pickup', 'earliest', 'latest', 'note'):
            self.assertEqual(returned[key], waiting[key])

    def test_waiting_validation_and_self_boarding(self):
        self.save('乘客', 'wait')
        self.assertEqual(store.registration(self.db, self.event, '乘客')['pickup'], '')
        client = self.app.test_client()
        self.login(client, '乘客')
        for earliest, latest in [('08:00', ''), ('', '09:00')]:
            self.save('乘客', 'wait', earliest=earliest, latest=latest)
            saved = store.registration(self.db, self.event, '乘客')
            self.assertEqual((saved['earliest'], saved['latest']), (earliest, latest))
            page = client.get(f'/events/{self.event}').get_data(as_text=True)
            self.assertIn('可选时间：' + (earliest or latest) + '</p>', page)
        for earliest, latest in [('09:00', '08:00'), ('invalid', '09:00')]:
            with self.assertRaises(store.UserError):
                self.save('乘客', 'wait', pickup='南门', earliest=earliest, latest=latest)
        self.save('乘客', 'wait', pickup='南门', note='等车备注', earliest='', latest='')
        vehicle = self.save('司机', 'drive', capacity='2')
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['departure'], '')
        self.save('乘客', 'ride', vehicle_id=str(vehicle))
        rider = store.registration(self.db, self.event, '乘客')
        self.assertEqual((rider['pickup'], rider['note']), ('南门', '等车备注'))

    def test_collect_rejects_other_car_full_car_closed_event_and_changed_record(self):
        vehicle = self.car(capacity=0)
        other_vehicle = self.car('另一司机')
        self.save('乘客', 'wait', pickup='南门')
        waiting = store.registration(self.db, self.event, '乘客')
        values = {'name': '乘客', 'revision': waiting['revision'], 'vehicle_id': str(vehicle)}
        for actor in ('路人', '另一司机', '司机'):
            with self.assertRaises(store.UserError):
                store.collect_waiter(self.db, self.event, actor, values)
        values['vehicle_id'] = str(other_vehicle)
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        with self.assertRaises(store.UserError):
            store.collect_waiter(self.db, self.event, '另一司机', values)
        store.update_event(self.db, self.event, '创建者', {'version': '2', 'is_open': '1'}, toggle=True)
        self.save('乘客', 'public')
        with self.assertRaises(store.UserError):
            store.collect_waiter(self.db, self.event, '另一司机', values)
        self.assertEqual(store.registration(self.db, self.event, '乘客')['mode'], 'public')

    def test_two_drivers_cannot_collect_same_waiter(self):
        vehicles = [(actor, self.car(actor)) for actor in ('司机甲', '司机乙')]
        self.save('乘客', 'wait', pickup='南门')
        waiting = store.registration(self.db, self.event, '乘客')
        ready = Barrier(2)

        def collect(item):
            actor, vehicle = item
            connection = store.connect(self.path)
            try:
                ready.wait(timeout=5)
                try:
                    store.collect_waiter(connection, self.event, actor,
                                         {'name': '乘客', 'vehicle_id': str(vehicle), 'revision': waiting['revision']})
                    return 'saved'
                except store.UserError as exc:
                    return exc.status
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(collect, vehicles)), ['saved', 409])
        self.assertEqual(len(store.snapshot(self.db, self.event)['waiting']), 0)

    def test_waiting_page_and_collect_route(self):
        vehicle = self.car()
        self.save('<乘客>', 'wait', pickup='南门', earliest='08:00', latest='09:00')
        client = self.app.test_client()
        self.login(client, '司机')
        waiting = store.registration(self.db, self.event, '<乘客>')
        page = client.get(f'/events/{self.event}?focus=wait').get_data(as_text=True)
        self.assertIn('&lt;乘客&gt;', page)
        self.assertIn('data-pickup-target', page)
        self.assertIn('接到我的车上', page)
        self.assertIn('08:00–09:00', page)
        route = f'/events/{self.event}/collect'
        self.assertEqual(client.post(route).status_code, 400)
        response = self.post(client, route, name='<乘客>', vehicle_id=str(vehicle), revision=waiting['revision'])
        self.assertEqual(response.status_code, 303)
        self.assertEqual(store.registration(self.db, self.event, '<乘客>')['mode'], 'ride')

    def test_driver_releases_one_passenger_and_preserves_demand(self):
        vehicle = self.car()
        self.save('乘客甲', 'ride', vehicle_id=str(vehicle), pickup='南门', earliest='08:00', note='带背包')
        self.save('乘客乙', 'ride', vehicle_id=str(vehicle))
        rider = store.registration(self.db, self.event, '乘客甲')
        other = store.registration(self.db, self.event, '乘客乙')
        driver = store.registration(self.db, self.event, '司机')
        client = self.app.test_client()
        self.login(client, '司机')
        route = f'/events/{self.event}/release'
        self.assertIn(route, client.get(f'/events/{self.event}').get_data(as_text=True))
        self.assertEqual(client.post(route).status_code, 400)
        values = {'name': '乘客甲', 'vehicle_id': str(vehicle), 'revision': rider['revision']}
        response = self.post(client, route, **values)
        self.assertEqual(response.status_code, 303)
        returned = store.registration(self.db, self.event, '乘客甲')
        self.assertEqual(returned['mode'], 'wait')
        self.assertIsNone(returned['vehicle_id'])
        self.assertNotEqual(returned['revision'], rider['revision'])
        for key in ('pickup', 'earliest', 'latest', 'note'):
            self.assertEqual(returned[key], rider[key])
        self.assertEqual(store.registration(self.db, self.event, '乘客乙'), other)
        self.assertEqual(store.registration(self.db, self.event, '司机'), driver)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['remaining'], 1)
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        self.login(client, '乘客乙')
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        self.assertIn('退出车辆', page)
        self.assertEqual(page.count(f'action="{route}"'), 1)

    def test_passenger_can_leave_only_their_own_current_ride(self):
        vehicle = self.car()
        self.save('乘客甲', 'ride', vehicle_id=str(vehicle), pickup='南门', earliest='08:00', note='带背包')
        self.save('乘客乙', 'ride', vehicle_id=str(vehicle))
        rider = store.registration(self.db, self.event, '乘客甲')
        other = store.registration(self.db, self.event, '乘客乙')
        client = self.app.test_client()
        self.login(client, '乘客甲')
        route = f'/events/{self.event}/release'
        self.assertEqual(client.post(route).status_code, 400)
        self.assertEqual(self.post(client, route, name='乘客乙', vehicle_id=str(vehicle), revision=other['revision']).status_code, 403)
        values = {'name': '乘客甲', 'vehicle_id': str(vehicle), 'revision': rider['revision']}
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        self.assertNotIn('退出车辆</button>', client.get(f'/events/{self.event}').get_data(as_text=True))
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        store.update_event(self.db, self.event, '创建者', {'version': '2', 'is_open': '1'}, toggle=True)
        response = self.post(client, route, **values)
        self.assertEqual(response.status_code, 303)
        self.assertIn('focus=wait', response.location)
        waiting = store.registration(self.db, self.event, '乘客甲')
        self.assertEqual(waiting['mode'], 'wait')
        self.assertIsNone(waiting['vehicle_id'])
        for key in ('pickup', 'earliest', 'latest', 'note'):
            self.assertEqual(waiting[key], rider[key])
        self.assertEqual(store.registration(self.db, self.event, '乘客乙'), other)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['remaining'], 1)
        self.assertEqual(self.post(client, route, **values).status_code, 409)

    def test_release_rejects_wrong_owner_vehicle_event_and_stale_record(self):
        vehicle = self.car()
        another = self.car('另一司机')
        self.save('乘客', 'ride', vehicle_id=str(vehicle))
        rider = store.registration(self.db, self.event, '乘客')
        values = {'name': '乘客', 'vehicle_id': str(vehicle), 'revision': rider['revision']}
        client = self.app.test_client()
        route = f'/events/{self.event}/release'
        self.login(client, '另一司机')
        self.assertEqual(self.post(client, route, **values).status_code, 403)
        self.assertEqual(self.post(client, route, **{**values, 'vehicle_id': str(another)}).status_code, 409)
        self.login(client, '司机')
        self.assertEqual(self.post(client, route, **{**values, 'vehicle_id': str(another)}).status_code, 403)
        second = store.create_event(self.db, '司机', {'title': '另一个活动', 'event_date': '2026-10-25'})
        self.assertEqual(self.post(client, f'/events/{second}/release', **values).status_code, 403)
        driver = store.registration(self.db, self.event, '司机')
        self.assertEqual(self.post(client, route, name='司机', vehicle_id=str(vehicle), revision=driver['revision']).status_code, 409)
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '乘客'), rider)
        store.update_event(self.db, self.event, '创建者', {'version': '2', 'is_open': '1'}, toggle=True)
        self.save('乘客', 'ride', vehicle_id=str(another))
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '乘客')['vehicle_id'], another)

    def test_admin_scene_without_member_identity_manages_closed_event(self):
        first = self.car('司机甲', 2)
        second = self.car('司机乙', 2)
        self.save('等车人', 'wait', pickup='南门', earliest='08:00', note='带背包')
        self.save('原乘客', 'ride', vehicle_id=str(first))
        self.save('公交乘客', 'public')
        self.save('步行乘客', 'other')
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        client = self.app.test_client()
        self.admin(client)
        with client.session_transaction() as session:
            self.assertNotIn('person', session)
        response = client.get(f'/events/{self.event}')
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('管理员调度模式', page)
        self.assertIn(f'data-pickup-target="{first}"', page)
        self.assertIn(f'data-pickup-target="{second}"', page)
        self.assertIn('管理车辆 / 司机', page)
        for person in ('等车人', '原乘客', '公交乘客', '步行乘客'):
            record = store.registration(self.db, self.event, person)
            self.assertIn(f'id="pickup-{record["revision"]}"', page)
        for person, vehicle in [('等车人', first), ('原乘客', second), ('公交乘客', first), ('步行乘客', second)]:
            record = store.registration(self.db, self.event, person)
            result = self.post(client, f'/admin/events/{self.event}/assign', name=person,
                               vehicle_id=str(vehicle), revision=record['revision'])
            self.assertEqual(result.status_code, 303)
            self.assertIn(f'/events/{self.event}?focus=car-', result.location)
            self.assertEqual(store.registration(self.db, self.event, person)['vehicle_id'], vehicle)
        rider = store.registration(self.db, self.event, '等车人')
        values = {'name': '等车人', 'vehicle_id': str(first), 'revision': rider['revision']}
        result = self.post(client, f'/admin/events/{self.event}/release', **values)
        self.assertEqual(result.status_code, 303)
        self.assertEqual(self.post(client, f'/admin/events/{self.event}/release', **values).status_code, 409)
        waiting = store.registration(self.db, self.event, '等车人')
        self.assertEqual((waiting['mode'], waiting['pickup'], waiting['earliest'], waiting['note']),
                         ('wait', '南门', '08:00', '带背包'))

    def test_admin_scene_routes_require_admin_and_preserve_records_on_conflict(self):
        vehicle = self.car(capacity=1)
        self.save('原乘客', 'ride', vehicle_id=str(vehicle))
        self.save('等车人', 'wait')
        old = store.registration(self.db, self.event, '等车人')
        values = {'name': '等车人', 'vehicle_id': str(vehicle), 'revision': old['revision']}
        client = self.app.test_client()
        self.login(client, 'admin')
        for action in ('assign', 'release'):
            result = self.post(client, f'/admin/events/{self.event}/{action}', **values, admin='true')
            self.assertEqual(result.status_code, 302)
            self.assertIn('/admin/login', result.location)
        self.assertNotIn('管理员调度模式', client.get(f'/events/{self.event}').get_data(as_text=True))
        self.admin(client)
        route = f'/admin/events/{self.event}/assign'
        self.assertEqual(client.post(route, data=values).status_code, 400)
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '等车人'), old)
        second = store.create_event(self.db, '创建者', {'title': '别的活动', 'event_date': '2026-10-25'})
        foreign_car = store.save_travel(self.db, second, '外场司机', {'mode': 'drive', 'capacity': '2'})
        self.assertEqual(self.post(client, route, **{**values, 'vehicle_id': str(foreign_car)}).status_code, 409)
        self.assertEqual(self.post(client, f'/admin/events/{self.event}/release',
                                   **{**values, 'vehicle_id': str(foreign_car)}).status_code, 403)
        self.save('等车人', 'other')
        self.assertEqual(self.post(client, route, **values).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '等车人')['mode'], 'other')

    def test_admin_scene_editors_return_to_scene(self):
        self.car()
        client = self.app.test_client()
        self.admin(client)
        scene = f'/events/{self.event}'
        for suffix in ('travel?name=司机&scene=1', 'remove?name=司机&scene=1', 'edit?scene=1'):
            response = client.get(f'/admin/events/{self.event}/{suffix}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(f'href="{scene}"', response.get_data(as_text=True))
        response = self.post(client, f'/admin/events/{self.event}/travel', scene='1', name='新人员',
                             mode='wait', revision='')
        self.assertEqual(response.location, scene)
        response = self.post(client, f'/admin/events/{self.event}/edit', scene='1', version='1',
                             title='调整后的活动', event_date='2026-10-25')
        self.assertEqual(response.location, scene)
        response = self.post(client, f'/admin/events/{self.event}/toggle', scene='1', version='2', is_open='0')
        self.assertEqual(response.location, scene)
        driver = store.registration(self.db, self.event, '司机')
        response = self.post(client, f'/admin/events/{self.event}/remove', scene='1', name='司机', revision=driver['revision'])
        self.assertEqual(response.location, scene)
        self.post(client, '/admin/logout')
        self.assertIn('/identity', client.get(scene).location)
        self.assertIn('/admin/login', self.post(client, f'/admin/events/{self.event}/assign').location)

    def test_version_one_migration_preserves_data_and_allows_return_to_waiting(self):
        path = str(Path(self.temp.name) / 'legacy.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        legacy.executescript((Path(__file__).parent / 'fixtures' / 'schema_v1.sql').read_text(encoding='utf-8'))
        legacy.execute("INSERT INTO events(id, title, event_date, creator) VALUES ('old', '原活动', '2026-10-24', '司机')")
        legacy.execute("INSERT INTO vehicles(id, event_id, driver, capacity, departure) VALUES (1, 'old', '司机', 2, '公司')")
        legacy.executemany('INSERT INTO registrations(event_id, name, mode, vehicle_id, note, revision) VALUES (?, ?, ?, ?, ?, ?)',
                           [('old', '司机', 'drive', 1, '', 'driver-revision'), ('old', '乘客', 'ride', 1, '原备注', 'rider-revision')])
        store.remind(legacy, 'old', '后台提醒', '已有提醒')
        store.initialize(path)
        store.initialize(path)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])
        before = store.snapshot(legacy, 'old', private=True)
        self.assertEqual(before['cars'][0]['remaining'], 1)
        self.assertEqual(before['cars'][0]['appearance'], 'su7')
        self.assertEqual(before['reminders'][0]['name'], '后台提醒')
        rider = store.registration(legacy, 'old', '乘客')
        self.assertEqual((rider['note'], rider['revision'], rider['pickup']), ('原备注', 'rider-revision', ''))
        store.remove_travel(legacy, 'old', '司机', {'revision': 'driver-revision'})
        self.assertEqual(store.registration(legacy, 'old', '乘客')['mode'], 'wait')
        store.save_travel(legacy, 'old', '乘客', {'mode': 'wait', 'revision': store.registration(legacy, 'old', '乘客')['revision']})

    def test_version_two_migration_preserves_vehicle_and_waiting_details(self):
        path = str(Path(self.temp.name) / 'version-two.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        legacy.executescript((root / 'tests/fixtures/schema_v1.sql').read_text(encoding='utf-8'))
        legacy.executescript((root / 'migrations/migration_2.sql').read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        legacy.execute('INSERT INTO vehicles(event_id, driver, capacity, departure) VALUES (?, ?, 2, ?)', (event, '司机', '南门'))
        legacy.execute("INSERT INTO registrations(event_id, name, mode, revision, pickup, earliest) VALUES (?, '等车人', 'wait', 'old', '北门', '08:30')", (event,))
        store.initialize(path)
        store.initialize(path)
        state = store.snapshot(legacy, event)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual((state['cars'][0]['departure'], state['cars'][0]['plate']), ('南门', ''))
        self.assertEqual(state['cars'][0]['appearance'], 'su7')
        self.assertEqual((state['waiting'][0]['pickup'], state['waiting'][0]['earliest']), ('北门', '08:30'))

    def test_version_three_migration_preserves_car_and_passengers(self):
        path = str(Path(self.temp.name) / 'version-three.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        for script in ('tests/fixtures/schema_v1.sql', 'migrations/migration_2.sql', 'migrations/migration_3.sql'):
            legacy.executescript((root / script).read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        vehicle = legacy.execute('INSERT INTO vehicles(event_id, driver, capacity, departure, plate) VALUES (?, ?, 2, ?, ?)',
                                 (event, '司机', '南门', '粤B12345')).lastrowid
        legacy.executemany('INSERT INTO registrations(event_id, name, mode, vehicle_id, revision) VALUES (?, ?, ?, ?, ?)',
                           [(event, '司机', 'drive', vehicle, 'driver'), (event, '乘客', 'ride', vehicle, 'rider')])
        store.initialize(path)
        store.initialize(path)
        car = store.snapshot(legacy, event)['cars'][0]
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual((car['id'], car['plate'], car['appearance'], car['remaining']), (vehicle, '粤B12345', 'su7', 1))
        self.assertEqual(car['passengers'][0]['name'], '乘客')
        self.assertEqual(store.registration(legacy, event, '司机')['revision'], 'driver')

    def test_version_four_migration_preserves_vehicles_and_accepts_new_appearances(self):
        path = str(Path(self.temp.name) / 'version-four.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        for script in ('tests/fixtures/schema_v1.sql', 'migrations/migration_2.sql',
                       'migrations/migration_3.sql', 'migrations/migration_4.sql'):
            legacy.executescript((root / script).read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        for appearance in ('phantom', 'tricycle', 'su7'):
            vehicle = legacy.execute('''INSERT INTO vehicles(event_id, driver, capacity, departure, plate, appearance)
                VALUES (?, ?, 2, '南门', '粤B12345', ?)''', (event, appearance, appearance)).lastrowid
            legacy.execute("INSERT INTO registrations(event_id, name, mode, vehicle_id, revision) VALUES (?, ?, 'drive', ?, ?)",
                           (event, appearance, vehicle, appearance))
            store.save_travel(legacy, event, appearance + '乘客',
                              {'mode': 'ride', 'revision': '', 'vehicle_id': str(vehicle), 'note': '原备注'})
        before = store.snapshot(legacy, event)
        with patch('store.sqlite3.sqlite_version_info', (3, 34, 0)):
            with self.assertRaisesRegex(RuntimeError, 'SQLite 3.35'):
                store.initialize(path)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 4)
        self.assertEqual(store.snapshot(legacy, event), before)
        store.initialize(path)
        store.initialize(path)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        for car in before['cars']:
            car['color'] = 'default'
        self.assertEqual(store.snapshot(legacy, event), before)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])
        for appearance in ('v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega', 'ct5'):
            with self.subTest(appearance=appearance):
                vehicle = store.save_travel(legacy, event, appearance,
                                           {'mode': 'drive', 'revision': '', 'capacity': '1', 'appearance': appearance,
                                            'confirm_v800': 'yes' if appearance == 'v800' else ''})
                self.assertGreater(vehicle, before['cars'][-1]['id'])
                self.assertEqual(legacy.execute('SELECT appearance FROM vehicles WHERE id = ?', (vehicle,)).fetchone()[0], appearance)
        legacy.execute("INSERT INTO vehicles(event_id, driver, capacity, departure) VALUES (?, '默认车型', 1, '')", (event,))
        self.assertEqual(legacy.execute("SELECT appearance FROM vehicles WHERE driver = '默认车型'").fetchone()[0], 'su7')
        with self.assertRaises(sqlite3.IntegrityError):
            legacy.execute("UPDATE vehicles SET appearance = 'invalid'")
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_vehicle_appearance_create_edit_admin_and_sync(self):
        client = self.app.test_client()
        self.login(client, '司机')
        route = f'/events/{self.event}/travel'
        form = client.get(route + '?mode=drive').get_data(as_text=True)
        for appearance in store.VEHICLE_APPEARANCES:
            self.assertIn(f'value="{appearance}"', form)
            self.assertIn('/static/' + store.vehicle_image(appearance), form)
        self.assertIn('value="su7" checked', form)
        response = self.post(client, route, mode='drive', revision='', capacity='2', appearance='ct5')
        self.assertEqual(response.status_code, 303)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['appearance'], 'ct5')
        vehicle = store.registration(self.db, self.event, '司机')['vehicle_id']
        self.save('乘客', 'ride', vehicle_id=str(vehicle))
        for appearance in ('phantom', 'tricycle', 'v800', 'kart', 'yadea', 'horse-carriage', 'wuling', 'dayun', 'mega', 'ct5', 'su7'):
            params = self.sync_params(client)
            revision = store.registration(self.db, self.event, '司机')['revision']
            response = self.post(client, route, mode='drive', revision=revision, capacity='2', appearance=appearance,
                                 confirm_v800='yes' if appearance == 'v800' else '')
            self.assertEqual(response.status_code, 303)
            car = store.snapshot(self.db, self.event)['cars'][0]
            self.assertEqual((car['id'], car['appearance'], car['remaining']), (vehicle, appearance, 1))
            self.assertEqual(car['passengers'][0]['name'], '乘客')
            self.assertIn(f'value="{appearance}" checked', client.get(route).get_data(as_text=True))
            update = client.get(f'/events/{self.event}/sync', query_string=params).get_json()
            self.assertIn('/static/' + store.vehicle_image(appearance), update['html'])
        revision = store.registration(self.db, self.event, '司机')['revision']
        response = self.post(client, route, mode='drive', revision=revision, capacity='2', appearance='../invalid')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['appearance'], 'su7')
        self.assertEqual(store.registration(self.db, self.event, '司机')['revision'], revision)
        self.admin(client)
        response = self.post(client, f'/admin/events/{self.event}/travel', name='司机', mode='drive',
                             revision=revision, capacity='2', appearance='ct5')
        self.assertEqual(response.status_code, 303)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['appearance'], 'ct5')
        # An old form without the new field must retain the selected appearance.
        self.save('司机', 'drive', capacity='2')
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['appearance'], 'ct5')

    def test_su7_colors_preserve_passengers_and_sync_for_members_and_admin(self):
        vehicle = self.car()
        self.save('乘客', 'ride', vehicle_id=str(vehicle))
        client = self.app.test_client()
        self.login(client, '司机')
        route = f'/events/{self.event}/travel'
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['color'], 'default')
        for color, label in store.VEHICLE_COLORS['su7'].items():
            params = self.sync_params(client)
            revision = store.registration(self.db, self.event, '司机')['revision']
            response = self.post(client, route, mode='drive', revision=revision, capacity='2', appearance='su7', color=color)
            self.assertEqual(response.status_code, 303)
            car = store.snapshot(self.db, self.event)['cars'][0]
            self.assertEqual((car['id'], car['color'], car['remaining']), (vehicle, color, 1))
            self.assertEqual(car['passengers'][0]['name'], '乘客')
            self.assertIn(f'value="{color}" data-color-image="/static/vehicles/su7/{color}.webp" checked',
                          client.get(route).get_data(as_text=True))
            html = client.get(f'/events/{self.event}/sync', query_string=params).get_json()['html']
            self.assertIn(f'/static/vehicles/su7/{color}.webp', html)
            self.assertIn(label, html)
        before = store.snapshot(self.db, self.event)
        with self.assertRaisesRegex(store.UserError, '颜色'):
            self.save('司机', 'drive', capacity='2', color='../invalid')
        self.assertEqual(store.snapshot(self.db, self.event), before)
        self.save('司机', 'drive', capacity='2')  # An old form retains the selected color.
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['color'], 'obsidian-black')
        self.admin(client)
        revision = store.registration(self.db, self.event, '司机')['revision']
        response = self.post(client, f'/admin/events/{self.event}/travel', name='司机', mode='drive',
                             revision=revision, capacity='2', appearance='su7', color='sunset-purple')
        self.assertEqual(response.status_code, 303)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['color'], 'sunset-purple')
        self.save('司机', 'drive', capacity='2', appearance='kart')
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['color'], 'default')
        self.save('司机', 'drive', capacity='2', appearance='su7')
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['color'], 'default')

    def test_v800_requires_confirmation_for_member_and_admin(self):
        for admin in (False, True):
            with self.subTest(admin=admin):
                person = '管理员登记司机' if admin else '普通司机'
                client = self.app.test_client()
                if admin:
                    self.admin(client)
                else:
                    self.login(client, person)
                route = f'/admin/events/{self.event}/travel' if admin else f'/events/{self.event}/travel'
                fields = {'name': person, 'mode': 'drive', 'revision': '', 'capacity': '2', 'appearance': 'v800'}
                before = store.snapshot(self.db, self.event)
                for consent in ('', 'no'):
                    response = self.post(client, route, **fields, confirm_v800=consent)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(store.snapshot(self.db, self.event), before)
                response = self.post(client, route, **fields, confirm_v800='yes')
                self.assertEqual(response.status_code, 303)
                vehicle = store.registration(self.db, self.event, person)['vehicle_id']
                self.save(person + '乘客', 'ride', vehicle_id=str(vehicle))
                before = store.snapshot(self.db, self.event)
                with self.assertRaisesRegex(store.UserError, '车辆选择声明'):
                    self.save(person, 'drive', capacity='2')
                self.assertEqual(store.snapshot(self.db, self.event), before)
                self.assertEqual(self.save(person, 'drive', capacity='2', confirm_v800='yes'), vehicle)
                self.save(person, 'drive', capacity='2', appearance='su7')
                before = store.snapshot(self.db, self.event)
                with self.assertRaisesRegex(store.UserError, '车辆选择声明'):
                    self.save(person, 'drive', capacity='2', appearance='v800')
                self.assertEqual(store.snapshot(self.db, self.event), before)
                self.assertEqual(self.save(person, 'drive', capacity='2', appearance='v800', confirm_v800='yes'), vehicle)
                self.assertEqual(store.registration(self.db, self.event, person + '乘客')['vehicle_id'], vehicle)

    def test_version_five_color_migration_preserves_existing_arrangements(self):
        path = str(Path(self.temp.name) / 'version-five.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        for script in ('tests/fixtures/schema_v1.sql', 'migrations/migration_2.sql', 'migrations/migration_3.sql',
                       'migrations/migration_4.sql', 'migrations/migration_5.sql'):
            legacy.executescript((root / script).read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        for appearance in ('phantom', 'tricycle', 'su7', 'v800', 'kart', 'yadea', 'horse-carriage'):
            vehicle = legacy.execute('''INSERT INTO vehicles(event_id, driver, capacity, departure, appearance)
                VALUES (?, ?, 2, '南门', ?)''', (event, appearance, appearance)).lastrowid
            legacy.execute("INSERT INTO registrations(event_id, name, mode, vehicle_id, revision) VALUES (?, ?, 'drive', ?, ?)",
                           (event, appearance, vehicle, appearance))
            legacy.execute("INSERT INTO registrations(event_id, name, mode, vehicle_id, revision) VALUES (?, ?, 'ride', ?, ?)",
                           (event, appearance + '乘客', vehicle, appearance + '-rider'))
        before = store.snapshot(legacy, event)
        store.initialize(path)
        store.initialize(path)
        for car in before['cars']:
            car['color'] = 'default'
        self.assertEqual(store.snapshot(legacy, event), before)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_version_eight_migration_preserves_color_and_passengers_and_accepts_mega(self):
        path = str(Path(self.temp.name) / 'version-eight.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        for script in ('tests/fixtures/schema_v1.sql', 'migrations/migration_2.sql', 'migrations/migration_3.sql',
                       'migrations/migration_4.sql', 'migrations/migration_5.sql', 'migrations/migration_6.sql',
                       'migrations/migration_7.sql', 'migrations/migration_8.sql'):
            legacy.executescript((root / script).read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        vehicle = store.save_travel(legacy, event, '司机', {'mode': 'drive', 'revision': '', 'capacity': '2',
                                                        'appearance': 'su7', 'color': 'sunset-purple'})
        store.save_travel(legacy, event, '乘客', {'mode': 'ride', 'revision': '', 'vehicle_id': str(vehicle)})
        before = store.snapshot(legacy, event)
        store.initialize(path)
        store.initialize(path)
        self.assertEqual(store.snapshot(legacy, event), before)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])
        revision = store.registration(legacy, event, '司机')['revision']
        self.assertEqual(store.save_travel(legacy, event, '司机', {'mode': 'drive', 'revision': revision,
                         'capacity': '2', 'appearance': 'mega'}), vehicle)
        self.assertEqual(store.snapshot(legacy, event)['cars'][0]['appearance'], 'mega')
        self.assertEqual(store.registration(legacy, event, '乘客')['vehicle_id'], vehicle)

    def test_version_nine_migration_preserves_arrangements_and_accepts_ct5(self):
        path = str(Path(self.temp.name) / 'version-nine.sqlite3')
        legacy = store.connect(path)
        self.addCleanup(legacy.close)
        root = Path(__file__).resolve().parent.parent
        legacy.executescript((root / 'tests/fixtures/schema_v1.sql').read_text(encoding='utf-8'))
        for version in range(2, 10):
            legacy.executescript((root / 'migrations' / f'migration_{version}.sql').read_text(encoding='utf-8'))
        event = store.create_event(legacy, '司机', {'title': '旧活动', 'event_date': '2026-10-24'})
        vehicle = store.save_travel(legacy, event, '司机', {'mode': 'drive', 'revision': '', 'capacity': '2',
                                                        'appearance': 'su7', 'color': 'sunset-purple', 'plate': '粤B12345'})
        store.save_travel(legacy, event, '乘客', {'mode': 'ride', 'revision': '', 'vehicle_id': str(vehicle)})
        before = store.snapshot(legacy, event, private=True)
        store.initialize(path)
        store.initialize(path)
        self.assertEqual(store.snapshot(legacy, event, private=True), before)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 10)
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])
        new_vehicle = store.save_travel(legacy, event, 'CT5 司机', {'mode': 'drive', 'revision': '',
                                       'capacity': '2', 'appearance': 'ct5'})
        self.assertGreater(new_vehicle, vehicle)
        self.assertEqual(legacy.execute('SELECT appearance, color FROM vehicles WHERE id = ?',
                                       (new_vehicle,)).fetchone()[:], ('ct5', 'default'))
        revision = store.registration(legacy, event, '司机')['revision']
        self.assertEqual(store.save_travel(legacy, event, '司机', {'mode': 'drive', 'revision': revision,
                         'capacity': '2', 'appearance': 'ct5', 'plate': '粤B12345'}), vehicle)
        self.assertEqual(store.registration(legacy, event, '乘客')['vehicle_id'], vehicle)
        with self.assertRaises(sqlite3.IntegrityError):
            legacy.execute("UPDATE vehicles SET appearance = 'invalid'")
        self.assertEqual(legacy.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_optional_plate_round_trip_and_escaping(self):
        self.car()
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['plate'], '')
        client = self.app.test_client()
        self.login(client, '司机')
        revision = store.registration(self.db, self.event, '司机')['revision']
        result = self.post(client, f'/events/{self.event}/travel', mode='drive', revision=revision, capacity='2', plate=' 粤B12345 ')
        self.assertEqual(result.status_code, 303)
        self.assertEqual(store.snapshot(self.db, self.event)['cars'][0]['plate'], '粤B12345')
        self.assertIn('value="粤B12345"', client.get(f'/events/{self.event}/travel').get_data(as_text=True))
        with self.assertRaises(store.UserError):
            self.save('司机', 'drive', capacity='2', plate='A' * 21)
        self.save('司机', 'drive', capacity='2', plate='<b>车牌</b>')
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        self.assertIn('&lt;b&gt;车牌&lt;/b&gt;', page)
        self.assertNotIn('<b>车牌</b>', page)

    def test_public_and_other_quick_exit_preserves_details_and_only_changes_self(self):
        client = self.app.test_client()
        self.login(client, '本人')
        self.save('他人', 'public')
        for mode, label in [('public', '退出公共交通'), ('other', '退出自由出行')]:
            with self.subTest(mode=mode):
                self.save('本人', mode, pickup='南门', earliest='08:30', note='带行李')
                old = store.registration(self.db, self.event, '本人')
                self.assertIn(label, client.get(f'/events/{self.event}').get_data(as_text=True))
                result = self.post(client, f'/events/{self.event}/leave-mode', mode=mode, revision=old['revision'], name='他人')
                self.assertEqual(result.status_code, 303)
                current = store.registration(self.db, self.event, '本人')
                self.assertEqual((current['mode'], current['pickup'], current['earliest'], current['note']), ('wait', '南门', '08:30', '带行李'))
                self.assertEqual(store.registration(self.db, self.event, '他人')['mode'], 'public')
                self.assertEqual(self.post(client, f'/events/{self.event}/leave-mode', mode=mode, revision=old['revision']).status_code, 409)

    def test_quick_exit_rejects_changed_mode_closed_event_and_missing_csrf(self):
        client = self.app.test_client()
        self.login(client)
        self.save('成员', 'public')
        old = store.registration(self.db, self.event, '成员')
        route = f'/events/{self.event}/leave-mode'
        self.assertEqual(client.post(route, data={'mode': 'public', 'revision': old['revision']}).status_code, 400)
        self.assertEqual(self.post(client, route, mode='other', revision=old['revision']).status_code, 409)
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        self.assertEqual(self.post(client, route, mode='public', revision=old['revision']).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '成员')['mode'], 'public')

    def sync_params(self, client):
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        return {key: re.search(fr'data-{key}="([^"]+)"', page).group(1) for key in ('viewer', 'revision')}

    def test_sync_returns_only_changes_without_private_reminders_or_session_effects(self):
        client = self.app.test_client()
        self.login(client)
        params = self.sync_params(client)
        route = f'/events/{self.event}/sync'
        self.assertEqual(client.get(route, query_string=params).get_json(), {'revision': params['revision']})
        self.save('后台专用姓名', 'pending')
        self.assertNotIn('html', client.get(route, query_string=params).get_json())
        self.save('司机', 'drive', capacity='2', plate='粤B12345')
        with client.session_transaction() as session:
            session['motion'] = {'event': self.event, 'kind': 'board', 'focus': 'public'}
            session['_flashes'] = [('success', '待展示消息')]
        result = client.get(route, query_string=params)
        self.assertEqual(result.status_code, 200)
        update = result.get_json()
        self.assertNotEqual(update['revision'], params['revision'])
        self.assertIn('粤B12345', update['html'])
        for excluded in ('<html', '<script', '后台专用姓名', '待展示消息'):
            self.assertNotIn(excluded, update['html'])
        with client.session_transaction() as session:
            self.assertEqual(session['motion']['kind'], 'board')
            self.assertEqual(session['_flashes'], [('success', '待展示消息')])

    def test_sync_checks_identity_and_supports_admin_without_member_name(self):
        client = self.app.test_client()
        route = f'/events/{self.event}/sync'
        self.assertEqual(client.get(route).status_code, 401)
        self.admin(client)
        params = self.sync_params(client)
        self.assertEqual(client.get(route, query_string=params).status_code, 200)
        self.post(client, '/admin/logout')
        self.assertEqual(client.get(route, query_string=params).status_code, 401)
        self.login(client, '甲')
        params = self.sync_params(client)
        self.login(client, '乙')
        self.assertEqual(client.get(route, query_string=params).status_code, 409)

    def test_released_passenger_can_drag_self_to_another_car(self):
        original = self.car('原司机')
        target = self.car('新司机', 1)
        full = self.car('满员司机', 0)
        self.save('本人', 'ride', vehicle_id=str(original), pickup='北门', earliest='08:30', note='带行李')
        self.save('别人', 'wait')
        client = self.app.test_client()
        self.login(client, '本人')
        old = store.registration(self.db, self.event, '本人')
        result = self.post(client, f'/events/{self.event}/release', name='本人', vehicle_id=str(original), revision=old['revision'])
        self.assertEqual(result.status_code, 303)
        waiting = store.registration(self.db, self.event, '本人')
        other = store.registration(self.db, self.event, '别人')
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        self.assertIn(f'draggable="true" data-pickup-form="pickup-{waiting["revision"]}"', page)
        self.assertNotIn(f'data-pickup-form="pickup-{other["revision"]}"', page)
        self.assertIn(f'data-pickup-target="{target}"', page)
        self.assertNotIn(f'data-pickup-target="{full}"', page)
        form = re.search(fr'<form id="pickup-{waiting["revision"]}"[^>]*action="([^"]+)"[^>]*>(.*?)</form>', page, re.S)
        self.assertIsNotNone(form)
        fields = dict(re.findall(r'<input[^>]*name="([^"]+)" value="([^"]*)"', form.group(2)))
        self.assertIn(f'<option value="{target}">', form.group(2))
        self.assertNotIn(f'<option value="{full}">', form.group(2))
        # Drag-and-drop sets the select value and submits this same rendered form.
        fields.update(vehicle_id=str(target), name='别人')
        result = client.post(form.group(1), data=fields)
        self.assertEqual(result.status_code, 303)
        current = store.registration(self.db, self.event, '本人')
        self.assertEqual((current['mode'], current['vehicle_id'], current['pickup'], current['earliest'], current['note']),
                         ('ride', target, '北门', '08:30', '带行李'))
        self.assertEqual(store.registration(self.db, self.event, '别人'), other)
        self.assertEqual(client.post(form.group(1), data=fields).status_code, 409)
        # The last seat was occupied after another waiting member loaded the scene.
        self.login(client, '别人')
        self.assertEqual(self.post(client, form.group(1), mode='ride', vehicle_id=str(target), revision=other['revision']).status_code, 409)
        self.assertEqual(store.registration(self.db, self.event, '别人'), other)
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        closed = client.get(f'/events/{self.event}').get_data(as_text=True)
        self.assertNotIn('draggable="true"', closed)
        self.assertNotIn('data-pickup-target=', closed)
        self.assertEqual(self.post(client, form.group(1), mode='ride', vehicle_id=str(original), revision=other['revision']).status_code, 409)

    def test_sync_keeps_waiter_selection_key_when_details_change(self):
        client = self.app.test_client()
        self.login(client)
        self.save('等车人', 'wait', pickup='南门')
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        focus = re.search(r'data-select="(wait-[^"]+)"', page).group(1)
        params = self.sync_params(client)
        self.save('等车人', 'wait', pickup='北门')
        update = client.get(f'/events/{self.event}/sync', query_string={**params, 'focus': focus}).get_json()
        self.assertIn(f'data-focus="{focus}"', update['html'])
        self.assertIn(f'data-select="{focus}"', update['html'])
        self.assertIn('北门', update['html'])
        self.assertNotIn('南门', update['html'])

    def test_stale_registration_cannot_overwrite_or_recreate(self):
        self.save('同名', 'public')
        old = store.registration(self.db, self.event, '同名')
        self.save('同名', 'other', note='最新安排')
        with self.assertRaises(store.UserError):
            store.save_travel(self.db, self.event, '同名', {'mode': 'public', 'revision': old['revision']})
        with self.assertRaises(store.UserError):
            store.save_travel(self.db, self.event, '同名', {'mode': 'public', 'revision': ''})
        current = store.registration(self.db, self.event, '同名')
        self.assertEqual(current['note'], '最新安排')
        self.assertEqual(len(store.snapshot(self.db, self.event)['records']), 1)

    def test_two_connections_compete_for_last_seat(self):
        vehicle = self.car(capacity=1)
        ready = Barrier(2)

        def register(person):
            connection = store.connect(self.path)
            try:
                ready.wait(timeout=5)
                try:
                    store.save_travel(connection, self.event, person, {'mode': 'ride', 'vehicle_id': str(vehicle), 'revision': ''})
                    return 'saved'
                except store.UserError as exc:
                    return exc.status
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(register, ['甲', '乙']))
        self.assertCountEqual(results, ['saved', 409])
        self.assertEqual(len(store.snapshot(self.db, self.event)['cars'][0]['passengers']), 1)

    def test_closed_event_allows_admin_but_still_enforces_capacity(self):
        vehicle = self.car(capacity=1)
        store.update_event(self.db, self.event, '创建者', {'version': '1', 'is_open': '0'}, toggle=True)
        with self.assertRaises(store.UserError):
            self.save('甲', 'public')
        store.save_travel(self.db, self.event, '甲', {'mode': 'ride', 'vehicle_id': str(vehicle), 'revision': ''}, admin=True)
        with self.assertRaises(store.UserError):
            store.save_travel(self.db, self.event, '乙', {'mode': 'ride', 'vehicle_id': str(vehicle), 'revision': ''}, admin=True)

    def test_cross_event_vehicle_and_creator_permissions(self):
        vehicle = self.car()
        second = store.create_event(self.db, '别人', {'title': '另一次', 'event_date': '2026-10-25'})
        with self.assertRaises(store.UserError):
            store.save_travel(self.db, second, '乘客', {'mode': 'ride', 'vehicle_id': str(vehicle), 'revision': ''})
        with self.assertRaises(store.UserError):
            store.update_event(self.db, self.event, '别人', {'version': '1', 'is_open': '0'}, toggle=True)
        self.assertTrue(store.get_event(self.db, self.event)['is_open'])

    def test_pending_names_never_appear_in_public_html(self):
        self.save('后台专用提醒姓名', 'pending')
        self.save('后台专用提醒姓名', 'pending')
        client = self.app.test_client()
        self.login(client)
        public = client.get(f'/events/{self.event}')
        self.assertEqual(public.status_code, 200)
        self.assertNotIn('后台专用提醒姓名', public.get_data(as_text=True))
        self.assertEqual(client.get(f'/admin/events/{self.event}').status_code, 302)
        self.admin(client)
        admin = client.get(f'/admin/events/{self.event}')
        self.assertEqual(admin.status_code, 200)
        self.assertIn('后台专用提醒姓名', admin.get_data(as_text=True))
        reminders = store.snapshot(self.db, self.event, private=True)['reminders']
        self.assertEqual(len(reminders), 1)
        self.post(client, f'/admin/events/{self.event}/reminders/{reminders[0]["id"]}/resolve')
        self.assertIsNotNone(store.snapshot(self.db, self.event, private=True)['reminders'][0]['resolved_at'])

    def test_same_name_on_another_browser_and_member_cannot_target_others(self):
        first, second = self.app.test_client(), self.app.test_client()
        self.login(first, '林晓')
        self.assertEqual(self.post(first, f'/events/{self.event}/travel', mode='public', revision='', note='地铁前往').status_code, 303)
        self.login(second, '林晓')
        self.assertIn('地铁前往', second.get(f'/events/{self.event}').get_data(as_text=True))
        self.login(second, '另一人')
        self.post(second, f'/events/{self.event}/travel', mode='other', revision='', name='林晓')
        self.assertEqual(store.registration(self.db, self.event, '林晓')['mode'], 'public')
        self.assertEqual(store.registration(self.db, self.event, '另一人')['mode'], 'other')

    def test_csrf_deep_link_and_escaped_names(self):
        client = self.app.test_client()
        result = client.get(f'/events/{self.event}')
        self.assertIn('/identity?next=', result.location)
        self.login(client, '<script>alert(1)</script>')
        self.assertEqual(client.post('/events/new', data={'title': 'bad'}).status_code, 400)
        self.assertEqual(client.post('/events/new', data={'csrf': '错误令牌'}).status_code, 400)
        page = client.get(f'/events/{self.event}').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', page)
        self.assertNotIn('<script>alert(1)</script>', page)

    def test_all_editing_pages_render_and_errors_preserve_input(self):
        self.car()
        client = self.app.test_client()
        self.login(client, '创建者')
        for path in ('/events', '/events/new', f'/events/{self.event}/edit', f'/events/{self.event}/travel'):
            self.assertEqual(client.get(path).status_code, 200, path)
        result = self.post(client, f'/events/{self.event}/travel', mode='drive', revision='', departure='保留这个地点', capacity='-2')
        self.assertEqual(result.status_code, 400)
        self.assertIn('保留这个地点', result.get_data(as_text=True))
        self.admin(client)
        for path in ('/admin', f'/admin/events/{self.event}/edit', f'/admin/events/{self.event}/travel?name=司机', f'/admin/events/{self.event}/remove?name=司机'):
            self.assertEqual(client.get(path).status_code, 200, path)


if __name__ == '__main__':
    unittest.main()
