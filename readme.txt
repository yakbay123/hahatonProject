Для работы агрегатора необходимо скачать, питон  и несколько зависимостей они будут приведены ниже по ссылкам:
    0.1 для начала необходимо скачать компелятор питона:
        https://www.python.org/
    0.2 после чего нужно установить несколько зависимостей через терминал который открывается через сочитание клавиш виндувс+r и в выподающей менюшке необходимо в вести cmd
    0.3 скачивание самой программы через клонирование из гитхаба для этого в меню консоли необхопрописать:
         git clone <URL репозитория>
         cd HANATONPROJECT
    0.4 после чего в терминале необходимо прописать:
         pip install -r requirements.txt
        Если файла requirements.txt нет, установите следующие пакеты:
         pip install requests beautifulsoup4 selenium flask pandas
Инструкция по запуску агрегатора

1. Запуск
    python app.py
   
2. запустить нужный парсер
    python parser_ozon.py
    python parser_wb.py
    python parser_yamarket.py

3. Результаты будут находится в этих файлах и в консоли
    ozon_parsed_data.json - данные с Ozon
    wb_parsed_data.json - данные с Wildberries
    yandex_parsed_data.json - данные с Яндекс.Маркет
   
структура проэкта:
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