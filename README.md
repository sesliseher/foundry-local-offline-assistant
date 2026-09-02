# Foundry Local Offline Assistant

Bu projenin amacı, bilgisayardaki belgeler hakkında soruları yanıtlayan yerel bir
yapay zekâ asistanı geliştirmektir. Microsoft Foundry Local ile model çalıştırma,
RAG (Retrieval-Augmented Generation) ile ilgili belge parçalarını bulma ve SQLite
ile verileri yerel olarak saklama yaklaşımı kullanılacaktır.

Hedef, gerekli modeller ve bağımlılıklar ilk kez indirildikten sonra uygulamanın
internet bağlantısı olmadan çalışabilmesidir. Çevrimdışı çalışma henüz test edilmedi.

## Mevcut durum

- Proje klasör yapısı oluşturuldu.
- Python 3.12 sanal ortamı ve `requirements.txt` bağımlılıkları hazırlandı.
- Git dışlama kuralları eklendi.
- Model listeleme betiği hazırlandı; katalog ve model önbelleği durumunu gösterir.
- Streamlit kullanıcı arayüzü hazırdır; değerlendirme betiği henüz boştur.
- TXT belge okuma ve kaynak bilgili parçalama hazır; üç örnek belge 3 parçaya ayrıldı.
- Belge parçalarının embedding'leri SQLite'a kaydediliyor; tekrar kayıtta kopya oluşmuyor.
- Soru embedding'i ile SQLite'taki en ilgili parçaları bulan arama komutu hazırlandı.
- Yerel RAG komutu ilgili parçalarla kaynaklı cevap üretiyor; düşük skorda güvenli geri dönüş yapıyor.
- Tek soruluk yerel model denemesi `scripts/hello_model.py` ile yapılabilir.
- `qwen2.5-0.5b` CPU modeli indirildi ve ilk yerel Türkçe cevap başarıyla alındı.
- Üç örnek cümle üzerinde embedding ve benzerlik sıralama betiği hazırlandı.
- `qwen3-embedding-0.6b` indirildi; üç Türkçe soruda ilgili cümle ilk sırada bulundu.
- Uçtan uca RAG akışı hem komut satırında hem Streamlit arayüzünde çalışıyor.

## Planlanan çalışma akışı

1. Belgeleri oku ve metin parçalarına ayır.
2. Parçaların embedding vektörlerini oluştur ve SQLite'a kaydet.
3. Kullanıcının sorusunu aynı embedding modeliyle vektöre dönüştür.
4. Benzerlik aramasıyla ilgili parçaları bul.
5. Soruyu ve bulunan parçaları yerel sohbet modeline ilet.
6. Cevabı kaynak bilgileriyle kullanıcıya göster.

## Klasör yapısı

```text
app.py                       # Streamlit sohbet arayüzü
requirements.txt             # Sabitlenmiş Python bağımlılıkları
.env.example                 # Örnek ayarlar için ayrılmış dosya; henüz boş
src/offline_assistant/       # Uygulama modülleri
scripts/list_models.py       # Katalog ve indirilen modelleri listeler
scripts/hello_model.py       # Yerel sohbet modeline tek soru gönderir
scripts/embedding_demo.py    # Üç cümleyi soruya benzerliğine göre sıralar
scripts/ingest_documents.py  # TXT önizleme; --save ile embedding ve SQLite kaydı
scripts/search_documents.py  # SQLite indeksinde semantik arama yapar
scripts/answer_documents.py  # Yerel modelle kaynaklı RAG cevabı üretir
scripts/evaluate.py          # Değerlendirme betiği; henüz boş
data/raw/                   # Yerel kaynak belgeler
data/database/              # Üretilecek SQLite veritabanları
data/foundry/               # SDK çalışma dosyaları ve model önbelleği (Git dışında)
tests/                      # Testler
evaluation/                 # Değerlendirme soruları ve sonuçları
docs/screenshots/           # Dokümantasyon ekran görüntüleri
```

