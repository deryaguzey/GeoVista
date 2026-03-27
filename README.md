# 💠 GeoVista V5.4: Profesyonel CBS (GIS) ve Afet Simülasyon Platformu

GeoVista V5.4, coğrafya öğrencileri, CBS profesyonelleri ve afet yönetimi uzmanları için tasarlanmış, yüksek performanslı bir 3D mekânsal analiz ve simülasyon platformudur. Python tabanlı bu uygulama, modern bir arayüz ile gelişmiş 3D görselleştirme teknolojilerini (MapLibre GL JS) birleştirerek afetlerin etkilerini dinamik olarak modelleme imkanı sunar.

## 🚀 Öne Çıkan Özellikler

### 🌋 SafetLab Extreme 3D (Afet Simülasyonu)
- **🌊 3D Taşkın ve Sel**: Araziye duyarlı (Terrain-aware) su yükselme animasyonu. Sadece dere yatakları ve alçak zeminler etkilenirken, güvenli bölgeler (Safe Zone) net bir şekilde ayırt edilir.
- **💥 Sismik Hasar Modeli (Deprem)**: 
  - Magnitude (Mw) bazlı dinamik risk halkaları.
  - Binaların yatay kayması (`fill-extrusion-translate`) ve yüksek katlı binaların sarsıntı anında çökme (pancaking) animasyonları.
  - 15 saniyelik otomatik sönümleme ve raporlama sayacı.
- **⛰️ 3D Heyelan Risk Haritası**: Hillshade (kabartma) ve DEM (yükseklik) verileri ile 5 farklı risk seviyesinde (Çok Yüksek -> Güvenli) dik yamaç analizi.

### 🧪 Mekânsal Veri Laboratuvarı
- **Vektör Analizi**: `.shp` (Shapefile) ve `.geojson` veri setlerini yükleme, görüntüleme ve ArcGIS/QGIS uyumlu export alma.
- **Buffer (Tampon Bölge)**: Koordinat bazlı veya alan bazlı etki analizi.
- **Koordinat Araçları**: Hassas UTM (WGS84) dönüşümleri, Haversine mesafe ölçümü ve yön açısı (bearing) hesaplama.

### 🛰️ Modern CBS Motoru
- **3D Render**: MapLibre GL JS ile donanım hızlandırmalı bina ve arazi görselleştirme.
- **WMS Servisleri**: NASA GIBS ve ESA Sentinel-2 verilerine anlık erişim.
- **Hava Kalitesi ve İklim**: Open-Meteo entegrasyonu ile anlık meteoroloji ve hava kalitesi indeksleri.

## 🛠️ Teknoloji Yığını
- **Arayüz**: CustomTkinter
- **3D Render**: MapLibre GL JS (HTML/JS Injection)
- **CBS Motoru**: GeoPandas, Shapely, Fiona, PyProj, Folium
- **Görselleştirme**: Pillow (PIL), Matplotlib

## 📦 Kurulum ve Çalıştırma

```bash
# Depoyu kopyalayın
git clone https://github.com/deryaguzey/GeoVista.git
cd GeoVista

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# Uygulamayı başlatın
python geoVista.py
```

## 👤 Geliştirici
**Derya Güzey**
- GitHub: [@deryaguzey](https://github.com/deryaguzey)

## 📄 Lisans
Bu proje **MIT Lisansı** ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakabilirsiniz.

---
**Coğrafi Bilgi Sistemleri (CBS) Geleceği İçin Tasarlandı** 🌍🚀
