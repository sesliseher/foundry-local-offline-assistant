# Çevrimdışı RAG Demo Anlatım Metni

Bu demoda Foundry Local tabanlı çevrimdışı belge asistanını görüyoruz. Dış ağ
erişimi geçersiz bir yerel proxy ile engellendi. Sol taraftaki sağlık kontrolü
SQLite indeksinin, embedding modelinin ve sohbet modelinin hazır olduğunu
doğruluyor.

İlk olarak cevaplanabilir bir soru soruyoruz: “Bilgisayar laboratuvarı hafta içi
hangi saatlerde açıktır?” Soru yerel embedding modeliyle vektöre dönüştürülüyor
ve SQLite indeksinde aranıyor.

Sistem, laboratuvarın hafta içi 08.30 ile 17.30 arasında açık olduğunu söylüyor.
Cevabın yanında doğrulanmış `[K1]` kaynak etiketi, benzerlik skoru ve işlem
süreleri gösteriliyor.

Kaynak bölümünü açtığımızda cevabın `ornek_laboratuvar.docx` belgesinin birinci
parçasına dayandığını görüyoruz. Kaynak metni uygulama tarafından doğrudan arama
sonucundan gösterildiği için modelin uydurduğu bir atıf değil.

Son olarak belgelerde bulunmayan kampüs servis güzergâhını soruyoruz. Kaynaklar
arasındaki güven farkı yetersiz olduğu için sistem bilgi bulunamadı cevabını
veriyor ve sohbet modelini çağırmıyor. Böylece çevrimdışı RAG akışı hem kaynaklı
cevap hem de güvenli geri dönüş davranışını tamamlıyor.