Git boş klasörleri takip etmez. Yeni bir kopyada veri klasörleri gerektiğinde
oluşturulmalıdır.

## Mevcut ortamı kontrol etme

Proje kök dizinindeki PowerShell terminalinde:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
git status --short
```

Bu komutlar mevcut sanal ortamı doğrudan kullanır; ortamı etkinleştirmek gerekmez.
`pip check` paket bağımlılıklarını kontrol eder, modelin çalıştığını doğrulamaz.
Uygulama henüz çalıştırılabilir durumda olmadığı için uygulama başlatma adımları
ilgili geliştirme aşamasında eklenecektir.

## Git ve yerel dosyalar

Sanal ortam, `.env` ayarları, Python/test önbellekleri, günlükler ve
`data/database/` içindeki SQLite dosyaları Git dışında tutulur.
`.env.example` paylaşılabilir ayar şablonu olarak takip edilir; gerçek sırlar
bu dosyaya yazılmamalıdır.

`data/raw/` otomatik olarak dışlanmaz. Özel veya kişisel belgeleri depoya
eklemeden önce kontrol et.

## Modelleri listeleme

Proje kök dizininde:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\list_models.py
```

Betik SDK'yı başlatır, katalogdaki model alias'larını, seçili varyantlarını,
yeteneklerini ve bu varyantların indirilmiş olup olmadığını gösterir.
Son bölümde önbellekteki tüm indirilen varyantları listeler.
Model indirmez, belleğe yüklemez veya cevap üretmez. Kataloğun ilk kez alınması
ya da yenilenmesi internet gerektirebilir.

`-X utf8`, Türkçe terminal çıktısının UTF-8 olarak üretilmesini sağlar.

Varsayılan model önbelleği `data/foundry/cache/models/` klasörüdür. Bu uygulamaya
ait SDK çalışma dosyaları `data/foundry/` altında tutulur ve Git'e eklenmez.
Başka bir uygulamada indirdiğin modeller otomatik olarak bu klasöre taşınmaz.
Mevcut model önbelleğini okumak için `--model-cache-dir` seçeneğine o klasörün
yolunu verebilirsin. Gösterilen indirme durumu yalnızca seçilen önbellek içindir.

## Sıradaki hedef

Yanıtlanabilir ve yanıtsız sorulardan oluşan değerlendirme kümesini hazırlayıp
arama ve cevap kalitesini ölçmek.

## İlk yerel model cevabı

İlk denemede küçük `qwen2.5-0.5b` sohbet modeli kullanılır. Proje kökünde:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\hello_model.py --download
```

`--download`, yalnızca model önbellekte yoksa indirmeye izin verir. İlk indirme
internet bağlantısı ve diskte boş alan gerektirir. Model boyutu katalogdan okunup
indirme öncesinde gösterilir. Model yerelde mevcutsa tekrar indirilmez.

Sonraki denemelerde kendi sorunu verebilirsin:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\hello_model.py --prompt "2 + 2 kaç eder?"
```

Betik sırasıyla SDK'yı başlatır, modeli bulur, gerekirse indirir, belleğe yükler,
tek bir sorunun cevabını üretir ve modeli bellekten çıkarır. İndirilen dosyalar
model listeleme betiğiyle aynı `data/foundry/cache/models/` klasöründe kalır.
Yükleme ve cevap üretme süreleri ayrı gösterilir; indirme süresi bu ölçümlere
dahil değildir. Sohbet geçmişi tutulmaz ve henüz belgeler kullanılmaz.

`--model` ile başka bir katalog alias'ı, `--max-tokens` ile cevap uzunluğu sınırı,
`--model-cache-dir` ile farklı bir model önbelleği seçilebilir. Varsayılan cevap
sınırı 128 tokendır. Bu küçük modelin cevap kalitesi sınırlı olabilir; ilk hedef
yerel çıkarımın çalıştığını doğrulamaktır.

