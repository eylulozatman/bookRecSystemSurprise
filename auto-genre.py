import pandas as pd
from transformers import pipeline

import math

# 1. Genre listesi
candidate_labels = [
    "Science Fiction", "Fantasy", "Romance", "Mystery", 
    "Thriller", "Non-fiction", "Historical", "Biography",
    "Horror", "Young Adult", "Self-help", "Poetry", 
    "Children", "Adventure", "Politics", "Philosophy"
]

# 2. Tür tahmin fonksiyonu
def classify_genre(title, classifier, labels):
    try:
        result = classifier(title, labels)
        return result["labels"][0]
    except Exception as e:
        print(f"Hata: {e}")
        return "Unknown"

# 3. Ana fonksiyon
def main():
    # Kitapları oku
    df = pd.read_csv("book_info.csv")

    # Modeli yükle (küçük ve hızlı model)
    classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")

    # Chunk sonuçlarını birleştirmek için liste
    chunks_with_genre = []

    # 1000'lik parçalara böl ve işle
    for i in range(0, math.floor(len(df)/100)):
        print(f"⏳ {i}. satırdan itibaren işleniyor...")
        df_chunk = df.iloc[i:i+1000].copy()
        df_chunk["Genre"] = df_chunk["Book-Title"].apply(
            lambda x: classify_genre(x, classifier, candidate_labels)
        )
        chunks_with_genre.append(df_chunk)

    # Parçaları birleştir
    final_df = pd.concat(chunks_with_genre)

    # Yeni CSV dosyasını kaydet
    final_df.to_csv("bookWgenres.csv", index=False)
    print("✔️ Kitaplar tahmin edildi ve bookWgenres.csv dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
