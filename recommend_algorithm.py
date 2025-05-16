#algoritma 

def to_inner_id(model, raw_id, id_type='user'):
    try:
        if id_type == 'user':
            return model.trainset.to_inner_uid(raw_id)
        elif id_type == 'item':
            return model.trainset.to_inner_iid(raw_id)
    except ValueError:
        return None

def to_raw_id(model, inner_id, id_type='user'):
    try:
        if id_type == 'user':
            return model.trainset.to_raw_uid(inner_id)
        elif id_type == 'item':
            return model.trainset.to_raw_iid(inner_id)
    except ValueError:
        return None

def get_neighbors(model, inner_id, k=5):
    return model.get_neighbors(inner_id, k)

# --- USER-BASED with common books consideration ---

def get_user_based_similar_users(models, user_id, k=5, min_common_books=1):
    inner_id = to_inner_id(models['user_based'], user_id, 'user')
    if inner_id is None:
        return None, 'User not found'

    neighbors = get_neighbors(models['user_based'], inner_id, k * 5)  # Daha çok al, sonra filtrele
    user_books = {item['isbn'] for item in models['user_history'].get(user_id, [])}

    similar_users = []
    for neighbor_inner_id in neighbors:
        raw_id = to_raw_id(models['user_based'], neighbor_inner_id, 'user')
        neighbor_books = {item['isbn'] for item in models['user_history'].get(raw_id, [])}

        common_books = user_books & neighbor_books
        if len(common_books) >= min_common_books:
            similarity = models['user_based'].sim[inner_id][neighbor_inner_id]
            weighted_similarity = similarity * (len(common_books) / (len(user_books) + 1))  # +1: bölme hatası önleme

            similar_users.append({
                'user_id': raw_id,
                'similarity': round(float(similarity), 3),
                'common_books_count': len(common_books),
                'weighted_similarity': round(weighted_similarity, 3)
            })

    similar_users.sort(key=lambda x: x['weighted_similarity'], reverse=True)

    return similar_users[:k], None

def predict_user_based_score(item, similarity):
    raw_score = item['rating'] * similarity
    return max(1, min(10, round(raw_score, 2)))

def get_user_based_recommendations(models, user_id, k=5, min_common_books=1):
    if user_id not in models['user_history']:
        return None, 'User not found'

    similar_users, err = get_user_based_similar_users(models, user_id, k, min_common_books)
    if err:
        return None, err

    read_books = {item['isbn'] for item in models['user_history'][user_id]}
    recommendations = []

    for neighbor in similar_users:
        neighbor_id = neighbor['user_id']
        similarity = neighbor['similarity']
        for item in models['user_history'].get(neighbor_id, []):
            if item['isbn'] not in read_books:
                predicted_score = predict_user_based_score(item, similarity)
                recommendations.append({
                    **item,
                    'predicted_score': predicted_score,
                    'similarity': similarity
                })

    recommendations = sorted(recommendations, key=lambda x: -x['predicted_score'])[:k]

    return {
        'similar_users': similar_users,
        'recommendations': recommendations
    }, None

# --- ITEM-BASED (Değişiklik yok, olduğu gibi bırakıldı) ---

def get_item_based_similar_books(models, isbn, k=5):
    inner_id = to_inner_id(models['item_based'], isbn, 'item')
    if inner_id is None:
        return None, 'Item not found'

    neighbors = get_neighbors(models['item_based'], inner_id, k + 1)[1:]  # exclude itself
    similar_books = []

    for neighbor_inner_id in neighbors:
        neighbor_isbn = to_raw_id(models['item_based'], neighbor_inner_id, 'item')
        similarity = models['item_based'].sim[inner_id][neighbor_inner_id]
        book_info = models['book_info'].get(neighbor_isbn, {})
        avg_rating = models['avg_ratings'].get(neighbor_isbn, 0)

        similar_books.append({
            **book_info,
            'isbn': neighbor_isbn,
            'similarity': round(float(similarity), 3),
            'avg_rating': round(avg_rating, 2)
        })

    return similar_books, None

def get_item_based_recommendations(models, isbn, k=5):
    source_book = models['book_info'].get(isbn, {})
    similar_books, err = get_item_based_similar_books(models, isbn, k)
    if err:
        return None, err

    return {
        'source_book': source_book,
        'recommendations': similar_books
    }, None