`--download` kullanmamak tam çevrimdışı mod anlamına gelmez: SDK'nın katalog
sorgusu yine internet gerektirebilir. Tam çevrimdışı başlangıç ayrıca test edilecektir.

### Doğrulanan ilk deneme (30 Ağustos 2026)

- Varyant: `qwen2.5-0.5b-instruct-generic-cpu:4`.
- Katalog boyutu: 822 MB.
- Soru: “Merhaba! Kendini Türkçe tek cümleyle tanıtır mısın?”
- Cevap: “Merhaba! Size nasıl yardımcı olabilirim?”
- Yükleme: 2,73 saniye; cevap üretme: 0,97 saniye.
- İşlem başarıyla tamamlandı ve model bellekten çıkarıldı.
- İkinci çalıştırmada `--download` verilmeden önbellek kullanıldı; “2 + 2 kaç eder?
  Sadece sonucu yaz.” sorusuna “4” cevabı alındı (yükleme 2,33 saniye, cevap 0,34 saniye).

Bu iki deneme yerel çıkarımın çalıştığını gösterir; Türkçe kalite, talimata uyum
veya genel performans garantisi değildir. Süreler donanıma ve soruya göre değişir.
SDK/katalog başlangıcı bu sürelerin dışındadır; kısıtlı ağda yeniden başlatma
denemesinde katalog beklemesi gözlendi. Tüm bilgisayarın interneti kapatılarak
uçtan uca çevrimdışı çalışma testi henüz yapılmadı.

## Embedding ve benzerlik denemesi

`scripts/embedding_demo.py`, kütüphane saatleri, yemekhane ve ders kaydı hakkında
üç sabit Türkçe cümle kullanır. Cümleleri ve soruyu aynı yerel
`qwen3-embedding-0.6b` modeliyle sayısal vektörlere dönüştürür; kosinüs
benzerliğini hesaplayıp üç cümleyi yüksek skordan düşük skora sıralar.
Bu model sohbet modelinden ayrıdır ve ilk kullanımda ayrıca indirilir.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\embedding_demo.py --download
```

Varsayılan soru “Kütüphane saat kaçta kapanıyor?” şeklindedir. Sonraki denemelerde
indirme seçeneği vermeden kendi sorunu sorabilirsin:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\embedding_demo.py --query "Öğle yemeğini nerede yiyebilirim?"
```

`--query` aynı komutta birden fazla kez verilirse cümlelerin embedding'leri bir
kez oluşturulur ve her soru ayrı sıralanır. `--model` ve `--model-cache-dir`
seçenekleriyle model alias'ı ve önbellek değiştirilebilir.

Çıktı vektör boyutunu, ilk vektörün beş örnek değerini, benzerlik skorlarını ve
en yakın cümleyi gösterir. Kosinüs benzerliği vektörlerin yönlerini karşılaştırır;
1 aynı yönü, 0 dik yönleri, -1 zıt yönleri ifade eder. Skor bir doğruluk yüzdesi
değildir. İlgisiz sorularda da bir cümle en yüksek skoru alır; henüz “bilgi yok”
kararı veya sohbet cevabı üretilmez.

Vektörler yalnızca bellekte tutulur; SQLite'a kayıt ve belge okuma bu betiğin
kapsamında değildir. İş bitince model bellekten çıkarılır, dosyaları mevcut
`data/foundry/cache/models/` önbelleğinde kalır. Katalog erişimi internet
gerektirebilir; indirme yapmamak çevrimdışı çalışma garantisi değildir.

