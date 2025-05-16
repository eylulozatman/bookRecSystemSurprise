from flask import Blueprint, request, jsonify, render_template
user_service_bp = Blueprint('user_service', __name__)
import os , math, csv 
import pandas as pd

BOOK_INFO_CSV = 'models/book_info.csv'
COMPLETE_CSV = 'models/newbookdata.csv'


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

    new_row = [user_id, isbn, rating, title, author, image]

    with open(COMPLETE_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(new_row)

    return jsonify({'success': True, 'message': f'Book {title} added for user {user_id}'})


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


@user_service_bp.route('/api/user/<user_id>/recommend', methods=['GET'])
def get_recommendations(user_id):
    try:
        # Kullanıcının kitaplarını oku
        user_books = set()
        user_ratings = {}
        all_users_books = {}
        all_users_ratings = {}

        with open(COMPLETE_CSV, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                uid, isbn, rating, title, author, image = row
                if uid == user_id:
                    user_books.add(isbn)
                    user_ratings[isbn] = float(rating)
                else:
                    all_users_books.setdefault(uid, set()).add(isbn)
                    all_users_ratings.setdefault(uid, {})[isbn] = float(rating)

        # Kullanıcıya en çok ortak kitabı olan kullanıcıları bul ve benzerlik skoru hesapla
        similarity_scores = []
        for other_uid, books_set in all_users_books.items():
            common_books = user_books.intersection(books_set)
            if not common_books:
                continue
                
            # Cosine similarity hesapla
            dot_product = 0
            user_norm = 0
            other_norm = 0
            
            for book in common_books:
                user_rating = user_ratings[book]
                other_rating = all_users_ratings[other_uid].get(book, 0)
                
                dot_product += user_rating * other_rating
                user_norm += user_rating ** 2
                other_norm += other_rating ** 2
                
            if user_norm == 0 or other_norm == 0:
                similarity = 0
            else:
                similarity = dot_product / (math.sqrt(user_norm) * math.sqrt(other_norm))
            
            similarity_scores.append((other_uid, similarity, len(common_books)))

        # Benzerlik skoruna göre sırala
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        top_neighbors = [uid for uid, sim, count in similarity_scores[:3]]  # ilk 3 komşu

        # Komşuların kitaplarından, kullanıcının olmayanları topla ve tahmini puan hesapla
        recommendations = {}
        book_counts = {}
        
        for neighbor in top_neighbors:
            neighbor_similarity = next(sim for uid, sim, cnt in similarity_scores if uid == neighbor)
            
            for isbn, rating in all_users_ratings[neighbor].items():
                if isbn not in user_books:
                    if isbn not in recommendations:
                        recommendations[isbn] = {
                            'title': '',
                            'author': '',
                            'image': '',
                            'weighted_sum': 0,
                            'similarity_sum': 0
                        }
                        book_counts[isbn] = 0
                    
                    recommendations[isbn]['weighted_sum'] += rating * neighbor_similarity
                    recommendations[isbn]['similarity_sum'] += neighbor_similarity
                    book_counts[isbn] += 1

        # Kitap bilgilerini ve tahmini puanları ekle
        rec_list = []
        with open(BOOK_INFO_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ISBN'] in recommendations:
                    rec = recommendations[row['ISBN']]
                    rec['title'] = row['Book-Title']
                    rec['author'] = row['Book-Author']
                    rec['image'] = row['Image-URL-M']
                    
                    # Tahmini puan hesapla (0-10 arasında)
                    if rec['similarity_sum'] > 0:
                        predicted = rec['weighted_sum'] / rec['similarity_sum']
                        predicted = max(0, min(10, predicted))  # 0-10 arasında kırp
                    else:
                        predicted = 5  # default
                        
                    rec_list.append({
                        'isbn': row['ISBN'],
                        'title': rec['title'],
                        'author': rec['author'],
                        'image': rec['image'],
                        'similarity': rec['similarity_sum'] / book_counts[row['ISBN']],
                        'predicted_rating': predicted
                    })

        # Tahmini puana göre sırala
        rec_list.sort(key=lambda x: x['predicted_rating'], reverse=True)
        
        return jsonify({
            'success': True, 
            'recommendations': rec_list[:5]  # en iyi 5 öneri
        })

    except Exception as e:
        print(f"Error in recommendations: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Error generating recommendations'
        }), 500