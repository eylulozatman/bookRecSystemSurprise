import numpy as np
from surprise import PredictionImpossible

def get_user_based_recommendations1(models, user_id, k=5):
    model = models.get('user_based')
    trainset = model.trainset

    try:
        inner_uid = trainset.to_inner_uid(str(user_id))
    except ValueError:
        return None, "User not found"

    rated_items = set(trainset.to_raw_iid(iid) for (iid, _) in trainset.ur[inner_uid])
    neighbors = model.get_neighbors(inner_uid, k * 2)

    candidates = {}
    for neighbor_inner in neighbors:
        similarity = model.sim[inner_uid, neighbor_inner]
        for iid, _ in trainset.ur[neighbor_inner]:
            raw_iid = trainset.to_raw_iid(iid)
            if raw_iid in rated_items:
                continue
            if raw_iid not in candidates:
                candidates[raw_iid] = []
            candidates[raw_iid].append(similarity)

    results = []
    for isbn, sims in candidates.items():
        try:
            pred = model.predict(str(user_id), isbn).est
        except PredictionImpossible:
            continue
        avg_sim = np.mean(sims)
        book = models['book_info'].get(isbn, {})
        results.append({
            'isbn': isbn,
            'title': book.get('title', book.get('Book-Title', 'Unknown Title')),
            'author': book.get('author', book.get('Book-Author', 'Unknown Author')),
            'image_url': book.get('image_url', book.get('Image-URL-M', '')),
            'predicted_score': round(pred, 2),
            'similarity': round(avg_sim, 3)
        })

    results.sort(key=lambda x: -x['predicted_score'])

    similar_users = [{
        'user_id': trainset.to_raw_uid(n),
        'similarity': round(model.sim[inner_uid, n], 3)
    } for n in neighbors[:k]]

    return {
        'recommendations': results[:k],
        'similar_users': similar_users
    }, None

def get_item_based_recommendations1(models, isbn, k=5):
    model = models.get('item_based')
    trainset = model.trainset

    try:
        inner_iid = trainset.to_inner_iid(str(isbn))
    except ValueError:
        return None, "Item not found"

    neighbors = model.get_neighbors(inner_iid, k + 1)[1:]  # exclude itself
    results = []

    for neighbor_inner in neighbors:
        sim = model.sim[inner_iid, neighbor_inner]
        neighbor_isbn = trainset.to_raw_iid(neighbor_inner)
        book = models['book_info'].get(neighbor_isbn, {})
        results.append({
            'isbn': neighbor_isbn,
            'title': book.get('title', book.get('Book-Title', 'Unknown Title')),
            'author': book.get('author', book.get('Book-Author', 'Unknown Author')),
            'image_url': book.get('image_url', book.get('Image-URL-M', '')),
            'similarity': round(sim, 3),
            'avg_rating': round(models['avg_ratings'].get(neighbor_isbn, 0), 2)
        })

    source_book = models['book_info'].get(isbn, {})
    return {
        'source_book': {
            'isbn': isbn,
            'title': source_book.get('title', source_book.get('Book-Title', '')),
            'author': source_book.get('author', source_book.get('Book-Author', '')),
            'image_url': source_book.get('image_url', source_book.get('Image-URL-M', ''))
        },
        'recommendations': results[:k]
    }, None

def get_hybrid_recommendations1(models, user_id, k=10):
    user_result, user_err = get_user_based_recommendations1(models, user_id, k * 2)
    if user_err:
        return None, user_err

    user_read = {item['isbn'] for item in models['user_history'].get(str(user_id), [])}
    hybrid = {}

    for rec in user_result['recommendations']:
        if rec['isbn'] in user_read:
            continue
        hybrid[rec['isbn']] = {
            **rec,
            'hybrid_score': rec['predicted_score'],
            'source': 'cf',
            'explanation': f"Recommended based on similar users. Similarity: {rec['similarity']}"
        }

    cb_result, cb_err = get_item_based_recommendations1(models, list(user_read)[0], k * 2)
    if not cb_err and cb_result:
        for rec in cb_result['recommendations']:
            if rec['isbn'] in hybrid:
                hybrid[rec['isbn']]['hybrid_score'] += rec['similarity'] * 2  # Boost hybrid score
                hybrid[rec['isbn']]['source'] = 'cf+cb'
                hybrid[rec['isbn']]['explanation'] += f" | Content-based similarity: {rec['similarity']}"
            else:
                hybrid[rec['isbn']] = {
                    'isbn': rec['isbn'],
                    'title': rec['title'],
                    'author': rec['author'],
                    'image_url': rec['image_url'],
                    'hybrid_score': rec['similarity'] * 2,
                    'source': 'cb',
                    'explanation': f"Recommended based on similar content. Similarity: {rec['similarity']}"
                }

    sorted_hybrid = sorted(hybrid.values(), key=lambda x: -x['hybrid_score'])[:k]
    return {
        'recommendations': sorted_hybrid,
        'strategy': 'simple hybrid (cf prioritized)'}, None