import time
import json
from pathlib import Path
from curl_cffi import requests
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService

COOKIES_PATH = Path("cookies_dict.json")
UA_PATH = Path("user_agent.txt")

def get_cookies():
    with uc.Chrome(service=ChromeService(ChromeDriverManager().install())) as driver:
        driver.implicitly_wait(60)
        driver.get("https://ozon.ru")
        driver.find_element(By.CSS_SELECTOR, "#stickyHeader")
        time.sleep(2)
        user_agent = driver.execute_script("return navigator.userAgent")
        cookies = driver.get_cookies()
    cookies_dict = {c["name"]: c["value"] for c in cookies}
    return user_agent, cookies_dict

def load_or_create_credentials():
    user_agent = None
    cookies_dict = None


    if UA_PATH.exists() and UA_PATH.stat().st_size > 0:
        user_agent = UA_PATH.read_text(encoding="utf-8").strip()

    if COOKIES_PATH.exists() and COOKIES_PATH.stat().st_size > 0:
        try:
            cookies_dict = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))

            if not isinstance(cookies_dict, dict):
                cookies_dict = None
        except Exception:
            cookies_dict = None

    if not user_agent or not cookies_dict:
        user_agent, cookies_dict = get_cookies()
        COOKIES_PATH.write_text(json.dumps(cookies_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        UA_PATH.write_text(user_agent, encoding="utf-8")

    return user_agent, cookies_dict

def main():
    user_agent, cookies_dict = load_or_create_credentials()

    url = ("https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?"
           "url=/search/?from_global=true&layout_container=default&layout_page_index=3"
           "&page=3&paginator_token=3635012&search_page_state=UAPapvVpdNnVS9Q-M_kdcHbMSfYceL07TZCEImduP3YliA-"
           "ZO3MQQ5UBQ9848TIZkYHS7WvSKPUq0JyT_ANMpb5DCY-eF2IHigt9sr1mZ-qoehIxb5BKzRgmOVF0Lq9wu2fvHsM%3D"
           "&start_page_id=9406b6583935ed9f17869c2289d16916&text=ps+vita")

    headers = {"user-agent": user_agent}

    response = requests.get(url, cookies=cookies_dict, headers=headers)  

    try:
        data = response.json()
        with open("json.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        with open("html.html", "w", encoding="utf-8") as f:
            f.write(response.text)

if __name__ == "__main__":
    main()


