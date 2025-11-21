from flask import Flask, jsonify, request, send_file
import json
import os

app = Flask(__name__)

# Обработчик ошибки JSON decode
@app.errorhandler(500)
def handle_internal_error(error):
    if isinstance(error.original_exception, json.JSONDecodeError):
        return jsonify({
            "error": "Invalid JSON format",
            "message": "Неверный формат JSON данных"
        }), 400
    return jsonify({"error": "Internal server error"}), 500

# Главная страница
@app.route('/')
def index():
    return send_file('index.html')

# Статус API
@app.route('/status')
def status():
    return jsonify({
        "status": "active",
        "message": "API работает корректно",
        "available_parsers": ["ozon", "wildberries", "yandex"]
    })

# Ozon данные
@app.route('/api/ozon')
def get_ozon_data():
    try:
        if os.path.exists('ozon_parsed_data.json'):
            with open('ozon_parsed_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({
                "source": "ozon",
                "data": data
            })
        else:
            return jsonify({
                "error": "File not found",
                "message": "Файл ozon_parsed_data.json не найден"
            }), 404
    except Exception as e:
        return jsonify({
            "error": "Error reading Ozon data",
            "message": str(e)
        }), 500

# Wildberries данные
@app.route('/api/wildberries')
def get_wildberries_data():
    try:
        if os.path.exists('wb_parsed_data.json'):
            with open('wb_parsed_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({
                "source": "wildberries",
                "data": data
            })
        else:
            return jsonify({
                "error": "File not found",
                "message": "Файл wb_parsed_data.json не найден"
            }), 404
    except Exception as e:
        return jsonify({
            "error": "Error reading Wildberries data",
            "message": str(e)
        }), 500

# Яндекс Маркет данные
@app.route('/api/yandex')
def get_yandex_data():
    try:
        if os.path.exists('yandex_parsed_data.json'):
            with open('yandex_parsed_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({
                "source": "yandex_market",
                "data": data
            })
        else:
            return jsonify({
                "error": "File not found",
                "message": "Файл yandex_parsed_data.json не найден"
            }), 404
    except Exception as e:
        return jsonify({
            "error": "Error reading Yandex Market data",
            "message": str(e)
        }), 500

# Запуск парсера (пример эндпоинта)
@app.route('/api/parse/<parser_name>', methods=['POST'])
def run_parser(parser_name):
    parsers = {
        'ozon': 'parser_ozon.py',
        'wildberries': 'parser_wb.py', 
        'yandex': 'parser_yamarket.py'
    }
    
    if parser_name not in parsers:
        return jsonify({
            "error": "Parser not found",
            "available_parsers": list(parsers.keys())
        }), 404
    
    try:
        # Здесь можно добавить логику запуска парсера
        # Например, через subprocess или импорт модуля
        return jsonify({
            "message": f"Парсер {parser_name} запущен",
            "parser_file": parsers[parser_name]
        })
    except Exception as e:
        return jsonify({
            "error": f"Error running parser {parser_name}",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)