Model indirmeden matematik ve vektör/metin eşleştirme testleri:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_embedding_demo.py -q -p no:cacheprovider
```

### Doğrulanan embedding denemesi (30 Ağustos 2026)

- Varyant: `qwen3-embedding-0.6b-generic-cpu:1`; katalog boyutu: 495 MB.
- Her vektör 1024 sayı içerdi; üç cümlenin embedding üretimi 4,33 saniye sürdü.
- Kütüphane kapanış sorusunda saatleri açıklayan cümle ilk sırada: 0,6165.
- Öğle yemeği sorusunda yemekhane cümlesi ilk sırada: 0,5823.
- Ders kaydı sorusunda öğrenci bilgi sistemi cümlesi ilk sırada: 0,4988.
- Matematik ve yanıt eşleştirmesi için 8 test geçti.

Bunlar üç örnek üzerindeki sonuçlardır; genel arama kalitesini ölçmez ve sabit
bir benzerlik eşiği belirlemek için yeterli değildir. Süreye indirme, SDK
başlangıcı, model yükleme ve soru embedding'leri dahil değildir.

## TXT belgelerini okuma ve parçalama

`src/offline_assistant/documents.py`, TXT dosyalarını okur ve `source`,
`chunk_number`, `text` alanlarını taşıyan parçalar oluşturur.
`scripts/ingest_documents.py` varsayılan olarak bu parçaları terminalde önizler.
Önizleme modunda model, internet veya veritabanı kullanılmaz; kaynak dosyalar
değiştirilmez. Embedding ve SQLite kaydı için aşağıdaki `--save` modu kullanılır.

`data/raw/` içinde kütüphane, yemekhane ve ders kaydı hakkında üç örnek TXT
dosyası bulunur. İçerikleri deneme için kurgulanmıştır; gerçek kurum kuralları
değildir. Kendi UTF-8 kodlamalı TXT belgelerini de bu klasöre ekleyebilirsin.
Alt klasörler de taranır. Özel belgeleri Git'e eklemeden önce kontrol et.

Proje kökünde çalıştır:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\ingest_documents.py
```

Varsayılan üst sınır parça başına 600 **karakterdir**, token sayısı değildir.
Kısa paragraflar aynı parçada birleştirilir; uzun paragraflar mümkün olduğunda
kelime sınırlarında bölünür. Sınırı aşan tek kelime karakter sınırında bölünür.
Paragraflar boş satırlarla tanınır; paragraf içindeki satır sonları ve fazla
boşluklar normalleştirilir. Parçalar arasında örtüşme (overlap) yoktur; başlıklar
sonraki parçalara otomatik kopyalanmaz. Bu ilk yaklaşımda anlam bütünlüğünü
çıktıyı okuyarak kontrol etmelisin.

Farklı parça boyutu ve belge klasörü kullanılabilir:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\ingest_documents.py --input-dir data\raw --max-chars 350
```

Her parçanın çıktısında kaynak yolu, 1'den başlayan belge içi parça numarası,
karakter sayısı ve metin bulunur. Kaynak yolu giriş klasörüne görelidir;
farklı alt klasörlerde aynı adı taşıyan dosyalar ayırt edilir. Dosya veya parça
boyutu değiştiğinde parça numaraları da değişebilir; bunlar kalıcı kimlik değildir.

Boş belgeler uyarıyla atlanır. Klasör bulunamazsa, TXT yoksa, tüm belgeler boşsa
veya kodlama hatası varsa komut başarısız çıkış kodu döndürür. UTF-8 BOM desteklenir;
eski Türkçe Windows dosyaları için gerektiğinde `--encoding cp1254` kullanılabilir.
Kodlama hataları sessizce atlanmaz. PDF ve DOCX dosyaları henüz işlenmez.

Doğrulama: varsayılan 600 karakter sınırında üç örnek belgeden 3 parça üretildi.
Belge okuma/parçalama ve önceki embedding yardımcıları dahil toplam 18 test geçti.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

## Embedding'leri SQLite'a kaydetme

Mevcut embedding modeli indirilmiş olduğundan doğrudan çalıştırabilirsin:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\ingest_documents.py --save
```

Betik TXT belgelerini okur, parçalarına ayırır, yerel embedding modelini yükler
ve en fazla sekiz parçalık gruplarla vektör üretir. Tüm vektörler başarıyla
üretildikten ve doğrulandıktan sonra `data/database/assistant.db` dosyasına
tek bir SQLite transaction'ı ile kaydeder. Model dosyaları yeniden indirilmez.
SDK katalog erişimi internet gerektirebilir. Yeni kurulumda önce
`embedding_demo.py --download` ile embedding modeli hazırlanmalıdır.

