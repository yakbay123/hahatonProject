import json
import time
import os
import re  
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from curl_cffi import requests 

# --- КОНФИГУРАЦИЯ ---
COOKIES_FILE = "cookies_dict.txt"
UA_FILE = "user_agent.txt"

# --- ФУНКЦИИ ДЛЯ ФАЙЛОВ ---
def load_data(filename, default_value=None):
    if not os.path.exists(filename): return default_value
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content: return default_value
            try: return json.loads(content)
            except: return content
    except: return default_value

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        if isinstance(data, (dict, list)): json.dump(data, file, ensure_ascii=False, indent=4)
        else: file.write(str(data))

# --- БРАУЗЕР (SELENIUM) ---
def get_new_cookies():
    print("\n Запускаем Chrome для обновления куки...")
    options = uc.ChromeOptions()
    try:
        with uc.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options) as driver:
            driver.implicitly_wait(10)
            driver.get("https://www.ozon.ru")
            print(" Ждем прогрузки защиты Ozon (6 сек)...")
            time.sleep(6) 
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(2)
            
            user_agent = driver.execute_script("return navigator.userAgent")
            cookies = driver.get_cookies()
            cookies_dict = {c["name"]: c["value"] for c in cookies}
            
            save_data(UA_FILE, user_agent)
            save_data(COOKIES_FILE, cookies_dict)
            print(" Куки обновлены!\n")
            return user_agent, cookies_dict
    except Exception as e:
        print(f" Ошибка обновления: {e}")
        return None, None

# --- ПРОВЕРКА КУКИ ---
def check_cookies_validity(cookies, user_agent):
    if not cookies or not user_agent: return False
    print(" Проверка куки...")
    try:
        response = requests.get(
            "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/search/?text=test",
            cookies=cookies, headers={"User-Agent": user_agent, "x-o3-app-name": "dweb_client"},
            impersonate="chrome110", timeout=10
        )
        if response.status_code == 200:
            print(" Куки валидны.")
            return True
        print(" Куки просрочены.")
        return False
    except: return False

# --- API ЗАПРОС ---
def get_page(text: str, page: int, cookies: dict, ua: str):
    print(f" Запрос страницы {page}")
    url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/search/?page={page}&text={text.replace(' ', '+')}&layout_container=searchPage"
    try:
        response = requests.get(
            url, cookies=cookies, headers={"User-Agent": ua, "x-o3-app-name": "dweb_client"},
            impersonate="chrome110", timeout=15
        )
        if response.status_code == 403: return None, 1
        
        resp_json = response.json()
        total_pages = 1
        try:
            shared = resp_json.get("shared")
            if isinstance(shared, str): shared = json.loads(shared)
            if shared: total_pages = shared.get("catalog", {}).get("totalPages", 1)
        except: pass
        return response, total_pages
    except Exception as e:
        print(f"Ошибка: {e}")
        return None, 1

# --- ПАРСИНГ JSON ---
def get_data_json(response_json):
    result = []
    widget_states = response_json.get("widgetStates", {})
    found_something = False
    
    # Рекурсивный поиск
    def deep_search(data, target_keys=None, value_condition=None):
        found_values = []
        if isinstance(data, dict):
            for k, v in data.items():
                if target_keys and k in target_keys: found_values.append(v)
                if value_condition and isinstance(v, str) and value_condition(v): found_values.append(v)
                found_values.extend(deep_search(v, target_keys, value_condition))
        elif isinstance(data, list):
            for item in data: found_values.extend(deep_search(item, target_keys, value_condition))
        return found_values

    for key, value_str in widget_states.items():
        try:
            data = json.loads(value_str)
            if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                if "mainState" in data["items"][0]:
                    found_something = True
                    
                    for item in data["items"]:
                        # 1. НАЗВАНИЕ
                        potential_names = deep_search(item, target_keys=["textAtom", "text"])
                        clean_names = [p["text"] if isinstance(p, dict) and "text" in p else p for p in potential_names if isinstance(p, str) or isinstance(p, dict)]
                        name = "Нет названия"
                        if clean_names:
                            best_name = max(clean_names, key=len)
                            if len(best_name) > 10: name = best_name

                        # 2. ЦЕНА
                        potential_prices = deep_search(item, value_condition=lambda x: "₽" in x and len(x) < 20)
                        price = potential_prices[0] if potential_prices else "Нет цены"
                        if price == "Нет цены":
                             pv2 = deep_search(item, target_keys=["priceV2"])
                             if pv2: 
                                 try: price = pv2[0]["price"][0]["text"]
                                 except: pass

                        # 3. ФОТО
                        potential_images = deep_search(
                            item, target_keys=["src", "url", "link"], 
                            value_condition=lambda x: isinstance(x, str) and x.startswith("http") and (".jpg" in x or ".webp" in x)
                        )
                        image_url = next((img for img in potential_images if "ozon" in img or "cdn" in img), potential_images[0] if potential_images else "Нет фото")

                        # 4. АРТИКУЛ (НОВОЕ!)
                        article = "Нет артикула"
                        # Способ А: Прямой ID (обычно это и есть артикул)
                        if "id" in item:
                            article = str(item["id"])
                        
                        # Способ Б: Вытаскиваем из ссылки, если ID не найден
                        if article == "Нет артикула":
                             links = deep_search(item, target_keys=["link", "url"], value_condition=lambda x: "/product/" in x)
                             if links:
                                 # Ссылка вида: /product/tovar-name-123456/?...
                                 # Ищем цифры после последнего дефиса и перед слешем
                                 match = re.search(r'-(\d+)/', links[0])
                                 if match:
                                     article = match.group(1)

                        if name != "Нет названия":
                            result.append([name, price, article, image_url]) # <--- Добавили article в список
                    
                    break 
        except Exception: continue

    return result

# --- ЗАПУСК ---
if __name__ == '__main__':
    user_agent = load_data(UA_FILE)
    cookies_dict = load_data(COOKIES_FILE)

    if not check_cookies_validity(cookies_dict, user_agent):
        user_agent, cookies_dict = get_new_cookies()
        if not cookies_dict: exit()

    query = "ps vita"
    all_items = []
    
    print(f"\n Ищем: {query}")
    response, total_pages = get_page(query, 1, cookies_dict, user_agent)
    
    if response:
        if response.status_code == 403:
             print(" 403. Обновляем куки...")
             user_agent, cookies_dict = get_new_cookies()
             response, total_pages = get_page(query, 1, cookies_dict, user_agent)

        if response and response.status_code == 200:
            all_items.extend(get_data_json(response.json()))
            print(f" Страниц: {total_pages}")
            
            # Парсим до 3 страниц
            for page in range(2, min(total_pages, 3) + 1):
                time.sleep(1.5)
                resp, _ = get_page(query, page, cookies_dict, user_agent)
                if resp and resp.status_code == 200:
                    all_items.extend(get_data_json(resp.json()))

    print(f"\n Собрано: {len(all_items)}")
    
    # Вывод с артикулом
    print("-" * 80)
    print(f"{'АРТИКУЛ':<15} | {'ЦЕНА':<10} | {'НАЗВАНИЕ'}")
    print("-" * 80)
    for item in all_items[:10]:
        # item = [Name, Price, Article, Image]
        name = (item[0][:45] + '..') if len(item[0]) > 45 else item[0]
        print(f"{item[2]:<15} | {item[1]:<10} | {name}")