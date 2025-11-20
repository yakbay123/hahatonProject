import json
import time
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from curl_cffi import requests 

# --- ФУНКЦИИ ДЛЯ ДАННЫХ ---
def load_data(filename, default_value=None):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content: return default_value
            try: return json.loads(content)
            except: return content
    except FileNotFoundError: return default_value

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        if isinstance(data, (dict, list)): json.dump(data, file, ensure_ascii=False, indent=4)
        else: file.write(str(data))

# --- ОСНОВНАЯ ЛОГИКА ---
cookies_dict = load_data("cookies_dict.txt", default_value={}) 
user_agent = load_data("user_agent.txt", default_value="")

def get_cookies():
    print("Запуск браузера для получения куки...")
    options = uc.ChromeOptions()
    try:
        with uc.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options) as driver:
            driver.implicitly_wait(10)
            driver.get("https://www.ozon.ru")
            time.sleep(6) 
            driver.execute_script("window.scrollTo(0, 200);")
            
            new_user_agent = driver.execute_script("return navigator.userAgent")
            cookies = driver.get_cookies()

        new_cookies_dict = {i["name"]: i["value"] for i in cookies}
        save_data("user_agent.txt", new_user_agent)
        save_data("cookies_dict.txt", new_cookies_dict)
        return new_user_agent, new_cookies_dict
    except Exception as e:
        print(f"Ошибка в браузере: {e}")
        return "", {}

def get_page(text: str, page: int, current_cookies: dict, current_user_agent: str):
    print(f"Запрос API: страница {page}")
    
    url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/search/?page={page}&text={text.replace(' ', '+')}&layout_container=searchPage"
    
    headers = {
        "User-Agent": current_user_agent,
        "Accept": "application/json",
        "x-o3-app-name": "dweb_client", 
    }

    try:
        response = requests.get(
            url, 
            cookies=current_cookies, 
            headers=headers, 
            impersonate="chrome110",
            timeout=15
        )
        
        if response.status_code == 403:
            print("403 Forbidden. Куки сгорели.")
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
    
    # --- УНИВЕРСАЛЬНЫЙ ПОИСК ---
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
                    print(f"-> Данные найдены в ключе: {key}")
                    found_something = True
                    
                    for item in data["items"]:
                        # 1. НАЗВАНИЕ (Самый длинный текст в объекте)
                        potential_names = deep_search(item, target_keys=["textAtom", "text"])
                        clean_names = []
                        for p in potential_names:
                            if isinstance(p, dict) and "text" in p: clean_names.append(p["text"])
                            elif isinstance(p, str): clean_names.append(p)
                        
                        name = "Нет названия"
                        if clean_names:
                            best_name = max(clean_names, key=len)
                            if len(best_name) > 10: name = best_name

                        # 2. ЦЕНА (Ищем символ рубля)
                        potential_prices = deep_search(item, value_condition=lambda x: "₽" in x and len(x) < 20)
                        price = potential_prices[0] if potential_prices else "Нет цены"
                        
                        # Если цена не найдена символом, пробуем через структуру
                        if price == "Нет цены":
                             pv2 = deep_search(item, target_keys=["priceV2"])
                             if pv2:
                                 try: price = pv2[0]["price"][0]["text"]
                                 except: pass

                        # 3. ИЗОБРАЖЕНИЕ (Новый блок)
                        # Ищем ссылки, заканчивающиеся на расширения картинок
                        potential_images = deep_search(
                            item,
                            target_keys=["src", "url", "link"], # Возможные ключи
                            value_condition=lambda x: isinstance(x, str) and x.startswith("http") and (".jpg" in x or ".jpeg" in x or ".webp" in x or ".png" in x)
                        )
                        
                        # Фильтруем мусор (иконки, SVG и т.д., если они попали), берем первую нормальную ссылку
                        image_url = "Нет картинки"
                        for img in potential_images:
                            # Ozon картинки обычно лежат на cdn или ir.ozon.ru
                            if "ozon" in img or "cdn" in img:
                                image_url = img
                                break
                        
                        # Если ничего специфичного не нашли, берем первую попавшуюся
                        if image_url == "Нет картинки" and potential_images:
                            image_url = potential_images[0]

                        if name != "Нет названия":
                            result.append([name, price, image_url])
                    
                    break 
        except Exception as e:
            continue

    if not found_something:
        print("Данные не найдены.")

    return result

if __name__ == '__main__':
    if not user_agent or not cookies_dict:
        user_agent, cookies_dict = get_cookies()
    
    query = "ps vita"
    all_items = []
    
    response, total_pages = get_page(query, 1, cookies_dict, user_agent)
    
    if response:
        if response.status_code == 403:
             print("Обновляем куки...")
             user_agent, cookies_dict = get_cookies()
             response, total_pages = get_page(query, 1, cookies_dict, user_agent)

        items = get_data_json(response.json())
        all_items.extend(items)
        
        print(f"Страниц всего: {total_pages}")
        max_pages = min(total_pages, 3)

        for page in range(2, max_pages + 1):
            time.sleep(1.5)
            resp = get_page(query, page, cookies_dict, user_agent)[0]
            if resp:
                all_items.extend(get_data_json(resp.json()))

    print(f"\nРезультат: собрано {len(all_items)} товаров")
    
    # Выводим красивые результаты
    for i in all_items[:5]: # Показываем первые 5 для примера
        print(f"Товар: {i[0][:40]}... | Цена: {i[1]} | Фото: {i[2]}")