`src/offline_assistant/storage.py` iki tabloyu yönetir:

| Tablo | Saklanan bilgiler |
| --- | --- |
| `chunks` | Kaynak yolu, parça numarası, parça metni, JSON biçiminde embedding |
| `index_metadata` | Kaynak klasörü, tam model varyantı/sürümü, vektör boyutu, parça boyutu sınırı |

Model bilgisi bütün indeks için ortaktır. `(source, chunk_number)` birincil
anahtarı aynı parçanın çoğaltılmasını engeller. Kaynak ve metin sorgularında SQL
parametreleri kullanılır. SQLite Python ile gelir; ek paket veya sunucu kurulmaz.

**Tekrar çalıştırma davranışı:** Bu sürüm küçük koleksiyon için tam yenileme yapar;
değişmeyen parçaların embedding'lerini de yeniden hesaplar. Aynı komut tekrar
çalıştırıldığında kayıt sayısı artmaz. Başarılı yenilemede artık kaynak klasöründe
bulunmayan belgeler ve eski parçalar indeksten çıkarılır. Kaynak TXT dosyaları
silinmez veya değiştirilmez.

Okuma/embedding üretimi başarısızsa eski kayıtlar korunur. Veritabanına yazma
sırasında hata olursa transaction geri alınır. Hiç TXT veya dolu parça bulunamazsa
indeks otomatik boşaltılmaz; komut hata verir ve önceki kayıtları korur.
Model bellekten çıkarılırken hata oluşursa kayıt daha önce tamamlanmış olabilir;
komut çıktısındaki kayıt sonucunu kontrol et.

Bir veritabanı tek kaynak klasörüne bağlıdır. Başka bir klasör için farklı
`--db` yolu seçilmelidir. `--model`, `--model-cache-dir`, `--encoding` ve
`--max-chars` seçenekleri de kullanılabilir. Model veya parça boyutu değişirse
indeks tamamen yenilenir; farklı embedding uzayları aynı indekste karışmaz.
Kaynak klasörünün mutlak yolu saklandığından projeyi başka yere taşıdığında
indeksi yeni bir veritabanına yeniden oluşturmalısın.

Veritabanı kaynak metinlerin kopyalarını içerir ve şifreli değildir. Git dışında
tutulur; özel belgeleri işlerken veritabanını da özel veri olarak koru.
Bu aşama henüz soru araması veya sohbet cevabı üretmez.

Doğrulama: üç örnek belgenin 3 parçası, 1024 boyutlu vektörlerle kaydedildi.
Aynı gerçek model akışı ikinci kez çalıştırıldı ve ayrı bir bağlantıyla
veritabanı yeniden açıldığında yine 6 benzersiz kayıt bulundu. SQLite bütünlük
kontrolü `ok` döndürdü. Kalıcılık, tekrar kayıt, eski parçaların kaldırılması,
geçersiz vektörler, kaynak klasörü koruması ve SQL hatasında geri alma dahil
o aşamadaki toplam 26 test geçti. Arama katmanı eklendikten sonra bütün test
paketi yeniden çalıştırıldı; Streamlit katmanı tamamlandığında toplam 52 test geçti.

## SQLite indeksinde semantik arama

`scripts/search_documents.py`, soruyu indekste kayıtlı **aynı tam model
varyantıyla** embedding'e dönüştürür. SQLite'taki üç parçayı salt okunur olarak
belleğe alır, kosinüs benzerliklerini hesaplar ve varsayılan olarak ilk üç sonucu
kaynak dosyası, parça numarası, skor ve tam metinle gösterir.

