from flask import Flask, request, jsonify, render_template
from surprise import dump
import pandas as pd
import os
from collections import defaultdict
import numpy as np

app = Flask(__name__)

def load_models_and_data():
    try:
        # Load models
        _, user_based = dump.load('models/user_based_model')
        _, item_based = dump.load('models/item_based_model')
        
        # Load data
        df = pd.read_csv('newbookdata.csv', dtype={'User-ID': str, 'ISBN': str})
        df.columns = ['User-ID', 'ISBN', 'Book-Rating', 'Book-Title', 'Book-Author', 'Image-URL-M']
        
        # Book information
        book_info = {
            row['ISBN']: {
                'title': row['Book-Title'],
                'author': row['Book-Author'],
                'image_url': row['Image-URL-M']
            } for _, row in df.iterrows()
        }
        
        # User history
        user_history = defaultdict(list)
        for _, row in df.iterrows():
            user_history[row['User-ID']].append({
                'isbn': row['ISBN'],
                'title': row['Book-Title'],
                'rating': row['Book-Rating'],
                'author': row['Book-Author'],
                'image_url': row['Image-URL-M']
            })
        
        # Average ratings
        avg_ratings = df.groupby('ISBN')['Book-Rating'].mean().to_dict()
        
        return {
            'user_based': user_based,
            'item_based': item_based,
            'book_info': book_info,
            'user_history': dict(user_history),
            'avg_ratings': avg_ratings,
            'all_users': list(user_history.keys()),
            'all_books': list(book_info.keys())
        }
        
    except Exception as e:
        print(f"Error loading models: {str(e)}")
        return None

models = load_models_and_data()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search/users/<prefix>')
def search_users(prefix):
    if not models:
        return jsonify({'error': 'Models not loaded'}), 500
    matches = [{'user_id': uid} for uid in models['all_users'] if str(uid).startswith(prefix)]
    return jsonify({'results': matches[:10]})

@app.route('/api/search/books/<prefix>')
def search_books(prefix):
    if not models:
        return jsonify({'error': 'Models not loaded'}), 500
    matches = [{'isbn': isbn} for isbn in models['all_books'] if isbn.startswith(prefix)]
    return jsonify({'results': matches[:10]})

@app.route('/api/user-based/recommend', methods=['POST'])
def user_based_recommend():
    try:
        data = request.get_json()
        user_id = str(data['user_id'])
        k = int(data.get('k', 5))
        
        if user_id not in models['user_history']:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Find similar users
        user_inner_id = models['user_based'].trainset.to_inner_uid(user_id)
        neighbors = models['user_based'].get_neighbors(user_inner_id, k=5)
        
        similar_users = []
        for inner_id in neighbors:
            neighbor_id = models['user_based'].trainset.to_raw_uid(inner_id)
            similarity = models['user_based'].sim[user_inner_id][inner_id]
            similar_users.append({
                'user_id': neighbor_id,
                'similarity': round(float(similarity), 3)
            })
        
        # Calculate recommendations with normalized scores (1-10)
        read_books = {item['isbn'] for item in models['user_history'][user_id]}
        recommendations = []
        
        for neighbor in similar_users:
            for item in models['user_history'].get(neighbor['user_id'], []):
                if item['isbn'] not in read_books:
                    # Normalize the score to 1-10 range
                    raw_score = item['rating'] * neighbor['similarity']
                    normalized_score = max(1, min(10, round(raw_score, 2)))
                    
                    recommendations.append({
                        **item,
                        'predicted_score': normalized_score,
                        'similarity': neighbor['similarity']
                    })
        
        # Select top recommendations
        recommendations = sorted(recommendations, key=lambda x: -x['predicted_score'])[:k]
        
        return jsonify({
            'success': True,
            'similar_users': similar_users,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/item-based/recommend', methods=['POST'])
def item_based_recommend():
    try:
        data = request.get_json()
        isbn = str(data['isbn'])
        k = int(data.get('k', 5))
        
        # Find similar books
        book_inner_id = models['item_based'].trainset.to_inner_iid(isbn)
        neighbors = models['item_based'].get_neighbors(book_inner_id, k=k+1)[1:]
        
        similar_books = []
        for inner_id in neighbors:
            neighbor_isbn = models['item_based'].trainset.to_raw_iid(inner_id)
            similarity = models['item_based'].sim[book_inner_id][inner_id]
            
            similar_books.append({
                **models['book_info'].get(neighbor_isbn, {}),
                'isbn': neighbor_isbn,
                'similarity': round(float(similarity), 3),
                'avg_rating': round(models['avg_ratings'].get(neighbor_isbn, 0), 2)
            })
        
        return jsonify({
            'success': True,
            'source_book': models['book_info'].get(isbn, {}),
            'recommendations': similar_books
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)