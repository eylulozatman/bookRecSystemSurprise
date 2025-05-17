from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict
from surprise import KNNBasic
import math

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

def enhanced_pearson_sim(user1_ratings, user2_ratings):
    """Gelişmiş Pearson benzerlik fonksiyonu"""
    common_books = set(user1_ratings.keys()) & set(user2_ratings.keys())
    n = len(common_books)
    
    if n < 2:
        return 0.0
    
    # Ortak kitaplar için ratingleri al
    ratings1 = [user1_ratings[book] for book in common_books]
    ratings2 = [user2_ratings[book] for book in common_books]
    
    # Pearson korelasyonu
    mean1, mean2 = np.mean(ratings1), np.mean(ratings2)
    numerator = np.sum((ratings1 - mean1) * (ratings2 - mean2))
    denominator = np.sqrt(np.sum((ratings1 - mean1)**2)) * np.sqrt(np.sum((ratings2 - mean2)**2))
    
    if denominator == 0:
        return 0.0
    
    pearson = numerator / denominator
    
    # Ortak kitap sayısına göre ağırlıklandırma (logaritmik scaling)
    common_weight = min(1.0, math.log(n + 1) / math.log(50))
    
    # Rating tutarlılık faktörü
    rating_diff = np.mean(np.abs(np.array(ratings1) - np.array(ratings2)))
    consistency = 1.0 - (rating_diff / 9.0)
    
    # Nihai benzerlik skoru
    final_sim = pearson * common_weight * consistency
    
    return max(-1.0, min(1.0, final_sim))

# 1. GELİŞMİŞ USER-BASED FONKSİYONLAR
def get_user_based_similar_users(models, user_id, k=5, min_common_books=3):
    """Gelişmiş benzer kullanıcı bulma"""
    if user_id not in models['user_history']:
        return None, 'User not found'
    
    # Mevcut kullanıcının verileri
    user_books = {item['isbn']: item['rating'] for item in models['user_history'][user_id]}
    
    # Tüm kullanıcılar arasında benzerlik hesapla
    similar_users = []
    for other_user, other_history in models['user_history'].items():
        if other_user == user_id:
            continue
            
        other_books = {item['isbn']: item['rating'] for item in other_history}
        common_books = set(user_books.keys()) & set(other_books.keys())
        
        if len(common_books) >= min_common_books:
            similarity = enhanced_pearson_sim(user_books, other_books)
            
            # Benzerlik ağırlığı (ortak kitaplara göre)
            weight = min(1.0, len(common_books) / 20.0)  # Max 20 kitap üzerinden
            weighted_sim = round(similarity * (0.7 + 0.3 * weight), 3)            
            similar_users.append({
                'user_id': other_user,
                'similarity': weighted_sim,
                'common_books': len(common_books)
            })
    
    # En benzer k kullanıcıyı seç
    similar_users.sort(key=lambda x: -x['similarity'])
    return similar_users[:k], None

def predict_user_based_score(item, similarity, global_avg=5.0):
    """Gelişmiş rating tahmini"""
    # Similarity 0-1 aralığına normalize et
    norm_sim = (similarity + 1) / 2.0
    
    # Temel skor + benzerlik etkisi
    predicted = global_avg + (item['rating'] - global_avg) * norm_sim
    return max(1.0, min(10.0, round(predicted, 2)))

