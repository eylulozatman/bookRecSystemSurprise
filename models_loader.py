# models_loader.py
from surprise import dump
import pandas as pd
from collections import defaultdict
from surprise import Trainset

def load_models_and_data():
    try:
        _, user_based = dump.load('models/user_based_model')
        _, item_based = dump.load('models/item_based_model')
        
        df = pd.read_csv('models/newbookdata.csv', dtype={'User-ID': str, 'ISBN': str})
        df.columns = ['User-ID', 'ISBN', 'Book-Rating', 'Book-Title', 'Book-Author', 'Image-URL-M']
        
        book_info = {
            row['ISBN']: {
                'title': row['Book-Title'],
                'author': row['Book-Author'],
                'image_url': row['Image-URL-M']
            } for _, row in df.iterrows()
        }

        user_history = defaultdict(list)
        for _, row in df.iterrows():
            user_history[row['User-ID']].append({
                'isbn': row['ISBN'],
                'title': row['Book-Title'],
                'rating': row['Book-Rating'],
                'author': row['Book-Author'],
                'image_url': row['Image-URL-M']
            })
        
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


