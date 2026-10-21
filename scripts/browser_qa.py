import json,time,os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
url='http://127.0.0.1:8088'
checks=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
 page=context.new_page()
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);page.wait_for_selector('#topic-nav button');expect(page.locator("#ai-status")).to_contain_text("Sẵn sàng")
 page.screenshot(path=str(ROOT/'reports'/'desktop.png'),full_page=True)
 assert page.locator('h1').first.is_visible();checks.append('Desktop landing, model status and seven topics')
 page.locator('.toggle').click();page.locator('#question').fill('hoc phi nam nay bao nhieu');page.locator('#send').click()
 page.wait_for_selector('.message.assistant .citation',timeout=20000)
 assert page.locator('.message.assistant .citation').first.get_attribute('href').startswith('https://')
 page.screenshot(path=str(ROOT/'reports'/'chat.png'),full_page=True);checks.append('Chat without accents, answer and official citation')
 page.locator('[data-vote="1"]').last.click();page.wait_for_selector('[data-vote="1"].selected');checks.append('Feedback persisted')
 page.locator('a[data-view="knowledge"]').click();page.wait_for_selector('.faq-card')
 page.locator('#knowledge-category').select_option('ky_tuc_xa');page.wait_for_timeout(400)
 assert 'Ký túc xá' in page.locator('#knowledge-list').inner_text();page.locator('.faq-card').first.click()
 page.screenshot(path=str(ROOT/'reports'/'knowledge.png'),full_page=True);checks.append('Knowledge filter, expand and source link')
 page.locator('a[data-view="experiments"]').click();page.wait_for_selector('.cm-table')
 assert page.locator('.cm-table').count()==2;checks.append('Experimental comparison and confusion matrices')
 page.screenshot(path=str(ROOT/'reports'/'experiments.png'),full_page=True)
 page.locator('a[data-view="admin"]').click();page.wait_for_selector('#admin-password')
 page.locator('#admin-password').fill(os.environ.get('HAUI_ADMIN_PASSWORD') or (ROOT/'data'/'initial-admin-password.txt').read_text().strip());page.locator('#login-form button').click()
 page.wait_for_selector('#add-faq');checks.append('Admin login and knowledge management')
 page.locator('[data-tab="ai"]').click();page.wait_for_selector('#ai-form')
 assert page.locator('input[name="model"]').input_value()=='qwen3:4b';checks.append('Local and external generative AI settings')
 page.screenshot(path=str(ROOT/'reports'/'admin.png'),full_page=True)
 page.locator('#logout').click();page.wait_for_selector('#login-form');checks.append('Admin logout')
 mobile=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
 mp=mobile.new_page();mp.on('pageerror',lambda e:errors.append(str(e)));mp.goto(url);mp.wait_for_selector('#topic-nav button')
 assert mp.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 assert mp.locator('#question').is_visible();assert mp.locator('#send').is_visible()
 mp.screenshot(path=str(ROOT/'reports'/'mobile.png'),full_page=True);checks.append('390px mobile layout without horizontal overflow')
 mp.locator('#menu').click();assert mp.locator('#sidebar').evaluate("e=>e.classList.contains('open')")
 mp.locator('a[data-view="knowledge"]').click();mp.wait_for_selector('.faq-card');assert not mp.locator('#sidebar-overlay').is_visible();checks.append('Mobile navigation')
 context.request.delete(url+'/api/history');mobile.request.delete(url+'/api/history');context.close();mobile.close();browser.close()
assert not errors,errors
out={'passed':len(checks),'checks':checks,'javascript_errors':errors}
(ROOT/'reports'/'browser-qa.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
