#model_trainer.py

import datetime
from surprise import Dataset, Reader, KNNBasic, dump
from surprise.model_selection import train_test_split
import pandas as pd
import os
from surprise import Trainset
import threading
import schedule
from models_loader import load_models_and_data

update_lock = threading.Lock()

def incremental_update(user_id, isbn, rating):
    """User-Based modeli anlık olarak günceller"""
    global models
    
    with update_lock:
        try:
            # Inner ID'leri al
            user_inner = models['user_based'].trainset.to_inner_uid(user_id)
            item_inner = models['user_based'].trainset.to_inner_iid(isbn)
            
            # Rating matrisini güncelle
            models['user_based'].trainset.update(user_inner, item_inner, rating)
            
            # Benzerlik matrisini yeniden hesapla
            models['user_based'].compute_similarities()
            print(f"Model updated for user {user_id}")
            return True
        except ValueError:  # Yeni kullanıcı/item durumu
            print(f"New user/item detected - {user_id}/{isbn}")
            return False
        except Exception as e:
            print(f"Update error: {str(e)}")
            return False

def schedule_retrain(hour=3):
    def job():
        print("\nScheduled retrain started...")
        train_and_save_models()
        # Modeli yeniden yükle
        global models
        models = load_models_and_data()
        print("Retrain completed at", datetime.now())
    
    schedule.every().day.at(f"{hour:02}:00").do(job)

def optimize_ratings(df):
    """Rating dağılımı düşükse genişletmek için normalizasyon uygular"""
    rating_stats = df['Book-Rating'].describe()
    if rating_stats['std'] < 2.0:
        print("\n⚠️ Rating normalizasyonu uygulanıyor...")
        df['Book-Rating'] = df['Book-Rating'].apply(
            lambda x: max(1, min(10, x * 2))
        )
    return df

def train_model(trainset, user_based=True):
    sim_options = {
        'name': 'pearson_baseline',  
        'user_based': user_based,
        'shrinkage': 100,           
        'min_support': 3             # En az 3 ortak oylama şartı
    }

    print(f"\n🔧 {'User' if user_based else 'Item'}-Based Model Eğitiliyor (Pearson)...")
    model = KNNBasic(
        k=30,                        # Komşu sayısı
        min_k=3,                     # Tahmin yapmak için en az 3 benzer komşu gerekir
        sim_options=sim_options,
        verbose=True
    )
    model.fit(trainset)
    return model

def save_metadata(df):
    """Kitap meta verilerini dışa aktarır"""
    meta_cols = ['ISBN', 'Book-Title', 'Book-Author', 'Image-URL-M']
    df[meta_cols].drop_duplicates().to_csv('models/book_info.csv', index=False)
    print("✅ Kitap meta verileri kaydedildi")

def train_and_save_models():
    """Tüm eğitim süreci"""
    # 1. Veri yükleme
    df = pd.read_csv("models/newbookdata.csv", dtype={'User-ID': str, 'ISBN': str})
    df = df[['User-ID', 'ISBN', 'Book-Rating', 'Book-Title', 'Book-Author', 'Image-URL-M']]
    
    # 2. Rating normalizasyonu (gerekirse)
    df = optimize_ratings(df)

    # 3. Surprise Dataset hazırlığı
    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df[['User-ID', 'ISBN', 'Book-Rating']], reader)
    trainset, _ = train_test_split(data, test_size=0.2)

    # 4. Modellerin eğitimi
    user_model = train_model(trainset, user_based=True)
    item_model = train_model(trainset, user_based=False)

    # 5. Modelleri kaydet
    os.makedirs('models', exist_ok=True)
    dump.dump('models/user_based_model', algo=user_model)
    dump.dump('models/item_based_model', algo=item_model)

    # 6. Kitap bilgilerini kaydet
    save_metadata(df)

    print("\n✅ Eğitim başarıyla tamamlandı!")


if __name__ == '__main__':
    train_and_save_models()    