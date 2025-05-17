#userService.py
from flask import Blueprint, request, jsonify, render_template

from model_trainer import incremental_update
import os , math, csv 
import pandas as pd
from models_loader import load_models_and_data
from recommend_algorithm import get_hybrid_recommendations

user_service_bp = Blueprint('user_service', __name__)



BOOK_INFO_CSV = 'models/book_info.csv'
COMPLETE_CSV = 'models/newbookdata.csv'

models = load_models_and_data()


@user_service_bp.route('/user/<int:user_id>/service')
def user_service(user_id):
    return render_template('userService.html', user_id=user_id)


@user_service_bp.route('/api/search/books/<query>', methods=['GET'])
def search_books(query):
    print(f"Received search query: {query}")
    page = int(request.args.get('page', 1)) 
    size = 10

    if not os.path.exists(BOOK_INFO_CSV):
        return jsonify({'success': False, 'message': 'Book data file not found'}), 404

    try:
        df = pd.read_csv(BOOK_INFO_CSV, dtype=str, on_bad_lines='skip')
        query_lower = query.lower()

        df['Book-Title'] = df['Book-Title'].fillna('')
        df['Book-Author'] = df['Book-Author'].fillna('')
        df['ISBN'] = df['ISBN'].fillna('')

        matches = df[
            df['Book-Title'].str.lower().str.contains(query_lower) |
            df['ISBN'].str.contains(query) |
            df['Book-Author'].str.lower().str.contains(query_lower)
        ]

        total_results = len(matches)
        start = (page - 1) * size
        end = start + size

        paginated = matches.iloc[start:end]
        books = paginated[['ISBN', 'Book-Title', 'Book-Author', 'Image-URL-M']].to_dict(orient='records')

        return jsonify({
            'success': True,
            'results': books,
            'total': total_results,
            'page': page,
            'size': size
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@user_service_bp.route('/api/user/<int:user_id>/added-isbns', methods=['GET'])
def get_added_isbns(user_id):
    try:
        df = pd.read_csv(COMPLETE_CSV, dtype=str, on_bad_lines='skip')
        user_books = df[df['User-ID'] == str(user_id)]
        isbns = user_books['ISBN'].dropna().unique().tolist()
        return jsonify({'success': True, 'isbns': isbns})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
   

@user_service_bp.route('/api/user/<user_id>/add-book', methods=['POST'])
def add_book(user_id):
    data = request.get_json()
    isbn = data.get('isbn')
    rating = data.get('rating')
    title = data.get('title')
    author = data.get('author')
    image = data.get('image')

    if not all([isbn, rating, title, author, image]):
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    new_row = [user_id, data['isbn'], data['rating'], data['title'], data['author'], data['image']]
    with open(COMPLETE_CSV, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(new_row)

    # 2. Modeli anlık güncelle
    incremental_update(str(user_id), data['isbn'], float(data['rating']))
    
    # 3. Bellekteki user_history'i güncelle
    if user_id not in models['user_history']:
        models['user_history'][user_id] = []
    
    models['user_history'][user_id].append({
        'isbn': data['isbn'],
        'title': data['title'],
        'rating': float(data['rating']),
        'author': data['author'],
        'image_url': data['image']
    })

    return jsonify({'success': True})

@user_service_bp.route('/mybooklist/<int:user_id>')
def my_book_list(user_id):
    return render_template('mybooklist.html', user_id=user_id)

@user_service_bp.route('/api/user/<user_id>/books', methods=['GET'])
def get_user_books(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = 10
    try:
        with open(COMPLETE_CSV, encoding='utf-8') as f:
            reader = csv.reader(f)
            user_books = [
                {'isbn': row[1], 'rating': row[2], 'title': row[3], 'author': row[4], 'image': row[5]}
                for row in reader if len(row) >= 6 and row[0] == str(user_id)
            ]
            total_books = len(user_books)
            start, end = (page - 1) * per_page, page * per_page
            books = user_books[start:end]

        return jsonify({
            'success': True,
            'books': books,
            'total': total_books,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_books + per_page - 1) // per_page
        })

    except FileNotFoundError:
        return jsonify({'success': False, 'message': 'No books found', 'books': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'books': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}), 500


@user_service_bp.route('/api/user/<user_id>/hybrid-recommend', methods=['GET'])
def get_recommendations(user_id):
    
    try:
        result, error = get_hybrid_recommendations(models, str(user_id))
        if error:
            return jsonify({'success': False, 'error': error}), 400
            
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500