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
   