import sqlite3
import os
from flask import Flask, g, jsonify, make_response, abort, request

# Config
DATABASE = '/tmp/file_structure.db'
DEBUG = True
SECRET_KEY = 'asdf'
USERNAME = 'admin'
PASSWORD = 'admin'

app = Flask(__name__)
app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'file_structure.db')))
app.config['JSON_AS_ASCII'] = False

descendants_lst = []
accessing_the_db_objects = 'SELECT id, name, type, parent FROM object'


def connect_db():
    """Общая функция установления соединения с БД"""

    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    """Функция для создания таблиц БД"""
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def get_db():
    """Соединение с БД, если оно еще не установлено"""
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


def request_to_db(row_request):
    """Запрос к БД"""
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(row_request)
    except:
        abort(500)
    data = cur.fetchall()
    result = get_dict(data)
    return result


def get_dict(data):
    """Получение списка словарей из объекта sqlite3.row"""
    return [dict(row) for row in data]


def check_nested_elements(lst):
    """Проверка вложенных объектов, есть ли среди них папки, если их нет, возвращаем список обратно"""
    print(f'check_nested_elements(lst)')
    lst_type_folder = [i for i in lst if i['type'] == 'folder']
    if not lst or not lst_type_folder:
        return lst
    return search_descendants_3(lst_type_folder)


# def search_descendants(lst):
#     """Поиск всех потомков"""
#     print(f'Run search_descendants_2 ({lst})')
#     if not lst:
#         return lst
#
#     lst_type_folder = [i for i in lst if i['type'] == 'folder']   #
#     descendants_lst = []
#     if not lst_type_folder:    #
#         descendants_lst.append(lst)
#         return descendants_lst
#     else:
#         for i in lst_type_folder:
#             lst = request_to_db(f"SELECT id, name, type, parent FROM object WHERE parent={i['id']}")
#             descendants_lst.append(lst)
#             search_descendants(lst)
#         return descendants_lst


def search_descendants_2(lst):
    """Поиск всех потомков"""
    print(f'Run search_descendants_2(lst)\n{lst}')
    descendant = []
    if lst[0]['type'] != 'folder':
        return jsonify(lst)

    get_object_descendant = request_to_db(f"{accessing_the_db_objects} WHERE parent={lst[0]['id']}")
    # print(get_object_descendant)

    if not get_object_descendant:
        return jsonify(lst)

    for i in get_object_descendant:
        descendant.append(search_descendants_2([i]))
        # result = i
        print(i['id'])
        result = {"id": i['id'],
                  "name": i['name'],
                  "type": i['type'],
                  "parent": i['parent'],
                  "descendant": descendant,  # Возвращает [<Response 88 bytes [200 OK]>] ???
                  }
        print(result)

    return jsonify(result)


def search_descendants_3(lst_type_folder):
    """Поиск потомков"""
    print(f'search_descendants_3(lst_type_folder)')
    for i in lst_type_folder:
        print(f'Цикл FOR')
        try:
            lst_db = request_to_db(f"{accessing_the_db_objects} WHERE parent={i['id']}")
        except:
            abort(500)
        if not lst_db:
            print(f'Список lst_db пустой, объектов нет {lst_db}')
            return
        descendants_lst.append(lst_db)
        check_nested_elements(lst_db)
    return descendants_lst


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Неверный запрос (страница не найдена)'}), 404)


@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Неверный запрос (не число)'}), 400)


@app.errorhandler(500)
def internal_server_error(error):
    return make_response(jsonify({'error': 'Ошибка сервера'}), 500)


@app.route('/')
def index():
    return '<h1>REST service structure of folders and files from the database</h1>'


@app.route('/api/v1/object/0', methods=["GET"])
@app.route('/api/v1/object/', methods=["GET"])
def get_all_objects():
    """Получение всех объектов из БД, с учетом GET параметра '?filter=name'"""
    get_param = request.args.get('filter')
    print(get_param)
    if get_param:
        objects = request_to_db(f'{accessing_the_db_objects} WHERE name LIKE "%{get_param}%"')
        if not objects:
            return make_response(jsonify({'error': 'Таких объектов не существует'}), 404)
    else:
        objects = request_to_db(f'{accessing_the_db_objects}')
    return jsonify(objects)


@app.route('/api/v1/object/<int:pk>', methods=["GET"])
def get_object(pk):
    object = request_to_db(f'{accessing_the_db_objects} WHERE id={pk}')
    if not object:
        return make_response(jsonify({'error': 'Объект не существует'}), 404)
    if object[0]['type'] != 'folder':
        print(f'Объект не папка, выводим объект')
        return jsonify(object)
    else:
        print(f'Объект возможно имеет потомков, выводим сам объект и всех потомков (если они есть)')
        descendants = request_to_db(f'{accessing_the_db_objects} WHERE parent={pk}')
        if not descendants:
            print(f'Потомков нет, выводим только объект')
            return jsonify(object)
        descendants_lst.clear()
        tmp = (check_nested_elements(descendants))
        if tmp != [] and tmp != descendants:
            print(f'Добавляем а к списку объектов из запроса БД')
            descendants.append(tmp)
        object.append(descendants)
        return jsonify(object)


@app.route('/api/v1/object/<string:pk>', methods=["GET"])
def get_object_str(pk):
    """Возвращаем ошибку, если запрос не число"""
    abort(400)


#  Рекурсивный запрос к БД (к функции tree()):
accessing_the_db_objects_tree = f"WITH cte AS ( " \
                                f"SELECT id, parent, '/' || name AS name " \
                                f"FROM object WHERE parent is null " \
                                f"UNION all " \
                                f"SELECT object.id, object.parent, cte.name || '/' || object.name " \
                                f"FROM cte, object ON object.parent = cte.id) " \
                                f"SELECT name FROM cte;"


@app.route('/api/v2/object/', methods=["GET"])
def tree():
    """Отображение иерархии (путей) объектов"""
    objects = request_to_db(f'{accessing_the_db_objects_tree}')
    return jsonify(objects)


@app.route('/api/v4/object/<int:pk>', methods=["GET"])
def view_tree(pk):
    """Древовидное отображение объектов"""
    object = request_to_db(f'{accessing_the_db_objects} WHERE id={pk}')
    return search_descendants_2(object)


@app.teardown_appcontext
def close_db(error):
    """Закрываем соединение с БД, если оно было установлено"""
    if hasattr(g, 'link_db'):
        g.link_db.close()


if __name__ == '__main__':
    app.run(debug=True)
