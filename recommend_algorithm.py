#recommend_algorithm.py
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
    common_books = set(user1_ratings.keys()) & set(user2_ratings.keys())
    n = len(common_books)
    if n < 2:
        return 0.0

    ratings1 = [user1_ratings[book] for book in common_books]
    ratings2 = [user2_ratings[book] for book in common_books]

    mean1, mean2 = np.mean(ratings1), np.mean(ratings2)
    numerator = np.sum((np.array(ratings1) - mean1) * (np.array(ratings2) - mean2))
    denominator = np.sqrt(np.sum((np.array(ratings1) - mean1) ** 2)) * np.sqrt(np.sum((np.array(ratings2) - mean2) ** 2))
    if denominator == 0:
        return 0.0

    pearson = numerator / denominator
    common_weight = min(1.0, math.log(n + 1) / math.log(50))
    rating_diff = np.mean(np.abs(np.array(ratings1) - np.array(ratings2)))
    consistency = 1.0 - (rating_diff / 9.0)

    final_sim = pearson * common_weight * consistency
    return max(-1.0, min(1.0, final_sim))


def get_user_based_similar_users(models, user_id, k=5, min_common_books=3):
    if user_id not in models['user_history']:
        return None, 'User not found'

    user_books = {item['isbn']: item['rating'] for item in models['user_history'][user_id]}
    similar_users = []

    for other_user, other_history in models['user_history'].items():
        if other_user == user_id:
            continue

        other_books = {item['isbn']: item['rating'] for item in other_history}
        common_books = set(user_books.keys()) & set(other_books.keys())

        if len(common_books) >= min_common_books:
            similarity = enhanced_pearson_sim(user_books, other_books)
            weight = min(1.0, len(common_books) / 20.0)
            weighted_sim = round(similarity * (0.7 + 0.3 * weight), 3)

            similar_users.append({
                'user_id': other_user,
                'similarity': weighted_sim,
                'common_books': len(common_books)
            })

    similar_users.sort(key=lambda x: -x['similarity'])
    return similar_users[:k], None


def predict_user_based_score(item, similarity, global_avg=5.0):
    norm_sim = (similarity + 1) / 2.0
    predicted = global_avg + (item['rating'] - global_avg) * norm_sim
    return max(1.0, min(10.0, round(predicted, 2)))


def get_user_based_recommendations(models, user_id, k=5):
    similar_users, err = get_user_based_similar_users(models, user_id, k * 2)
    if err or not similar_users:
        return None, err or 'No similar users found'

    read_books = {item['isbn'] for item in models['user_history'][user_id]}
    global_avg = np.mean(list(models['avg_ratings'].values())) if models['avg_ratings'] else 5.0

    recommendations = []
    for neighbor in similar_users:
        neighbor_id = neighbor['user_id']
        similarity = neighbor['similarity']
        boosted_similarity = similarity ** 0.5  # Küçük benzerlikleri yükselt

        for item in models['user_history'].get(neighbor_id, []):
            if item['isbn'] not in read_books:
                predicted_score = predict_user_based_score(item, similarity, global_avg)
                avg_rating = models['avg_ratings'].get(item['isbn'], 5.0)
                book_popularity = min(1.0, avg_rating / 8.0)  # Daha yüksek popülerlik etkisi

                # Final quality score: 0-1 arasında ama daha yüksek
                quality_score = round(min(1.0, 0.6 * boosted_similarity + 0.4 * book_popularity), 3)

                recommendations.append({
                    **item,
                    'predicted_score': predicted_score,
                    'similarity': similarity,
                    'quality_score': quality_score,
                    'recommendation_type': 'user_based'
                })

    recommendations.sort(key=lambda x: -x['quality_score'])
    return {
        'recommendations': recommendations[:k],
        'similar_users': similar_users[:k]
    }, None


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

