markdown

# Hanaton Project: Парсер товаров с маркетплейсов

Этот проект представляет собой веб-приложение и набор парсеров для сбора данных о товарах с популярных российских маркетплейсов: **Ozon**, **Wildberries** и **Яндекс.Маркет**.

## Структура проекта

HANATONPROJECT/
├── pycache/ # Кэшированные Python-файлы (автогенерация)
├── app.py # Основной файл веб-приложения
├── cookies_dict.txt # Файл с куками для парсеров
├── html.html # Вспомогательный HTML-файл
├── index.html # Главная страница веб-интерфейса
├── module.py # Вспомогательный модуль с общими функциями
├── ozon_parsed_data.json # Результаты парсинга Ozon
├── parser_ozon.py # Парсер для маркетплейса Ozon
├── parser_wb.py # Парсер для маркетплейса Wildberries
├── parser_yamarket.py # Парсер для маркетплейса Яндекс.Маркет
├── user_agent.txt # User-Agent строки для обхода блокировок
├── wb_cookies.json # Куки для Wildberries в JSON-формате
├── wb_parsed_data.json # Результаты парсинга Wildberries
├── wb_user_agent.txt # Специфичные User-Agent для Wildberries
└── yandex_parsed_data.json # Результаты парсинга Яндекс.Маркет
text


## Функциональность

- **Парсинг данных**: Сбор информации о товарах (название, цена, рейтинг, отзывы и т.д.)
- **Веб-интерфейс**: Простой способ запуска парсеров и просмотра результатов
- **Поддержка нескольких платформ**: Ozon, Wildberries, Яндекс.Маркет
- **Обход блокировок**: Использование cookies и user-agent для имитации реального пользователя

## Установка и настройка

1. **Клонируйте репозиторий**:
   ```bash
   git clone <URL репозитория>
   cd HANATONPROJECT

Установите зависимости:
bash

pip install requests beautifulsoup4 selenium flask

    Настройка cookies и user-agent:

        Обновите файлы cookies_dict.txt, wb_cookies.json при необходимости

        Проверьте актуальность user-agent в user_agent.txt и wb_user_agent.txt

Использование
Через веб-интерфейс:

    Запустите веб-приложение:
    bash

python app.py

    Откройте в браузере: http://localhost:5000

    Используйте интерфейс для запуска парсеров

Через командную строку:

Запустите нужный парсер напрямую:
bash

python parser_ozon.py
python parser_wb.py
python parser_yamarket.py