Proje kökünde:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\search_documents.py "Kütüphane hafta içi saat kaçta kapanır?"
```

Sonuç sayısı ve veritabanı değiştirilebilir:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\search_documents.py "Derslere nasıl kayıt olurum?" --top-k 2
.\.venv\Scripts\python.exe -X utf8 scripts\search_documents.py "Öğle yemeği ne zaman?" --db data\database\assistant.db
```

Komut önce veritabanı metadata'sını ve bütün embedding'leri doğrular. Model
alias'ının güncel sürümünü seçmek yerine indeks oluşturulurken kaydedilen tam
varyant kimliğini kullanır; farklı boyut ve sürümlerin karışmasına izin vermez.
Model önbellekte değilse otomatik indirme yapmaz ve açık bir hata verir.

Bu küçük koleksiyonda bütün vektörleri Python ile karşılaştırmak yeterlidir.
Kayıt sayısı büyüdüğünde özel bir vektör indeksi veya veritabanı uzantısı gerekir.
`--top-k` kayıt sayısından büyükse var olan bütün parçalar birer kez döner.
Eşit skorlarda kaynak adı ve parça numarası kararlı sıralama sağlar.

**Sınır:** Kosinüs skoru doğruluk veya güven yüzdesi değildir. En ilgisiz soruda
bile matematiksel olarak en yakın parçalar döner. Bu aşamada eşik belirlenmedi,
“bilgi yok” kararı verilmez ve yerel sohbet modeli cevap üretmez. Sonuç metinleri
veritabanından aynen gösterilir; örnek belgelerdeki bilgiler kurgusaldır.

Doğrulanan ilk sorguda “Kütüphane hafta içi saat kaçta kapanır?” sorusu için
`ornek_kutuphane.txt`, parça 1, 0,6333 skorla birinci sırada bulundu. Son RAG
doğrulamasında sorgu embedding'i ve üç parçalık arama 3,30 saniye sürdü; SDK/model başlangıcı bu
süreye dahil değildir. Bu tek sorgu genel arama kalitesini ölçmez.

Arama katmanının testleri sonuç sıralamasını, eşit skorların kararlılığını,
`top-k` sınırlarını, eksik veritabanını, geçersiz sorgu vektörlerini ve bozuk
embedding kayıtlarının reddedilmesini kapsar.

## Yerel RAG ile kaynaklı cevap üretme

