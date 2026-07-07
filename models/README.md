# Bu dosya, eğitilmiş LightGBM modelinin (.pkl) yerini gösterir.
# 
# Üretim ortamında:
# 1. Gerçek hastane randevu verileriyle LightGBM modelini eğitin.
# 2. Model dosyasını pickle ile kaydedin:
#    import pickle
#    with open('models/lightgbm_model.pkl', 'wb') as f:
#        pickle.dump(trained_model, f)
#
# 3. Bu README dosyasını silebilirsiniz.
#
# Demo/geliştirme ortamında:
# app/modules/no_show/model_utils.py içindeki _build_fallback_model()
# fonksiyonu otomatik olarak sentetik bir LightGBM modeli oluşturur.
