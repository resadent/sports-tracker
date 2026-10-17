"""End-to-end checks. Always creates its own temporary database and server.

Install the optional browser-test dependencies and run this file directly.
Screenshots go to /tmp/sports-tracker-browser-artifacts by default.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright


@contextmanager
def isolated_server():
    with tempfile.TemporaryDirectory(prefix="sports-tracker-browser-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{directory}/review.sqlite", PYTHONPATH="src")
        command = (
            "from sports_tracker.main import app; "
            "from sports_tracker.db.base import Base; "
            "from sports_tracker.db.session import engine; "
            "Base.metadata.create_all(engine); "
            f"import uvicorn; uvicorn.run(app, host='127.0.0.1', port={port}, log_level='warning')"
        )
        with open(Path(directory) / "server.log", "w+") as log:
            process = subprocess.Popen([sys.executable, "-c", command], env=env, stdout=log, stderr=log)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    if process.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(log.read())
                    try:
                        with urllib.request.urlopen(base, timeout=1):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Preview server did not start")
                yield base
            finally:
                process.terminate()
                process.wait(timeout=10)


def check_dashboard(BASE):
    artifacts = Path(os.getenv("BROWSER_ARTIFACTS", "/tmp/sports-tracker-browser-artifacts"))
    artifacts.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        request = p.request.new_context(base_url=BASE)
        email = f'browser{int(time.time())}@example.com'
        password = 'supersecret1'
        assert request.post('/api/v1/users', data={'email':email,'password':password}).status == 201
        login = request.post('/api/v1/auth/login', form={'username':email,'password':password})
        headers = {'Authorization':'Bearer '+login.json()['access_token']}
        today = date.today()
        for offset,weight,waist in [(10,71.123456789,83.3456789),(1,70.123456789,82.3456789)]:
            r = request.post('/api/v1/measurements', headers=headers, data={'date':str(today-timedelta(days=offset)), 'weight_kg':weight, 'waist_cm':waist,'notes':'Original <note>'})
            assert r.ok, r.text()
        browser = p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'), headless=True, args=['--no-sandbox'])
        context = browser.new_context(ignore_https_errors=True, viewport={'width':1100,'height':1000})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        page.locator('#login-email').fill(email)
        page.locator('#login-password').fill(password)
        page.locator('#login-form button[type=submit]').click()
        try:
            page.wait_for_function('typeof Chart !== "undefined" && dashboardMeasurements.length === 2', timeout=10000)
        except Exception:
            print("Initial dashboard state:", page.evaluate("({hash:location.hash, chart:typeof Chart, count:typeof dashboardMeasurements === 'undefined' ? null : dashboardMeasurements.length, body:document.body.innerText})"))
            print("Browser errors:", errors)
            raise
        assert page.locator('#weight-chart').count() == 1
        assert page.locator('#waist-chart').count() == 1
        assert page.locator('#recomposition-chart').count() == 1
        assert 'Insufficient data' in page.locator('#recomposition-status').inner_text()
        assert 'Same dates' in page.locator('#measurement-comparison').inner_text()
        assert page.evaluate('Chart.getChart(document.getElementById("weight-chart")).options.scales.x.type') == 'linear'
        # Existing-date entry is loaded and notes-only editing preserves full precision.
        existing = request.get('/api/v1/measurements',headers=headers).json()[-1]
        page.locator('#history-body tr').first.get_by_role('button',name='Edit',exact=True).click()
        page.locator('#log-form details').first.locator('summary').click()
        page.locator('#log-notes').fill('Changed <script>window.bad=1</script>')
        page.locator('#log-save').click()
        page.wait_for_function('dashboardMeasurements.some(m => m.notes.startsWith("Changed"))')
        after = request.get('/api/v1/measurements',headers=headers).json()[-1]
        assert after['weight_kg'] == existing['weight_kg'] and after['waist_cm'] == existing['waist_cm']
        assert page.evaluate('window.bad') is None
        # Unit preferences convert display only, even when saving the same entry again.
        page.locator('.measurement-settings > summary').click()
        page.locator('#set-weight-unit').select_option('lb')
        page.locator('#set-waist-unit').select_option('in')
        page.locator('#set-weight-reminder').fill('1')
        page.locator('#set-recomp').fill('1')
        page.locator('#settings-form button[type=submit]').click()
        page.wait_for_function('dashboardSettings.weight_unit === "lb"')
        assert page.evaluate('Chart.getChart(document.getElementById("recomposition-chart")).data.datasets[0].data.some(p => p.y != null)')
        assert request.get('/api/v1/settings',headers=headers).json()['recomp_window'] == 1
        assert 'Time to log weight' in page.locator('#reminder-msg').inner_text()
        page.locator('#log-notes').fill('Changed after units')
        page.locator('#log-save').click()
        page.wait_for_function('dashboardMeasurements.some(m => m.notes === "Changed after units")')
        after = request.get('/api/v1/measurements',headers=headers).json()[-1]
        assert after['weight_kg'] == existing['weight_kg'], (after,existing)
        assert after['waist_cm'] == existing['waist_cm']
        # Add repeat readings in inches; stored readings and mean are centimetres.
        page.locator('#log-date').fill(str(today))
        page.locator('#log-date').dispatch_event('change')
        page.locator('#log-repeats').fill('32, 32.2')
        page.locator('#log-notes').fill('Repeated tape')
        page.locator('#log-save').click()
        page.wait_for_function('dashboardMeasurements.length === 3')
        added = request.get('/api/v1/measurements',headers=headers).json()[-1]
        assert abs(added['waist_cm']-81.53) < 0.001
        assert all(abs(a-b) < 1e-10 for a,b in zip(added['waist_readings'],[81.28,81.788]))
        page.locator('#history-body tr').first.get_by_role('button',name='Delete',exact=True).click()
        page.wait_for_function('dashboardMeasurements.length === 2')
        page.locator('#undo-delete').click()
        page.wait_for_function('dashboardMeasurements.length === 3')
        restored = request.get('/api/v1/measurements',headers=headers).json()[-1]
        assert restored['id'] == added['id'] and restored['waist_readings'] == added['waist_readings']
        page.locator('#history-body tr').first.get_by_role('button',name='Delete',exact=True).click()
        page.wait_for_function('dashboardMeasurements.length === 2')
        page.reload()
        page.wait_for_function('dashboardMeasurements.length === 2')
        deleted_panel = page.locator('details.panel').filter(has=page.locator('#load-deleted'))
        deleted_panel.locator('summary').click()
        page.locator('#load-deleted').click()
        page.locator('#deleted-list button').first.click()
        page.wait_for_function('dashboardMeasurements.length === 3')
        page.locator('#log-form details').first.locator('summary').click()
        # Correct a date without changing values.
        page.locator('#history-body tr').first.get_by_role('button',name='Edit',exact=True).click()
        new_date = str(today-timedelta(days=2))
        page.locator('#log-date').fill(new_date)
        page.locator('#log-save').click()
        page.wait_for_function('(d) => dashboardMeasurements.some(m => m.date === d && m.notes === "Repeated tape")',arg=new_date)
        # CSV preview is read-only and existing dates are kept by default.
        page.locator('details.panel').last.locator('summary').click()
        csv_data = f'date,weight_kg\n{today-timedelta(days=1)},99\n{today},70\n'
        page.locator('#import-file').set_input_files({'name':'review.csv','mimeType':'text/csv','buffer':csv_data.encode()})
        page.locator('#import-form button[type=submit]').click()
        page.wait_for_function('importPreview !== null')
        assert len(request.get('/api/v1/measurements',headers=headers).json()) == 3
        assert '1 new' in page.locator('#import-msg').inner_text()
        assert '1 kept' in page.locator('#import-msg').inner_text()
        page.locator('#confirm-import').click()
        page.wait_for_function('dashboardMeasurements.length === 4')
        with page.expect_download() as download:
            page.locator('#export-measurements').click()
        assert download.value.suggested_filename.endswith('.csv')
        # Switching months and mobile layout remain usable.
        page.locator('#chart-window').select_option(str(today)[:7])
        page.screenshot(path=str(artifacts / 'measurement-dashboard-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(300)  # Wait for the responsive chart resize.
        page.screenshot(path=str(artifacts / 'measurement-dashboard-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows on mobile'
        assert not errors, errors
        print('Browser checks passed: charts, precision, units, notes, repeats, date correction, undo, CSV, reminders, mobile layout.')
        browser.close()


if __name__ == "__main__":
    with isolated_server() as base:
        check_dashboard(base)