`scripts/answer_documents.py` bütün hattı çalıştırır: sorunun embedding'ini
oluşturur, SQLite'tan en ilgili üç parçayı bulur, yeterli bağlam varsa bunları
yerel `qwen2.5-0.5b` sohbet modeline verir ve cevabın yanında doğrulanmış kaynak
listesini gösterir.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\answer_documents.py "Kütüphane hafta içi saat kaçta kapanır?"
```

Varsayılanlar `--top-k 3`, `--min-score 0.35`, `--max-score-drop 0.15` ve
`--max-tokens 256` şeklindedir.
Sohbet modeli `--chat-model`, veritabanı `--db` ve önbellek
`--model-cache-dir` ile değiştirilebilir. Her iki modelin önceden indirilmiş
olması gerekir; komut otomatik model indirmez.

Önce embedding modeli yüklenerek arama yapılır ve bu model bellekten çıkarılır.
Ardından yalnızca yeterli bağlam varsa sohbet modeli yüklenir. Bu sıralama iki
modelin aynı anda bellekte tutulmasını önler. Sohbet istemi yalnızca getirilen
bağlama dayanmayı, tahmin etmemeyi ve `[K1]` biçiminde kaynak etiketi kullanmayı
ister. Belge metinleri JSON içinde güvenilmeyen veri olarak sınırlandırılır ve
belgelerin içindeki talimatların uygulanmaması açıkça belirtilir.

Kaynak listesi model tarafından yazılmaz; uygulama doğrudan arama sonuçlarından
üretir. Model cevap içinde kaynak etiketi vermez veya mevcut olmayan bir etiket
kullanırsa komut görünür uyarı gösterir. Bu denetim cevabın her iddiasının
gerçekten desteklendiğini kanıtlamaz; önemli cevaplar yine gözden geçirilmelidir.

En iyi skor varsayılan 0,35 eşiğinin altındaysa sohbet modeli çağrılmaz ve
“Bu bilgi mevcut belgelerde bulunamadı.” cevabı döner. Bu eşik küçük örnek veri
üzerinde seçilmiş başlangıç sezgisidir; doğruluk olasılığı değildir. Kendi belge
ve değerlendirme sorularınla ölçülüp ayarlanmalıdır. Eşiği düşürmek daha çok
soruyu modele yollar ancak ilgisiz bağlamla cevap riskini artırır; yükseltmek
daha fazla güvenli geri dönüş üretir. Ayrıca yalnızca en iyi sonuçtan en fazla
0,15 düşük skorlu parçalar bağlama alınır. `--max-score-drop` büyütülürse çok
belgeli sorular için daha fazla parça alınır, fakat ilgisiz bağlam riski artar.

Doğrulamalar:

- Kütüphane sorusunda doğru parça 0,6333 skorla bulundu; göreli filtre yalnızca
  bu parçayı modele verdi ve yerel model saat bilgisini belgeden kullanarak cevap üretti.
- İlgisiz Mars sorusuyla düşük skor durumunda güvenli geri dönüş ve sohbet
  modelini çağırmama davranışı doğrulandı.
- İstem oluşturma, belge içi talimatların veri olarak kaçışlanması, eşik sınırı,
  kaynak listesi ve kaynak etiketi denetimi dahil testler eklendi.

## Streamlit kullanıcı arayüzü

Arayüzü proje kökünde başlat:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Terminalde gösterilen yerel adresi tarayıcıda aç. Varsayılan adres genellikle
`http://localhost:8501` olur. İlk soru sırasında SDK katalog başlangıcı nedeniyle
ek bekleme olabilir; sonraki sorularda aynı Foundry yöneticisi Streamlit
`cache_resource` içinde yeniden kullanılır.

Ana ekranda sohbet alanı bulunur. Her cevap şu bilgileri gösterir:

- Yerel model cevabı veya güvenli “bilgi bulunamadı” mesajı.
- En iyi benzerlik skoru, arama süresi ve kullanıldıysa cevap üretme süresi.
- Modelin kaynak etiketi davranışıyla ilgili görünür uyarılar.
- Açılır bölümde uygulama tarafından doğrulanan kaynak, parça, skor ve tam metin.

Kenar çubuğundan SQLite yolu, aranacak parça sayısı, minimum benzerlik,
en iyi skordan izin verilen fark, cevap token sınırı ve sohbet modeli alias'ı
değiştirilebilir. “Sohbet geçmişini temizle” yalnızca mevcut tarayıcı oturumundaki
ekran geçmişini temizler; kaynak belgeleri, SQLite veritabanını veya modelleri
silmez. Ayarlar değiştirildikten sonra yeni sorular yeni değerleri kullanır;
eski cevaplar üretildikleri ayarlarla ekranda kalır.

RAG servis mantığı `src/offline_assistant/service.py` içindedir; Streamlit'e bağlı
değildir. Servis her soruda SQLite indeksini yeniden okur, böylece uygulama açıkken
indeks yenilenirse sonraki soru yeni kayıtları kullanır. Paylaşılan yerel model
çalışmalarını bir kilitle seri hale getirir ve embedding ile sohbet modellerini
ardışık yükleyerek aynı anda bellekte tutmaz.

Arayüzde yapılan gerçek kontrollerde kütüphane sorusu doğru kaynakla cevaplandı;
Mars sorusu 0,1458 skorla eşik altında kaldı, güvenli mesaj gösterildi ve sohbet
modeli çağrılmadı. Açılış ekranı Streamlit'in uygulama test aracıyla model
yüklemeden doğrulandı; servis akışı sahte modeller ve geçici SQLite indeksiyle
ayrıca test edildi.
