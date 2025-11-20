import json
import time
import os
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from curl_cffi import requests 

# --- КОНФИГУРАЦИЯ ---
# Файлы для хранения сессии
COOKIES_FILE = "cookies_dict.txt"
UA_FILE = "user_agent.txt"

# --- ФУНКЦИИ ДЛЯ ФАЙЛОВ ---
def load_data(filename, default_value=None):
    if not os.path.exists(filename):
        return default_value
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
    """Запускает браузер, чтобы получить свежие куки."""
    print("\nЗапускаем Chrome для обновления куки...")
    options = uc.ChromeOptions()
    
    try:
        with uc.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options) as driver:
            driver.implicitly_wait(10)
            driver.get("https://www.ozon.ru")
            
            print("Ждем прогрузки защиты Ozon (6 сек)...")
            time.sleep(6) 
            
            # Имитируем поведение человека (скролл)
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(2)
            
            user_agent = driver.execute_script("return navigator.userAgent")
            cookies = driver.get_cookies()
            
            # Преобразуем куки в словарь
            cookies_dict = {c["name"]: c["value"] for c in cookies}
            
            save_data(UA_FILE, user_agent)
            save_data(COOKIES_FILE, cookies_dict)
            
            print("Куки успешно обновлены и сохранены!\n")
            return user_agent, cookies_dict
    except Exception as e:
        print(f"Ошибка при обновлении куки: {e}")
        return None, None

# --- ПРОВЕРКА КУКИ ---
def check_cookies_validity(cookies, user_agent):
    """Делает тестовый запрос, чтобы понять, живы ли куки."""
    if not cookies or not user_agent:
        return False
        
    print("Проверяем актуальность текущих куки...")
    url = "https://www.ozon.ru/api/composer-api.bx/_action/v2/searchResultsV2?url=/search/?text=test"
    
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/json",
        "x-o3-app-name": "dweb_client",
    }

    try:
        # Делаем легкий запрос
        response = requests.get(
            "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/search/?text=test",
            cookies=cookies,
            headers=headers,
            impersonate="chrome110",
            timeout=10
        )
        
        if response.status_code == 200:
            print("Куки валидны. Браузер запускать не нужно.")
            return True
        elif response.status_code == 403:
            print("Куки просрочены (403 Forbidden).")
            return False
        else:
            print(f"Странный статус ответа: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка проверки куки: {e}")
        return False

# --- ПАРСИНГ (API) ---
def get_page(text: str, page: int, cookies: dict, ua: str):
    print(f"Запрос API: страница {page}")
    
    url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/search/?page={page}&text={text.replace(' ', '+')}&layout_container=searchPage"
    
    headers = {
        "User-Agent": ua,
        "Accept": "application/json",
        "x-o3-app-name": "dweb_client", 
    }

    try:
        response = requests.get(
            url, 
            cookies=cookies, 
            headers=headers, 
            impersonate="chrome110",
            timeout=15
        )
        
        if response.status_code == 403:
            print("403 Forbidden во время парсинга.")
            return None, 1
            
        response_json = response.json()
        
        total_pages = 1
        try:
            shared = response_json.get("shared")
            if isinstance(shared, str): shared = json.loads(shared)
            if shared: total_pages = shared.get("catalog", {}).get("totalPages", 1)
        except: pass

        return response, total_pages
    
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None, 1

def get_data_json(response_json):
    result = []
    widget_states = response_json.get("widgetStates", {})
    found_something = False
    
    # Универсальная рекурсивная функция поиска
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
                    # print(f"-> Данные найдены в ключе: {key}") # Можно раскомментировать для отладки
                    found_something = True
                    
                    for item in data["items"]:
                        # 1. НАЗВАНИЕ
                        potential_names = deep_search(item, target_keys=["textAtom", "text"])
                        clean_names = []
                        for p in potential_names:
                            if isinstance(p, dict) and "text" in p: clean_names.append(p["text"])
                            elif isinstance(p, str): clean_names.append(p)
                        
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
                            item,
                            target_keys=["src", "url", "link"], 
                            value_condition=lambda x: isinstance(x, str) and x.startswith("http") and (".jpg" in x or ".webp" in x or ".png" in x)
                        )
                        
                        image_url = "Нет картинки"
                        for img in potential_images:
                            if "ozon" in img or "cdn" in img:
                                image_url = img
                                break
                        if image_url == "Нет картинки" and potential_images:
                            image_url = potential_images[0]

                        if name != "Нет названия":
                            result.append([name, price, image_url])
                    
                    break 
        except Exception:
            continue

    return result

# --- ГЛАВНЫЙ ЗАПУСК ---
if __name__ == '__main__':
    # 1. Загружаем сохраненные данные
    user_agent = load_data(UA_FILE)
    cookies_dict = load_data(COOKIES_FILE)

    # 2. ПРОВЕРЯЕМ КУКИ НА ВАЛИДНОСТЬ
    is_valid = check_cookies_validity(cookies_dict, user_agent)

    # 3. Если куки плохие или их нет -> обновляем
    if not is_valid:
        user_agent, cookies_dict = get_new_cookies()
        if not cookies_dict:
            print("Не удалось получить куки. Завершение работы.")
            exit()

    # 4. Начинаем парсинг
    query = "ps vita"
    all_items = []
    
    print(f"\nНачинаем поиск: {query}")
    response, total_pages = get_page(query, 1, cookies_dict, user_agent)
    
    if response:
        # Если вдруг даже после проверки словили 403 (редко, но бывает)
        if response.status_code == 403:
             print(" Внезапный 403. Пробуем обновить куки еще раз...")
             user_agent, cookies_dict = get_new_cookies()
             response, total_pages = get_page(query, 1, cookies_dict, user_agent)

        if response and response.status_code == 200:
            items = get_data_json(response.json())
            all_items.extend(items)
            
            print(f" Всего страниц: {total_pages}")
            max_pages = min(total_pages, 3) # Для теста берем 3 страницы

            for page in range(2, max_pages + 1):
                time.sleep(1.5)
                resp, _ = get_page(query, page, cookies_dict, user_agent)
                if resp and resp.status_code == 200:
                    all_items.extend(get_data_json(resp.json()))
                else:
                    break
        else:
            print("Не удалось получить данные первой страницы.")

    print(f"\n ИТОГ: собрано {len(all_items)} товаров")
    
    # Показать примеры
    for idx, item in enumerate(all_items[:5], 1):
        print(f"{idx}. {item[0][:40]}... | {item[1]} | {item[2]}")