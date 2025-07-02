import numpy as np
import pandas as pd
from surprise import Dataset, Reader
from surprise.model_selection import cross_validate
from datetime import datetime
from models_loader import load_models_and_data


class QuickEvaluator:
    def __init__(self, data_path='models/newbookdata.csv'):
        """
        Hızlı model değerlendirme sınıfı
        
        Args:
            data_path (str): Derecelendirme verilerinin yolu
        """
        self.data_path = data_path

    def _load_data(self):
        """Verileri yükler ve Surprise formatına çevirir"""
        df = pd.read_csv(self.data_path, dtype={'User-ID': str, 'ISBN': str})
        return Dataset.load_from_df(
            df[['User-ID', 'ISBN', 'Book-Rating']], 
            Reader(rating_scale=(1, 10)))
    
    def evaluate(self, models, cv=3):
        """
        Modelleri hızlıca değerlendirir ve konsola yazar
        
        Args:
            models: {'user_based': model1, 'item_based': model2} formatında sözlük
            cv (int): Cross-validation kat sayısı
        """
        data = self._load_data()
        print(f"\n🔍 Model Değerlendirme Başladı ({datetime.now().strftime('%H:%M:%S')})")
        print(f"📊 Cross-Validation Katları: {cv}")
        print("="*50)
        
        results = {}
        
        for model_name, model in models.items():
            print(f"\n🧮 {model_name.replace('_', ' ').title()} Modeli Değerlendiriliyor...")
            
            cv_results = cross_validate(
                model, data,
                measures=['RMSE', 'MAE'],
                cv=cv,
                verbose=False
            )
            
            # Sonuçları hesapla
            rmse_mean = np.mean(cv_results['test_rmse'])
            rmse_std = np.std(cv_results['test_rmse'])
            mae_mean = np.mean(cv_results['test_mae'])
            mae_std = np.std(cv_results['test_mae'])
            
            # Konsola yazdır
            print("\n📈 Performans Metrikleri:")
            print(f"• RMSE: {rmse_mean:.4f} ± {rmse_std:.4f}")
            print(f"• MAE:  {mae_mean:.4f} ± {mae_std:.4f}")
            
            print("\n⏱️ Zamanlama:")
            print(f"• Ortalama Eğitim Süresi: {np.mean(cv_results['fit_time']):.2f}s")
            print(f"• Ortalama Test Süresi:  {np.mean(cv_results['test_time']):.2f}s")
            
            results[model_name] = {
                'RMSE': rmse_mean,
                'MAE': mae_mean,
                'fit_time': np.mean(cv_results['fit_time']),
                'test_time': np.mean(cv_results['test_time'])
            }
        
        # Model karşılaştırması
        if len(results) > 1:
            print("\n" + "="*50)
            print("\n🔎 Model Karşılaştırması:")
            
            names = list(results.keys())
            rmse_diff = results[names[0]]['RMSE'] - results[names[1]]['RMSE']
            time_ratio = results[names[1]]['fit_time'] / results[names[0]]['fit_time']
            
            better_model = names[1] if rmse_diff > 0 else names[0]
            print(f"• Daha iyi model: {better_model.replace('_', ' ')} "
                  f"(%{abs(rmse_diff)/results[names[0]]['RMSE']*100:.1f} daha iyi RMSE)")
            print(f"• Hız farkı: {time_ratio:.1f}x")
        
        print("\n" + "="*50)
        print(f"✅ Değerlendirme Tamamlandı ({datetime.now().strftime('%H:%M:%S')})")

# Kullanım Örneği
if __name__ == "__main__":
    # Modelleri yükle
    models = load_models_and_data()  # Sizin mevcut fonksiyonunuz
    
    # Değerlendiriciyi oluştur ve çalıştır
    evaluator = QuickEvaluator()
    evaluator.evaluate({
        'user_based': models['user_based'],
        'item_based': models['item_based']
    })