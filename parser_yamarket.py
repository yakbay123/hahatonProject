import json
import time
import random
import os
import re
import module
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import unquote

# --- КОНФИГУРАЦИЯ ---
SEARCH_QUERY = module.a
OUTPUT_JSON_FILE = "yandex_parsed_data.json"
PAGES_TO_PARSE = 2

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def save_json(data, filename):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# --- БРАУЗЕРНЫЕ ФУНКЦИИ ---
def random_sleep(min_s=2, max_s=5):
    time.sleep(random.uniform(min_s, max_s))

def human_scroll(driver):
    print(" Скроллим страницу...")
    for _ in range(random.randint(3, 5)):
        driver.execute_script(f"window.scrollBy(0, {random.randint(400, 800)});")
        random_sleep(1, 2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    random_sleep(2, 3)

# --- ФУНКЦИЯ ПОИСКА АРТИКУЛА (МЕТОД "КУВАЛДА") ---
def extract_yandex_id(card_soup):
    """
    Ищет ID во всем HTML коде карточки, используя регулярные выражения.
    """
    # Превращаем объект карточки в строку текста
    html_str = str(card_soup)
    
    # 1. Поиск "skuId": "12345" (часто бывает в JSON внутри data-атрибутов)
    sku_id_match = re.search(r'"skuId"\s*[:=]\s*["\']?(\d+)', html_str)
    if sku_id_match:
        return sku_id_match.group(1)
    
    # 2. Поиск параметра sku=12345 в ссылках
    sku_param_match = re.search(r'sku=(\d+)', html_str)
    if sku_param_match:
        return sku_param_match.group(1)

    # 3. Поиск ID товара в пути ссылки: product--name/12345
    # Ищем число от 6 до 12 цифр после слэша, перед знаком вопроса или кавычкой
    product_id_match = re.search(r'product--[^/]+/(\d{6,15})', html_str)
    if product_id_match:
        return product_id_match.group(1)

    # 4. Резерв: поиск data-id="12345"
    data_id_match = re.search(r'data-id=["\'](\d+)["\']', html_str)
    if data_id_match:
        return data_id_match.group(1)

    return "Нет артикула"

# --- ПАРСИНГ HTML ---
def parse_yandex_html(html_source):
    soup = BeautifulSoup(html_source, 'html.parser')
    products = []
    
    # Ищем карточки
    cards = soup.find_all('article', {'data-auto': 'searchOrganic'})
    if not cards:
        cards = soup.find_all('div', {'data-zone-name': 'snippet-card'})

    print(f" Найдено карточек в HTML: {len(cards)}")

    for card in cards:
        try:
            # --- 1. АРТИКУЛ ---
            article = extract_yandex_id(card)

            # --- 2. НАЗВАНИЕ ---
            name = "Нет названия"
            name_el = card.find('h3')
            if not name_el: name_el = card.find('span', {'data-auto': 'snippet-title'})
            if not name_el:
                 links = card.find_all('a')
                 for l in links:
                     if len(l.text.strip()) > 15: 
                         name_el = l
                         break
            if name_el: name = name_el.text.strip()

            # --- 3. ЦЕНА ---
            price = "Нет цены"
            price_el = card.find('span', {'data-auto': 'snippet-price-current'})
            if price_el:
                price = price_el.text.strip().replace('\xa0', '').replace('₽', '')
            else:
                pt = card.find(string=re.compile(r'\d{2,}\s\d{3}'))
                if pt: price = pt.parent.text.strip().replace('\xa0', '').replace('₽', '')

            # --- 4. БРЕНД ---
            brand = "Не определен"
            known_brands = ["Apple", "Samsung", "Xiaomi", "Realme", "Poco", "Honor", "Sony", 
                            "Infinix", "Tecno", "Asus", "OnePlus", "Google", "Huawei", "Vivo", "Oppo"]
            
            for kb in known_brands:
                if kb.lower() in name.lower():
                    brand = kb
                    break
            if brand == "Не определен" and name != "Нет названия":
                clean_name = re.sub(r'^(Смартфон|Телефон|Мобильный телефон|Планшет|Умные часы)\s+', '', name, flags=re.IGNORECASE)
                first_word = clean_name.split()[0]
                if re.match(r'^[A-Za-z0-9]+$', first_word):
                    brand = first_word

            # --- 5. РЕЙТИНГ ---
            rating = "0.0"
            texts = card.get_text(separator=" ").split()
            for t in texts:
                if re.match(r'^[3-5][.,]\d$', t):
                    rating = t.replace(',', '.')
                    break

            # --- 6. ФОТО ---
            image_url = "Нет фото"
            imgs = card.find_all('img')
            for img in imgs:
                src = img.get('src') or img.get('data-src')
                if src and "//" in src and "avatars" in src and "mini" not in src:
                    if src.startswith('//'): src = "https:" + src
                    image_url = src
                    break
            
            # Добавляем
            if name != "Нет названия":
                products.append({
                    "article": article,
                    "name": name,
                    "price": price,
                    "rating": rating,
                    "brand": brand,
                    "image_url": image_url
                })

        except Exception:
            continue

    return products

# --- ГЛАВНАЯ ФУНКЦИЯ ---
if __name__ == "__main__":
    print("Запуск парсера Яндекс Маркета...")
    
    options = uc.ChromeOptions()
    # options.add_argument('--headless') 
    
    try:
        with uc.Chrome(options=options) as driver:
            driver.get("https://market.yandex.ru/")
            print("Ждем 5 сек...")
            time.sleep(5) 
            
            all_data = []

            for page in range(1, PAGES_TO_PARSE + 1):
                print(f"\nОбработка страницы {page}...")
                url = f"https://market.yandex.ru/search?text={SEARCH_QUERY.replace(' ', '%20')}&page={page}"
                driver.get(url)
                
                if "showcaptcha" in driver.current_url:
                    print("КАПЧА! Решите её и нажмите Enter...")
                    input()
                
                human_scroll(driver)
                items = parse_yandex_html(driver.page_source)
                all_data.extend(items)
                print(f"Найдено: {len(items)}")
                random_sleep(3, 5)

            if all_data:
                print(f"\nСохранено {len(all_data)} товаров в {OUTPUT_JSON_FILE}...")
                save_json(all_data, OUTPUT_JSON_FILE)
                
                print("=" * 160)
                print(f"{'АРТИКУЛ':<15} | {'ЦЕНА':<10} | {'РЕЙТ':<5} | {'БРЕНД':<12} | {'НАЗВАНИЕ':<40}")
                print("=" * 160)
                for p in all_data[:15]:
                    name_short = (p['name'][:37] + '..') if len(p['name']) > 40 else p['name']
                    # Обрезаем длинные имена для консоли
                    print(f"{p['article']:<15} | {p['price']:<10} | {p['rating']:<5} | {p['brand']:<12} | {name_short:<40}")
            else:
                print("Товары не найдены.")

    except Exception as e:
        print(f"Ошибка: {e}")