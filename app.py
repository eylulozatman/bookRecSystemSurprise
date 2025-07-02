from flask import Flask, render_template ,jsonify,request
import csv
from models_loader import load_models_and_data
from recommend_algorithm import get_user_based_recommendations, get_item_based_recommendations 
from userService import user_service_bp
from model_trainer import schedule_retrain
from recommend_algorithm2 import get_user_based_recommendations1, get_item_based_recommendations1


app = Flask(__name__)
app.register_blueprint(user_service_bp)

schedule_retrain(hour=3) 
USERS_CSV = 'models/users.csv'
models = load_models_and_data()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/autofill/users/<prefix>')
def search_users(prefix):
    if not models:
        return jsonify({'error': 'Models not loaded'}), 500
    matches = [{'user_id': uid} for uid in models['all_users'] if str(uid).startswith(prefix)]
    return jsonify({'results': matches[:10]})


@app.route('/api/autofill/books/<prefix>')
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

        result, error = get_user_based_recommendations(models, user_id, k)
        if error:
            return jsonify({'success': False, 'error': error}), 404

        return jsonify({'success': True, **result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/item-based/recommend', methods=['POST'])
def item_based_recommend():
    try:
        data = request.get_json()
        isbn = str(data['isbn'])
        k = int(data.get('k', 5))

        result, error = get_item_based_recommendations(models, isbn, k)
        if error:
            return jsonify({'success': False, 'error': error}), 404

        return jsonify({'success': True, **result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/login/<user_id>', methods=['POST'])
def login(user_id):
    try:
        with open(USERS_CSV, mode='r', newline='') as file:
            reader = csv.reader(file)
            users = list(reader)
    except FileNotFoundError:
        users = []

    user = None
    for row in users:
        if row[0] == str(user_id):
            user = row
            break

    if not user:
        with open(USERS_CSV, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([user_id])
        user = [str(user_id)]

    if user:
        return jsonify({'success': True})
    return jsonify({'success': False})



@app.route('/login-handle/<int:user_id>')
def user_service(user_id):
    return render_template('userService.html', user_id=user_id)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)  