def get_user_based_recommendations(models, user_id, k=5):
    """Gelişmiş user-based öneriler"""
    similar_users, err = get_user_based_similar_users(models, user_id, k*2)
    if err or not similar_users:
        return None, err or 'No similar users found'
    
    read_books = {item['isbn'] for item in models['user_history'][user_id]}
    global_avg = np.mean(list(models['avg_ratings'].values())) if models['avg_ratings'] else 5.0
    
    recommendations = []
    for neighbor in similar_users:
        neighbor_id = neighbor['user_id']
        similarity = neighbor['similarity']
        
        for item in models['user_history'].get(neighbor_id, []):
            if item['isbn'] not in read_books:
                predicted_score = predict_user_based_score(item, similarity, global_avg)
                
                book_popularity = min(1.0, models['avg_ratings'].get(item['isbn'], 5.0) / 10.0)
                quality_score = 0.8 * similarity + 0.2 * book_popularity
                
                recommendations.append({
                    **item,
                    'predicted_score': predicted_score,
                    'similarity': similarity,
                    'quality_score': round(quality_score, 3),
                    'recommendation_type': 'user_based'
                })
    
    # Return both recommendations and similar users
    return {
        'recommendations': recommendations[:k],
        'similar_users': similar_users[:k]
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



# 3. GELİŞMİŞ CONTENT-BASED FONKSİYONLAR
def get_content_based_recommendations(models, user_history, k=5):
    """Gelişmiş içerik tabanlı öneriler"""
    try:
        if not user_history:
            return None, "No user history"
        
        # Kullanıcının okuma profilini oluştur
        user_authors = " ".join([book['author'] for book in user_history])
        user_titles = " ".join([book['title'] for book in user_history])
        
        # Tüm kitapları hazırla
        book_data = []
        for isbn, book in models['book_info'].items():
            book_data.append({
                'isbn': isbn,
                'author': book['author'],
                'title': book['title'],
                'book_info': book
            })
        
        # Yazar benzerliği (daha yüksek ağırlık)
        author_vectorizer = TfidfVectorizer(stop_words='english')
        author_vectors = author_vectorizer.fit_transform([user_authors] + [b['author'] for b in book_data])
        author_sim = cosine_similarity(author_vectors[0:1], author_vectors[1:])[0]
        
        # Başlık benzerliği
        title_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        title_vectors = title_vectorizer.fit_transform([user_titles] + [b['title'] for b in book_data])
        title_sim = cosine_similarity(title_vectors[0:1], title_vectors[1:])[0]
        
        # Önerileri oluştur (yazar daha önemli)
        recommendations = []
        for i, book in enumerate(book_data):
            content_score = 0.8 * author_sim[i] + 0.2 * title_sim[i]
            recommendations.append({
                **book['book_info'],
                'isbn': book['isbn'],
                'content_score': content_score,
                'author_similarity': author_sim[i],
                'title_similarity': title_sim[i],
                'recommendation_type': 'content_based'
            })
        
        recommendations.sort(key=lambda x: -x['content_score'])
        return {'recommendations': recommendations[:k]}, None
    
    except Exception as e:
        return None, f"Content-based error: {str(e)}"


from collections import defaultdict

def get_hybrid_recommendations(models, user_id, k=10, similarity_threshold=0.3, min_content_based=2):
    """Hybrid recommendation system with guaranteed content-based diversity."""
    try:
        user_history = models['user_history'].get(str(user_id), [])
        if len(user_history) < 3:
            return None, "User needs at least 3 rated books"

        # 1. Get CF recommendations
        user_recs_data, _ = get_user_based_recommendations(models, user_id, k * 3)
        cf_recommendations = user_recs_data.get('recommendations', []) if user_recs_data else []
        similar_users = user_recs_data.get('similar_users', [])

        # 2. Analyze user's top authors
        author_counts = defaultdict(int)
        for book in user_history:
            author_counts[book['author']] += 1
        top_authors = [a for a, _ in sorted(author_counts.items(), key=lambda x: -x[1])[:3]]

        # 3. Format CF recommendations
        user_read_isbns = {b['isbn'] for b in user_history}
        cf_recs = []
        for rec in cf_recommendations:
            if rec['isbn'] in user_read_isbns:
                continue
            explanation_parts = []
            if rec['author'] in top_authors:
                explanation_parts.append(f"Author match ({rec['author']})")
            if similar_users:
                similar_users_str = ", ".join([u['user_id'] for u in similar_users[:2]])
                explanation_parts.append(f"Similar to users: {similar_users_str}")
            cf_recs.append({
                **rec,
                'source': 'cf',
                'explanation': " | ".join(explanation_parts),
                'main_score': rec['similarity']
            })

        # 4. Format content-based recommendations
        content_recs_data, _ = get_content_based_recommendations(models, user_history, k * 3)
        content_recs = content_recs_data.get('recommendations', []) if content_recs_data else []

        cb_recs = []
        for rec in content_recs:
            if rec['isbn'] in user_read_isbns:
                continue
            explanation = f"Similar to your interest in {rec['author']}'s style"
            if rec['author'] in top_authors:
                explanation += f" (your #{top_authors.index(rec['author']) + 1} most-read author)"
            cb_recs.append({
                **rec,
                'source': 'content',
                'explanation': explanation,
                'main_score': rec['author_similarity']
            })

        # 5. Select top CF and content-based
        strong_cf = sorted(
            [r for r in cf_recs if r['main_score'] >= similarity_threshold],
            key=lambda x: (-x['main_score'], -x.get('quality_score', 0))
        )[:k - min_content_based]

        strong_cb = sorted(
            cb_recs,
            key=lambda x: (-x['main_score'], -x.get('content_score', 0))
        )[:min_content_based]

        combined = strong_cf + strong_cb

        # 6. Fill remaining slots if needed
        remaining = k - len(combined)
        if remaining > 0:
            remaining_cf = [r for r in cf_recs if r['main_score'] < similarity_threshold and r['isbn'] not in {x['isbn'] for x in combined}]
            remaining_cb = [r for r in cb_recs if r['isbn'] not in {x['isbn'] for x in combined}]
            remaining_recs = sorted(
                remaining_cf + remaining_cb,
                key=lambda x: (-x['main_score'], -x.get('quality_score', x.get('content_score', 0)))
            )[:remaining]
            combined.extend(remaining_recs)

        # 7. Final formatting
        final_recommendations = []
        for rec in combined:
            score_type = 'user_similarity' if rec['source'] == 'cf' else 'author_similarity'
            hybrid_score = rec.get('quality_score') if score_type == 'user_similarity' else rec.get('content_score')
            final_recommendations.append({
                'title': rec['title'],
                'author': rec['author'],
                'image_url': rec.get('image_url') or rec.get('image'),
                'hybrid_score': hybrid_score,
                'score_value': rec['main_score'],
                'score_type': score_type,
                'explanation': rec['explanation'],
                'isbn': rec['isbn']  # Opsiyonel: Kullanıcıya detay göstermek istersen
            })

        final_recommendations = sorted(final_recommendations, key=lambda x: -x['hybrid_score'])[:k]

        # Strategy label (opsiyonel)
        cf_count = sum(1 for r in final_recommendations if r['score_type'] == 'user_similarity')
        strategy = (
            "CF-dominant" if cf_count >= k - min_content_based
            else "Content-balanced" if cf_count >= min_content_based
            else "Content-supplemented"
        )

        return {
            'recommendations': final_recommendations,
            'strategy': strategy,
            'cf_ratio': f"{cf_count}/{k}",
            'content_ratio': f"{k - cf_count}/{k}"
        }, None

    except Exception as e:
        return None, f"Hibrit öneri hatası: {str(e)}"
