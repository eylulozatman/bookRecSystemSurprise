from flask import Blueprint, request, jsonify, render_template
import pandas as pd
import csv
import os

from recommend_algorithm import get_hybrid_recommendations
from models_loader import load_models_and_data
models = load_models_and_data()

user_service_bp = Blueprint('user_service', __name__)

BOOK_INFO_CSV = 'models/book_info.csv'
COMPLETE_CSV = 'models/newbookdata.csv'

@user_service_bp.route('/api/reload-models', methods=['POST'])
def reload_models():
    global models
    try:
        load_models_and_data()
        print("✅ Models reloaded manually.")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



@user_service_bp.route('/user/<int:user_id>/service')
def user_service(user_id):
    return render_template('userService.html', user_id=user_id)


@user_service_bp.route('/api/search/books/<query>', methods=['GET'])
def search_books(query):
    page = int(request.args.get('page', 1))
    size = 5

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

    new_row = [user_id, isbn, rating, title, author, image]
    with open(COMPLETE_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(new_row)

    # Burada model güncelleme kodunu ekle (isteğe bağlı)

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
        return jsonify({
            'success': False,
            'message': 'No books found',
            'books': [],
            'total': 0,
            'page': 1,
            'per_page': per_page,
            'total_pages': 0
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'books': [],
            'total': 0,
            'page': 1,
            'per_page': per_page,
            'total_pages': 0
        }), 500



@user_service_bp.route('/api/user/<user_id>/has-rated', methods=['GET'])
def has_user_rated(user_id):
    try:
        df = pd.read_csv(COMPLETE_CSV, dtype=str, on_bad_lines='skip')
        count = df[df['User-ID'] == str(user_id)].shape[0]
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@user_service_bp.route('/api/random-books', methods=['GET'])
def get_random_books():
    exclude = request.args.getlist('exclude')
    try:
        df = pd.read_csv(BOOK_INFO_CSV, dtype=str, on_bad_lines='skip')
        df = df[~df['ISBN'].isin(exclude)]
        sampled = df.sample(n=10) if len(df) >= 10 else df
        books = sampled[['ISBN', 'Book-Title', 'Book-Author', 'Image-URL-M']].to_dict(orient='records')
        return jsonify({'success': True, 'books': books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@user_service_bp.route('/api/user/<user_id>/hybrid-recommend', methods=['GET'])
def get_recommendations(user_id):
    global models
    try:
        # İlk deneme
        result, error = get_hybrid_recommendations(models, str(user_id))
        if not error:
            return jsonify({'success': True, **result})
        
        # İlk denemede başarısızsa modelleri yeniden yükle
        print(f"⚠️ First hybrid recommend failed for user {user_id}: {error}")
        print("🔄 Reloading models...")
        from models_loader import load_models_and_data
        models = load_models_and_data()

        # Tekrar dene
        result, error = get_hybrid_recommendations(models, str(user_id))
        if not error:
            print(f"✅ Success after model reload for user {user_id}")
            return jsonify({'success': True, **result})
        
        # Hâlâ başarısızsa, logla ve hata döndür
        print(f"❌ Recommendation failed even after reload for user {user_id}: {error}")
        return jsonify({'success': False, 'error': error}), 400

    except Exception as e:
        print(f"🔥 Unexpected exception in hybrid-recommend for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
