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
OUTPUT_JSON_FILE = "ozon_parsed_data.json" # Имя файла для сохранения

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
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
            print(" Ждем прогрузки защиты (6 сек)...")
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

# --- ПАРСИНГ ДАННЫХ ---
def get_data_json(response_json):
    result = []
    widget_states = response_json.get("widgetStates", {})
    
    debug_saved = False

    # Универсальный рекурсивный поисковик значений
    def get_all_values(data):
        values = []
        if isinstance(data, dict):
            for v in data.values():
                values.extend(get_all_values(v))
        elif isinstance(data, list):
            for item in data:
                values.extend(get_all_values(item))
        elif isinstance(data, (str, int, float)):
            values.append(data)
        return values

    # Поиск по ключам (для ссылок и картинок)
    def deep_search_keys(data, keys):
        found = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in keys: found.append(v)
                found.extend(deep_search_keys(v, keys))
        elif isinstance(data, list):
            for item in data: found.extend(deep_search_keys(item, keys))
        return found

    for key, value_str in widget_states.items():
        try:
            data = json.loads(value_str)
            if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
                
                for item in data["items"]:
                    # Собираем все важные блоки, где может быть инфа
                    main_state = item.get('mainState', [])
                    right_state = item.get('rightState', [])
                    label_state = item.get('labelState', {}) 
                    
                    # --- 1. НАЗВАНИЕ ---
                    name = "Нет названия"
                    all_main_texts = [str(x) for x in get_all_values(main_state) if isinstance(x, str)]
                    candidates = [t for t in all_main_texts if len(t) > 10 and not t.startswith("http")]
                    if candidates:
                        name = max(candidates, key=len)

                    # --- 2. ЦЕНА ---
                    price = "Нет цены"
                    all_right_values = get_all_values(right_state)
                    price_cands = [str(x) for x in all_right_values if isinstance(x, str) and "₽" in x and len(x) < 15]
                    if price_cands:
                        price = price_cands[0]
                    else:
                        pv2 = deep_search_keys(item, ["priceV2"])
                        if pv2: 
                             try: price = pv2[0]["price"][0]["text"]
                             except: pass

                    # --- 3. ФОТО ---
                    image_url = "Нет фото"
                    imgs = deep_search_keys(item, ["src", "link", "url"])
                    valid_imgs = [x for x in imgs if isinstance(x, str) and "ozon" in x and ("jpg" in x or "webp" in x)]
                    if valid_imgs: image_url = valid_imgs[0]

                    # --- 4. АРТИКУЛ ---
                    article = "Нет артикула"
                    direct_id = item.get("id")
                    if direct_id:
                        article = str(direct_id)
                    
                    if article == "Нет артикула":
                        links = deep_search_keys(item, ["link", "href", "url"])
                        product_links = [l for l in links if isinstance(l, str) and "/product/" in l]
                        if product_links:
                            main_link = product_links[0]
                            match = re.search(r'-(\d+)(?:/|\?|$)', main_link)
                            if match:
                                article = match.group(1)
                            else:
                                match_simple = re.search(r'/product/(\d+)', main_link)
                                if match_simple:
                                    article = match_simple.group(1)

                    # --- 5. РЕЙТИНГ ---
                    rating = "0.0"
                    all_content_values = get_all_values(main_state) + get_all_values(right_state) + get_all_values(label_state)
                    found_floats = []
                    for val in all_content_values:
                        s_val = str(val).strip().replace(',', '.')
                        if re.match(r'^[3-5][.]\d{1,2}$', s_val) or s_val == "5":
                            try:
                                f = float(s_val)
                                if 3.0 <= f <= 5.0:
                                    found_floats.append(f)
                            except: pass
                    
                    best_rating = [f for f in found_floats if f % 1 != 0]
                    if best_rating:
                        rating = str(best_rating[0])
                    elif found_floats:
                         rating = str(found_floats[0])

                    # --- 6. БРЕНД ---
                    brand = "Не указан"
                    logo_vals = get_all_values(item.get('brandLogo', {}))
                    logo_strs = [str(s) for s in logo_vals if isinstance(s, str)]
                    for s in logo_strs:
                        m = re.search(r'/brand/([a-zA-Z0-9-]+)-', s)
                        if m: 
                            brand = m.group(1).replace('-', ' ').title()
                            break
                    
                    if (brand == "Не указан" or brand == "Noname") and name != "Нет названия":
                         clean_name_start = re.sub(r'^(Смартфон|Телефон|Восстановленный)\s+', '', name, flags=re.IGNORECASE)
                         first_word = clean_name_start.split()[0]
                         first_word = re.sub(r'[^\w]', '', first_word)
                         known_brands = ["Apple", "Sony", "Samsung", "Xiaomi", "Poco", "Realme", "Honor", "Tecno", "Infinix", "Asus"]
                         if first_word in known_brands or (len(first_word) > 2 and re.match(r'^[A-Z]', first_word)):
                             brand = first_word

                    if brand.lower() in ["для", "чехол", "стекло"]: brand = "Не указан"

                    if name != "Нет названия":
                        # !!! ИЗМЕНЕНИЕ: ТЕПЕРЬ СОХРАНЯЕМ КАК СЛОВАРЬ (DICT), А НЕ СПИСОК !!!
                        item_dict = {
                            "article": article,
                            "name": name,
                            "price": price,
                            "rating": rating,
                            "brand": brand,
                            "image_url": image_url
                        }
                        result.append(item_dict)
        except Exception: continue

    return result
                    
