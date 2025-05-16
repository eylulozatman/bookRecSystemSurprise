from surprise import Dataset, Reader, KNNBasic, dump
from surprise.model_selection import train_test_split
import pandas as pd
import os
from collections import Counter,defaultdict
import random
from tqdm import tqdm
import pandas as pd
import random
from collections import defaultdict

def analyze_data():
    
    file_path = 'models/newbookdata.csv'
    df = pd.read_csv(file_path)

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



def analyze_user_similarity():
    df = pd.read_csv("newbookdata.csv", dtype={'User-ID': str, 'ISBN': str})
    
    print("\n🔍 Kullanıcı bazlı ortak kitap okuma analizi başlatılıyor...\n")

    user_books = df.groupby("User-ID")["ISBN"].apply(set).to_dict()
    target_users = random.sample(list(user_books.keys()), 500)

    for target_user in tqdm(target_users, desc="🔄 Kullanıcılar analiz ediliyor"):
        target_set = user_books[target_user]
        result = []
        for other_user, other_set in user_books.items():
            if other_user == target_user:
                continue
            common_books = target_set & other_set
            if len(common_books) >= 2:
                result.append((other_user, len(common_books)))
        result.sort(key=lambda x: x[1], reverse=True)
        print(f"\n👤 Kullanıcı {target_user}, aşağıdaki kullanıcılarla ortak kitaplar okumuş:")
        for uid, count in result[:5]:
            print(f"   - {uid} ile {count} ortak kitap")

def analyze_item_similarity():
    df = pd.read_csv("newbookdata.csv", dtype={'User-ID': str, 'ISBN': str})
    
    print("\n📚 Kitap bazlı ortak kullanıcı okuma analizi başlatılıyor...\n")

    isbn_users = df.groupby("ISBN")["User-ID"].apply(set).to_dict()
    user_books = df.groupby("User-ID")["ISBN"].apply(set).to_dict()

    target_isbns = random.sample(list(isbn_users.keys()), 500)

    for target_isbn in tqdm(target_isbns, desc="🔄 Kitaplar analiz ediliyor"):
        users = isbn_users[target_isbn]
        book_counter = defaultdict(int)
        
        for user in users:
            books = user_books.get(user, set())
            for book in books:
                if book != target_isbn:
                    book_counter[book] += 1
        
        similar_books = sorted(book_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n📖 Kitap {target_isbn} (okuyan sayısı: {len(users)}), şu kitaplarla birlikte sıkça okunmuş:")
        for isbn, count in similar_books:
            print(f"   - {isbn}: {count} kez birlikte okunmuş")



def reduce_users_in_cleaned_data(target_user_count=5000):

    """    - Benzersiz kullanıcı sayısını azaltır (target_user_count'a kadar)
    - Veri sayısını korur
    - Çakışan ratinglerde rastgele birini seçer
    - Sonucu yeni bir CSV'ye kaydeder
    """
    # Veriyi yükle
    df = pd.read_csv("models/cleaned_bookdata.csv", dtype={'User-ID': str, 'ISBN': str})
    
    print(f"\n🔧 İşlem başlıyor...")
    print(f"Orijinal veri sayısı: {len(df):,}")
    print(f"Orijinal benzersiz kullanıcı: {df['User-ID'].nunique():,}")
    print(f"Hedef benzersiz kullanıcı: {target_user_count:,}")

    # 1. Kullanıcıları okuma sayılarına göre grupla
    user_book_counts = df['User-ID'].value_counts()
    all_users = user_book_counts.index.tolist()
    
    # 2. En aktif kullanıcıları seç (hedef sayı kadar)
    selected_users = all_users[:target_user_count]
    
    # 3. Kalan kullanıcıları rastgele seçilmiş kullanıcılara ata
    user_mapping = {user: user for user in selected_users}
    for user in all_users[target_user_count:]:
        user_mapping[user] = random.choice(selected_users)
    
    # 4. Kullanıcı ID'lerini güncelle
    df['User-ID'] = df['User-ID'].map(user_mapping)
    
    # 5. Aynı kullanıcı-kitap çiftleri için rastgele bir rating seç
    df = df.sample(frac=1).drop_duplicates(['User-ID', 'ISBN'], keep='first')
    
    # 6. Sonuçları kaydet
    output_path = "newbookdata.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\n✅ İşlem tamamlandı!")
    print(f"Yeni veri sayısı: {len(df):,}")
    print(f"Yeni benzersiz kullanıcı: {df['User-ID'].nunique():,}")
    print(f"Yeni benzersiz kitap: {df['ISBN'].nunique():,}")
    print(f"Sonuçlar '{output_path}' dosyasına kaydedildi.")

def create_users_csv(input_csv="newbookdata.csv", output_csv="users.csv"):
    """
    Kullanıcı ID'lerini alır ve users.csv dosyasına kaydeder.
    """
    # Veriyi oku
    df = pd.read_csv(input_csv, dtype={'User-ID': str})
    
    # Benzersiz kullanıcıları al
    unique_users = df['User-ID'].dropna().unique()
    
    # DataFrame oluştur
    users_df = pd.DataFrame({'User-ID': unique_users})
    
    # CSV dosyasına yaz
    users_df.to_csv(output_csv, index=False)
    
    # Bilgi ver
    print(f"\n✅ {len(unique_users):,} benzersiz kullanıcı bulundu ve '{output_csv}' dosyasına yazıldı.")


def common_books(user1_id, user2_id):
    file_path = 'models/newbookdata.csv'
    user_col = 'User-ID'
    book_col = 'ISBN'

    df = pd.read_csv(file_path)
    user1_books = set(df[df[user_col] == user1_id][book_col])
    user2_books = set(df[df[user_col] == user2_id][book_col])
    
    common = user1_books & user2_books
    
    return {
        'common_count': len(common),
        'common_books': list(common)
    }

if __name__ == '__main__':
  
    # analyze_user_similarity()
    # analyze_item_similarity()
    # create_users_csv()  
    # analyze_data()
    result = common_books(97324, 23902)
    print(result)

