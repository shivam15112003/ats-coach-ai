import os
import shutil
import tempfile
import time

FAILURE_PHRASES = (
    "temporarily unavailable",
    "temporarily not available",
    "temporarily closed",
    "something went wrong",
    "try again later",
    "service is unavailable",
    "service temporarily unavailable",
    "site can't be reached",
    "site can’t be reached",
    "i'm having trouble responding",
    "i’m having trouble responding",
    "i am having trouble responding",
    "unable to process your request",
    "unable to process this request",
    "error generating your response",
    "failed to generate a response",
)

RETRY_DELAY = float(os.environ.get("GEMINI_BROWSER_RETRY_DELAY", "8"))
GEMINI_URL = "https://gemini.google.com/app"

_BOX_JS = """return (document.querySelector('[role="textbox"][contenteditable="true"]')
  || document.querySelector('textarea[aria-label*="Ask Gemini"]')
  || document.querySelector('textarea[placeholder*="Ask Gemini"]'));"""

_SEND_JS = """const sels=['button[aria-label*="Send" i]','button[type="submit"]','[role="button"][aria-label*="Send" i]'];
for (const s of sels){for (const el of document.querySelectorAll(s)){
const r=el.getBoundingClientRect();const st=getComputedStyle(el);
if(r.width>0&&r.height>0&&st.display!=='none'&&!el.disabled)return el;}}return null;"""

_STOP_JS = """for (const el of document.querySelectorAll('button,[role="button"]')){
const t=((el.getAttribute('aria-label')||'')+' '+(el.innerText||'')).toLowerCase();
const r=el.getBoundingClientRect();
if(r.width>0&&r.height>0&&(t.includes('stop')||t.includes('cancel')))return true;}return false;"""

_RESP_JS = """const els=[...document.querySelectorAll('message-content, .response-container, [data-message-author-role="assistant"]')];
if(!els.length)return '';
return els[els.length-1].innerText||'';"""

_COUNT_JS = """return document.querySelectorAll('message-content,[data-message-author-role="assistant"]').length;"""


def _failure_phrase(text: str) -> str:
    low = (text or "").lower()
    return next((p for p in FAILURE_PHRASES if p in low), "")


def _build_options(fresh_profile_dir: str):
    from selenium import webdriver

    opts = webdriver.ChromeOptions()
    # Headless-first (Cloud-safe, no display, no login).
    opts.add_argument("--headless=new")
    # Headed alternative — commented out (local debugging only, needs a display):
    # opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(f"--user-data-dir={fresh_profile_dir}")
    for binary in ("chromium", "chromium-browser", "google-chrome"):
        path = shutil.which(binary)
        if path:
            opts.binary_location = path
            break
    return opts


def _new_driver(profile_dir: str):
    from selenium import webdriver

    return webdriver.Chrome(options=_build_options(profile_dir))


def _wait_idle(driver, timeout: int = 120):
    start = time.time()
    calm_since = None
    last_len = 0
    while time.time() - start < timeout:
        try:
            generating = bool(driver.execute_script(_STOP_JS))
        except Exception:
            generating = False
        try:
            text = str(driver.execute_script(_RESP_JS) or "")
        except Exception:
            text = ""
        if not generating and len(text) > 50 and len(text) == last_len:
            if calm_since is None:
                calm_since = time.time()
            if time.time() - calm_since > 3:
                return text
        else:
            calm_since = None
        last_len = len(text)
        time.sleep(1.0)
    try:
        return str(driver.execute_script(_RESP_JS) or "")
    except Exception:
        return ""


def browser_generate(
    prompt: str, max_attempts: int = 3, wait_timeout: int = 150
) -> str:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    profile_dir = tempfile.mkdtemp(prefix="ats_gemini_fresh_")
    driver = None
    failures = 0
    try:
        driver = _new_driver(profile_dir)
        driver.get(GEMINI_URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                time.sleep(RETRY_DELAY)
            try:
                box = driver.execute_script(_BOX_JS)
                if not box:
                    raise RuntimeError("composer not found")
                driver.execute_script("arguments[0].focus();", box)
                box.click()
                box.send_keys(Keys.CONTROL + "a")
                box.send_keys(Keys.DELETE)
                for chunk in [
                    prompt[i : i + 2000] for i in range(0, len(prompt), 2000)
                ]:
                    box.send_keys(chunk)
                    time.sleep(0.2)
                send_btn = driver.execute_script(_SEND_JS)
                if send_btn:
                    send_btn.click()
                else:
                    box.send_keys(Keys.ENTER)
                text = _wait_idle(driver, timeout=wait_timeout)
                bad = _failure_phrase(text) or _failure_phrase(
                    driver.find_element(By.TAG_NAME, "body").text
                )
                if bad:
                    raise RuntimeError(f"gemini busy: {bad}")
                if len((text or "").strip()) < 50:
                    raise RuntimeError("empty response")
                return text.strip()
            except Exception as e:
                failures += 1
                if attempt >= max_attempts:
                    raise
                if failures <= 1:
                    try:
                        driver.refresh()
                    except Exception:
                        driver.get(GEMINI_URL)
                    time.sleep(2)
                else:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    profile_dir = tempfile.mkdtemp(prefix="ats_gemini_fresh_")
                    driver = _new_driver(profile_dir)
                    driver.get(GEMINI_URL)
                    time.sleep(3)
        raise RuntimeError("browser attempts exhausted")
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        shutil.rmtree(profile_dir, ignore_errors=True)
