from surprise import Dataset, Reader, KNNBasic, dump
from surprise.model_selection import train_test_split
import pandas as pd
import os
from collections import Counter,defaultdict
import random
from tqdm import tqdm

def analyze_data(df):
    """Veri setini detaylı analiz eder"""
    print("\n📊 Veri Seti İstatistikleri:")
    print(f"✅ Toplam satır sayısı: {len(df):,}")
    print(f"✅ Benzersiz kullanıcı sayısı: {df['User-ID'].nunique():,}")
    print(f"✅ Benzersiz kitap sayısı: {df['ISBN'].nunique():,}")
    
    print("\n⭐ Rating Dağılımı:")
    print(df['Book-Rating'].value_counts().sort_index())
    
    print("\n👥 Kullanıcı Başına Rating Sayısı:")
    print(df['User-ID'].value_counts().describe())
    
    print("\n📚 Kitap Başına Rating Sayısı:")
    print(df['ISBN'].value_counts().describe())

def optimize_ratings(df):
    """Rating dağılımını optimize eder"""
    rating_stats = df['Book-Rating'].describe()
    if rating_stats['std'] < 2.0:
        print("\n⚠️ Rating normalizasyonu uygulanıyor...")
        df['Book-Rating'] = df['Book-Rating'].apply(
            lambda x: max(1, min(10, x * 2))
        )
    return df

def train_model(trainset, user_based=True):
    """Optimize edilmiş model eğitimi"""
    sim_options = {
        'name': 'pearson_baseline',
        'user_based': user_based,
        'shrinkage': 100,
        'min_support': 5
    }
    
    print(f"\n{'User' if user_based else 'Item'}-Based Model Eğitiliyor...")
    model = KNNBasic(
        k=30,
        min_k=3,
        sim_options=sim_options,
        verbose=True
    )
    model.fit(trainset)
    return model

def save_metadata(df):
    """Kitap meta verilerini kaydeder"""
    meta_cols = ['ISBN', 'Book-Title', 'Book-Author', 'Image-URL-M']
    df[meta_cols].drop_duplicates().to_csv('book_info.csv', index=False)
    print("✅ Kitap meta verileri kaydedildi")

def train_and_save_models():
    """Ana eğitim fonksiyonu"""
    # Veri yükleme
    df = pd.read_csv("newbookdata.csv", dtype={'User-ID': str, 'ISBN': str})
    df = df[['User-ID', 'ISBN', 'Book-Rating', 'Book-Title', 'Book-Author', 'Image-URL-M']]
    
    # Veri analizi ve optimizasyon
    analyze_data(df)
    df = optimize_ratings(df)
    
    # Model eğitimi
    reader = Reader(rating_scale=(1, 10))
    data = Dataset.load_from_df(df[['User-ID', 'ISBN', 'Book-Rating']], reader)
    trainset, _ = train_test_split(data, test_size=0.2)
    
    user_model = train_model(trainset, user_based=True)
    item_model = train_model(trainset, user_based=False)
    
    # Kayıt işlemleri
    os.makedirs('models', exist_ok=True)
    dump.dump('models/user_based_model', algo=user_model)
    dump.dump('models/item_based_model', algo=item_model)
    save_metadata(df)
    
    print("\n✅ Eğitim başarıyla tamamlandı!")


if __name__ == '__main__':
  
     train_and_save_models()
