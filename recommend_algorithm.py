from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict
from surprise import KNNBasic
import math

# ORTAK YARDIMCI FONKSİYONLAR
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
                
                # Öneri kalite skoru (benzerlik + kitap popülaritesi)
                book_popularity = min(1.0, models['avg_ratings'].get(item['isbn'], 5.0) / 10.0)
                quality_score = 0.6 * similarity + 0.4 * book_popularity
                
                recommendations.append({
                    **item,
                    'predicted_score': predicted_score,
                    'similarity': similarity,
                    'quality_score': round(quality_score, 3),
                    'recommendation_type': 'user_based'
                })
    
    # Kalite skoruna göre sırala
    recommendations.sort(key=lambda x: -x['quality_score'])
    return {'recommendations': recommendations[:k]}, None


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

# 4. GELİŞMİŞ HYBRID FONKSİYON
def get_hybrid_recommendations(models, user_id, k=5):
    """Gelişmiş hibrit öneri sistemi"""
    try:
        user_history = models['user_history'].get(str(user_id), [])
        if len(user_history) < 3:
            return None, "User needs at least 3 rated books"
        
        # Tüm öneri türlerini al
        user_recs, _ = get_user_based_recommendations(models, user_id, k*3)
        user_recs = user_recs['recommendations'] if user_recs else []
        
        content_recs, _ = get_content_based_recommendations(models, user_history, k*3)
        content_recs = content_recs['recommendations'] if content_recs else []
        
        # Okunmuş kitapları filtrele
        read_books = {book['isbn'] for book in user_history}
        user_recs = [r for r in user_recs if r['isbn'] not in read_books]
        content_recs = [r for r in content_recs if r['isbn'] not in read_books]
        
        # Hibrit skorlama
        hybrid_recs = defaultdict(dict)
        global_avg = np.mean(list(models['avg_ratings'].values())) if models['avg_ratings'] else 5.0
        
        # User-based önerilerini ekle
        for rec in user_recs:
            hybrid_recs[rec['isbn']].update({
                **rec,
                'user_based_score': rec['predicted_score'],
                'hybrid_components': {'user_based': rec['predicted_score']}
            })
        
        # Content-based önerilerini ekle
        for rec in content_recs:
            if rec['isbn'] in hybrid_recs:
                hybrid_recs[rec['isbn']]['hybrid_components']['content_based'] = rec['content_score']
            else:
                hybrid_recs[rec['isbn']].update({
                    **rec,
                    'hybrid_components': {'content_based': rec['content_score']}
                })
        
        # Hibrit skor hesapla
        final_recs = []
        for isbn, rec in hybrid_recs.items():
            components = rec['hybrid_components']
            
            # Normalizasyon yap
            user_score = components.get('user_based', global_avg)
            norm_user = (user_score - 1) / 9.0  # 1-10 => 0-1
            
            content_score = components.get('content_based', 0.5)
            norm_content = max(0.0, min(1.0, content_score))
            
            # Hibrit skor (dinamik ağırlık)
            if 'user_based' in components and 'content_based' in components:
                hybrid_score = 0.7 * norm_user + 0.3 * norm_content
            elif 'user_based' in components:
                hybrid_score = norm_user
            else:
                hybrid_score = norm_content
            
            final_recs.append({
                **rec,
                'hybrid_score': hybrid_score,
                'final_score': 1 + hybrid_score * 9.0  # 0-1 => 1-10
            })
        
        # Sıralama ve sonuç
        final_recs.sort(key=lambda x: -x['hybrid_score'])
        return {'recommendations': final_recs[:k]}, None
    
    except Exception as e:
        return None, f"Hybrid recommendation error: {str(e)}"