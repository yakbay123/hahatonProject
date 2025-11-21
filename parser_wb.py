import json
import time
import random
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
SEARCH_QUERY = "iphone 15"
PAGES_TO_PARSE = 3
SCROLL_PAUSE_TIME = 0.7 
OUTPUT_JSON_FILE = "wb_parsed_data.json" # Имя файла для сохранения

# --- ФУНКЦИЯ КАРТИНКИ ---
def get_big_image_url(thumb_url):
    """
    Превращает ссылку на миниатюру (c246x328) в ссылку на оригинал (big).
    """
    if not thumb_url or "base64" in thumb_url:
        return "Нет фото (не прогрузилось)"
    
    try:
        parts = thumb_url.split('/images/')
        if len(parts) == 2:
            return f"{parts[0]}/images/big/1.webp"
        return thumb_url
    except:
        return thumb_url

# --- БРАУЗЕРНЫЕ ФУНКЦИИ ---
def human_scroll(driver):
    print("Скроллим для загрузки картинок...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
        time.sleep(SCROLL_PAUSE_TIME)
        
        if driver.execute_script("return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 300;"):
            break
        last_height = driver.execute_script("return document.body.scrollHeight")

def parse_html_content(html_source):
    soup = BeautifulSoup(html_source, 'html.parser')
    products = []
    
    # Ищем карточки
    cards = soup.find_all('article', class_=lambda x: x and 'product-card' in x)
    if not cards:
        cards = soup.find_all('div', class_=lambda x: x and 'product-card' in x)

    for card in cards:
        try:
            # --- АРТИКУЛ ---
            article_raw = card.get('id', '').replace('c', '')
            if not article_raw: article_raw = card.get('data-nm-id', '0')
            
            # --- НАЗВАНИЕ И БРЕНД ---
            name_tag = card.find('span', class_='product-card__name')
            brand_tag = card.find('span', class_='product-card__brand')
            name = name_tag.text.strip().replace('/', '') if name_tag else "No Name"
            brand = brand_tag.text.strip() if brand_tag else "No Brand"
            
            # --- ЦЕНА ---
            price_tag = card.find('ins', class_='price__lower-price')
            if not price_tag: price_tag = card.find('span', class_='price__lower-price')
            price = 0
            if price_tag:
                price_text = price_tag.text.strip().replace('\xa0', '').replace('₽', '').replace(' ', '')
                try: price = int(price_text)
                except: pass
            
            # --- РЕЙТИНГ ---
            rating_tag = card.find('span', class_='address-rate-mini')
            rating = rating_tag.text.strip() if rating_tag else "0"

            # --- ФОТО ---
            img_tag = card.find('img')
            image_link = "Нет фото"
            
            if img_tag:
                src = img_tag.get('src')
                if src:
                    image_link = src
                
                if image_link.startswith('//'):
                    image_link = "https:" + image_link
                
                image_link = get_big_image_url(image_link)
                
                if article_raw and price > 0:
                    products.append({
                    'id': article_raw,
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'rating': rating,
                    'image': image_link
                })
        except Exception:
            continue
    return products

# --- MAIN ---
def main():
    print(f"Запуск надежного парсера (Selenium + HTML Images): {SEARCH_QUERY}")
    options = uc.ChromeOptions()
    # options.add_argument('--headless') 
    
    try:
        with uc.Chrome(options=options) as driver:
            driver.get("https://www.wildberries.ru")
            time.sleep(3)
            
            all_items = []
            for page in range(1, PAGES_TO_PARSE + 1):
                print(f"\nСтраница {page}...")
                if page == 1:
                    url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={SEARCH_QUERY}"
                else:
                    url = f"https://www.wildberries.ru/catalog/0/search.aspx?page={page}&sort=popular&search={SEARCH_QUERY}"
                
                driver.get(url)
                human_scroll(driver) 
                time.sleep(2)
                
                html = driver.page_source
                items = parse_html_content(html)
                
                print(f"Найдено: {len(items)} шт.")
                all_items.extend(items)

            # --- СОХРАНЕНИЕ В JSON  ---
            if all_items:
                print(f"\nСохраняю данные в файл {OUTPUT_JSON_FILE}...")
                with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_items, f, ensure_ascii=False, indent=4)
                print("Файл успешно сохранен!")

            # --- ВЫВОД В КОНСОЛЬ ---
            print(f"ИТОГО СОБРАНО: {len(all_items)}")
            print("=" * 180)
            header = f"{'АРТИКУЛ':<12} | {'ЦЕНА':<10} | {'РЕЙТ':<5} | {'БРЕНД':<12} | {'НАЗВАНИЕ':<35} | {'ФОТО'}"
            print(header)
            print("=" * 180)
            
            for p in all_items[:30]:
                name_cut = (p['name'][:33] + '..') if len(p['name']) > 35 else p['name']
                brand_cut = (p['brand'][:12]) if len(p['brand']) > 12 else p['brand']
                
                row = f"{p['id']:<12} | {p['price']:<10} | {p['rating']:<5} | {brand_cut:<12} | {name_cut:<35} | {p['image']}"
                print(row)

    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()