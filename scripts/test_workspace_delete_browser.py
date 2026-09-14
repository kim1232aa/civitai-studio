"""Browser regression: planner/editor shot deletion, real UI on the live entry.
Run from repo: python3 scripts/test_workspace_delete_browser.py --out temp/delete-proof
Use --baseline to serve HEAD's storyboard.js and reproduce before a working-tree fix.
"""
import argparse
import json
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--out', required=True)
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=True)
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1600, 'height': 1000})
    page = context.new_page()
    page.set_default_timeout(10000)
    if args.baseline:
        original = subprocess.check_output(['git', 'show', 'HEAD:static/storyboard.js'], cwd=root)
        page.route('**/static/storyboard.js*', lambda route: route.fulfill(body=original, content_type='application/javascript; charset=utf-8'))
    try:
        page.goto('http://127.0.0.1:18832/storyboard.html', wait_until='domcontentloaded')
        expect(page.locator('header [data-workspace="script"]')).to_be_visible()
        page.locator('header [data-workspace="script"]').click()
        page.locator('[data-script-act="add-scene"]').click()
        page.locator('[data-script-act="add-shot"]').click()
        shot = page.locator('[data-shot-title]').first.get_attribute('data-shot-title')
        page.locator('[data-shot-title]').first.fill('Deletion regression shot')
        button = page.locator(f'[data-script-act="delete-shot"][data-shot-id="{shot}"]')
        expect(button).to_be_visible()
        before = page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()')
        page.once('dialog', lambda dialog: dialog.dismiss())
        button.click()
        assert page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()') == before
        checks.append('planner cancel preserves full state')
        page.once('dialog', lambda dialog: dialog.accept())
        button.click()
        expect(button).to_have_count(0)
        page.reload(wait_until='domcontentloaded')
        saved = page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()')
        assert all(n['id'] != shot for n in saved['nodes'])
        assert all(shot not in s['shotIds'] for s in saved['script']['scenes'])
        assert len(saved['script']['scenes']) == len(before['script']['scenes'])
        assert {n['id'] for n in saved['nodes']} == {n['id'] for n in before['nodes']} - {shot}
        checks.append('planner accept + refresh removes only target node and scene membership')
        page.locator('[data-script-act="add-shot"]').click()
        shot = page.locator('[data-shot-title]').last.get_attribute('data-shot-title')
        page.locator('header [data-workspace="editor"]').click()
        button = page.locator(f'[data-editor-act="delete-shot"][data-shot-id="{shot}"]')
        expect(button).to_be_visible()
        before = page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()')
        page.once('dialog', lambda dialog: dialog.dismiss())
        button.click()
        assert page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()') == before
        checks.append('editor cancel preserves full state')
        page.once('dialog', lambda dialog: dialog.accept())
        button.click()
        expect(button).to_have_count(0)
        page.reload(wait_until='domcontentloaded')
        expect(page.locator(f'[data-editor-shot="{shot}"]')).to_have_count(0)
        saved = page.evaluate('(function(){const k=Object.keys(localStorage).find(k=>k.startsWith("nl-storyboard"));return k?JSON.parse(localStorage.getItem(k)):null})()')
        assert all(n['id'] != shot for n in saved['nodes'])
        assert all(shot not in s['shotIds'] for s in saved['script']['scenes'])
        assert len(saved['script']['scenes']) == len(before['script']['scenes'])
        checks.append('editor accept + refresh removes only target node and scene membership')
        page.screenshot(path=str(out / 'after-delete.png'))
        result = {'pass': True, 'checks': checks, 'baseline': args.baseline}
    except Exception as error:
        page.screenshot(path=str(out / 'failure.png'))
        result = {'pass': False, 'checks': checks, 'error': str(error), 'baseline': args.baseline}
    finally:
        browser.close()
(out / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['pass'] else 1)
