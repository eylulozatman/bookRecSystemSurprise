from surprise import Dataset, Reader, KNNBasic, dump
from surprise.model_selection import train_test_split
import pandas as pd
import os

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
    """Pearson Baseline ile User veya Item tabanlı model eğitimi"""
    sim_options = {
        'name': 'pearson_baseline',  
        'user_based': user_based,
        'shrinkage': 100,            # Gürültüyü bastırır
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