def get_hybrid_recommendations(models, user_id, k=10, similarity_threshold=0.4, cb_boost_weight=0.3, cf_priority_boost=1.2):
  
    try:
        user_id = str(user_id)
        user_history = models['user_history'].get(user_id, [])
        if len(user_history) < 3:
            return None, "User needs at least 3 rated books"

        # Get base recommendations
        cf_result, cf_err = get_user_based_recommendations(models, user_id, k * 5)
        cb_result, cb_err = get_content_based_recommendations(models, user_history, k * 5)

        user_read_isbns = {b["isbn"] for b in user_history}
        combined = {}

        # Process CF recommendations with priority boost
        if cf_result and cf_result.get("recommendations"):
            for rec in cf_result["recommendations"]:
                if rec["isbn"] in user_read_isbns:
                    continue
                raw_cf_score = rec.get("similarity", 0)
                boosted_cf = raw_cf_score * cf_priority_boost  
                combined[rec["isbn"]] = {
                    "isbn": rec["isbn"],
                    "title": rec["title"],
                    "author": rec["author"],
                    "image_url": rec.get("image_url", rec.get("image")),
                    "cf_raw": raw_cf_score,
                    "cf_boosted": boosted_cf,
                    "cb_raw": 0,
                    "source_flags": ["cf"],
                    "explanations": {
                        "cf": [
                            "Recommended by similar users",
                            f"User similarity: {raw_cf_score*100:.1f}%",
                        ]
                    }
                }

        # Process CB recommendations
        if cb_result and cb_result.get("recommendations"):
            for rec in cb_result["recommendations"]:
                if rec["isbn"] in user_read_isbns:
                    continue
                raw_cb_score = rec.get("author_similarity", rec.get("content_score", 0))
                entry = combined.get(rec["isbn"], {
                    "isbn": rec["isbn"],
                    "title": rec["title"],
                    "author": rec["author"],
                    "image_url": rec.get("image_url", rec.get("image")),
                    "cf_raw": 0,
                    "cf_boosted": 0,
                    "cb_raw": raw_cb_score,
                    "source_flags": [],
                    "explanations": {}
                })
                entry.update({
                    "cb_raw": raw_cb_score,
                    "source_flags": list(set(entry["source_flags"] + ["cb"])),
                    "explanations": {
                        **entry.get("explanations", {}),
                        "cb": [
                            "Matches your reading preferences",
                            f"Content similarity: {raw_cb_score*100:.1f}%"
                        ]
                    }
                })
                combined[rec["isbn"]] = entry

        # Check if we have meaningful CF recommendations
        has_meaningful_cf = any(rec["cf_boosted"] >= similarity_threshold for rec in combined.values())
        
        # Fallback to CB-only if no meaningful CF
        if not has_meaningful_cf:
            cb_results = [
                {
                    "isbn": rec["isbn"],
                    "title": rec["title"],
                    "author": rec["author"],
                    "image_url": rec["image_url"],
                    "hybrid_score": round(rec["cb_raw"], 4),
                    "cf_score": 0,
                    "cb_score": round(rec["cb_raw"], 4),
                    "source": "cb",
                    "explanation": " | ".join(rec["explanations"].get("cb", [])) + 
                                 f" (CB-only, score: {rec['cb_raw']*100:.1f}%)"
                }
                for rec in combined.values() 
                if rec["cb_raw"] > 0
            ]
            cb_results = sorted(cb_results, key=lambda x: -x["cb_score"])[:k]
            
            return {
                "recommendations": cb_results,
                "strategy_details": {
                    "strategy": "CB-only (insufficient CF data)",
                    "recommendation_count": len(cb_results)
                }
            }, None

        # Generate hybrid recommendations
        results = []
        for rec in combined.values():
            cf_boosted = rec["cf_boosted"]
            cb_raw = rec["cb_raw"]
            
            # Determine recommendation source and score
            if cf_boosted >= similarity_threshold:
                if cb_raw > 0:
                    # CF with CB boost
                    hybrid_score = cf_boosted + (cb_raw * cb_boost_weight)
                    source = "cf+cb"
                else:
                    # Pure CF
                    hybrid_score = cf_boosted
                    source = "cf"
            elif cb_raw > 0:
                # Pure CB (CF below threshold)
                hybrid_score = cb_raw
                source = "cb"
            else:
                continue

            # Build explanation
            explanation_parts = []
            if "cf" in rec["source_flags"]:
                explanation_parts.extend(rec["explanations"].get("cf", []))
            if "cb" in rec["source_flags"] and source != "cf":
                explanation_parts.extend(rec["explanations"].get("cb", []))
                if source == "cf+cb":
                    explanation_parts.append(f"Content boost applied (+{cb_raw*cb_boost_weight*100:.1f}%)")

            results.append({
                "isbn": rec["isbn"],
                "title": rec["title"],
                "author": rec["author"],
                "image_url": rec["image_url"],
                "hybrid_score": round(hybrid_score, 4),
                "cf_score": round(rec["cf_raw"], 4),  # Store original CF score
                "cb_score": round(cb_raw, 4),
                "source": source,
                "explanation": " | ".join(explanation_parts) + 
                               f" (Final score: {hybrid_score*100:.1f}%)"
            })

        # Prioritization with controlled CF bias
        def compute_priority(rec):
            """Priority with slight CF preference"""
            cf = rec["cf_score"]  # Use original CF score for display
            boosted_cf = rec.get("cf_boosted", cf)
            cb = rec["cb_score"]
            
            # Strong boosted CF gets top priority
            if boosted_cf >= similarity_threshold:
                return 3 + boosted_cf  # CF gets priority boost
            # Strong CB comes next
            elif cb >= similarity_threshold:
                return 2 + cb
            # Everything else
            else:
                return 1 + max(cf, cb)

        # Sort by priority then by hybrid score
        sorted_results = sorted(
            results,
            key=lambda x: (-compute_priority(x), -x["hybrid_score"])
        )[:k]

        strategy_details = {
            "strategy": "CF-prioritized hybrid (balanced)",
            "parameters": {
                "similarity_threshold": similarity_threshold,
                "cb_boost_weight": cb_boost_weight,
                "cf_priority_boost": cf_priority_boost
            },
            "composition": {
                "total": len(sorted_results),
                "cf_strong": sum(1 for r in sorted_results if r["source"] == "cf"),
                "cf_cb_hybrid": sum(1 for r in sorted_results if r["source"] == "cf+cb"),
                "cb_only": sum(1 for r in sorted_results if r["source"] == "cb")
            }
        }

        return {
            "recommendations": sorted_results,
            "strategy_details": strategy_details
        }, None

    except Exception as e:
        return None, f"Hybrid recommendation error: {str(e)}"
    

  