# --- ЗАПУСК ---
if __name__ == '__main__':
    user_agent = load_data(UA_FILE)
    cookies_dict = load_data(COOKIES_FILE)

    if not check_cookies_validity(cookies_dict, user_agent):
        user_agent, cookies_dict = get_new_cookies()
        if not cookies_dict: exit()

    query = "ps5"
    all_items = []
    
    print(f"\n Ищем: {query}")
    response, total_pages = get_page(query, 1, cookies_dict, user_agent)
    
    if response:
        # Получаем первую страницу
        if response.status_code == 403:
             print(" 403. Обновляем куки...")
             user_agent, cookies_dict = get_new_cookies()
             response, total_pages = get_page(query, 1, cookies_dict, user_agent)

        if response and response.status_code == 200:
            data = response.json()
            all_items.extend(get_data_json(data)) # Сразу добавляем
        
            # Парсим остальные страницы (ограничим до 3 для примера)
            limit_pages = min(total_pages, 3)
            for page in range(2, limit_pages + 1):
                time.sleep(1.5)
                resp, _ = get_page(query, page, cookies_dict, user_agent)
                if resp and resp.status_code == 200:
                    all_items.extend(get_data_json(resp.json()))

    print(f"\n Собрано: {len(all_items)}")
    
    # --- СОХРАНЕНИЕ В JSON ФАЙЛ ---
    if all_items:
        print(f" Сохраняю данные в {OUTPUT_JSON_FILE}...")
        save_data(OUTPUT_JSON_FILE, all_items)
        print(" Готово!")
        # --- ВЫВОД ТАБЛИЦЫ  ---
    print("=" * 160) 
    header = f"{'АРТИКУЛ':<12} | {'ЦЕНА':<10} | {'РЕЙТИНГ':<7} | {'БРЕНД':<12} | {'НАЗВАНИЕ':<35} | {'ФОТО'}"
    print(header)
    print("=" * 160)
    
    for item in all_items[:15]:
        # Теперь обращаемся по ключам
        name_short = (item["name"][:33] + '..') if len(item["name"]) > 35 else item["name"]
        brand_short = (item["brand"][:12]) if len(item["brand"]) > 12 else item["brand"]
        
        row = f"{item['article']:<12} | {item['price']:<10} | {item['rating']:<7} | {brand_short:<12} | {name_short:<35} | {item['image_url']}"
        print(row)