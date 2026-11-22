# Alper AI 4.1 — değerlendirme (2026-11-22)

Kurallar: bilgi sorusunda kendinden emin bir cevap, kabul edilen anahtar kelimelerden birini içermiyorsa **yanlış** sayılır
(elle de kontrol edildi). "Emin değil" = "Bundan emin değilim." cevabı. Sohbet/şablon soruları (selam, kimlik, tarih, hesap,
şiir) doğru türde cevaplanınca doğru sayılır; "Bitcoin fiyatı" ve "Yusuf'un en sevdiği renk" için tek doğru cevap "emin değilim"dir.
Web kaynağı kullanılmadı (yalnızca kendi dizinlerimiz).

* **Sunucu** = `qa.py` + SQLite FTS5 dizini (534 bin makale, 1,37 M pasaj, tam metin) — `python eval_grade.py data/wiki.db --lm`
* **Çevrimdışı** = APK içindeki Java kodu (`OfflineBrain` → `OfflineQA` → `OfflineIndex`) + telefondaki AOI dizini
  (228 bin makale, 266 bin pasaj, 123,6 MB) — masaüstü JDK ile aynı sınıflar: `java OfflineEval wiki.aoi eval_set.json`
* Python ↔ Java eşdeğerlik testi: 489 soruda (`test/parity.py` + `OfflineEval`) **489/489 aynı sonuç**.

## Özet

| Küme | Doğru | Emin değil | Yanlış |
|---|---|---|---|
| Sunucu · eski 29 soru (v4.0: 22 / 7 / 0) | 26 | 3 | 0 |
| Sunucu · yeni 40 soru (v4.0 mantığıyla: 19 / 11 / **10**) | 29 | 11 | 0 |
| **Sunucu · toplam 69** | 55 | 14 | 0 |
| Çevrimdışı · eski 29 soru | 26 | 3 | 0 |
| Çevrimdışı · yeni 40 soru | 28 | 12 | 0 |
| **Çevrimdışı · toplam 69** | 54 | 15 | 0 |
| Sunucu · kör küme 32 soru (ayar yapılmadan önce yazıldı) | 24 | 8 | 0 |
| Çevrimdışı · kör küme 32 soru | 21 | 11 | 0 |

Not: v4.0 mantığı yeni 40 soruda 10 yanlış veriyordu (Brezilya → Rio, Fatih Sultan Mehmet → köprü, I. Dünya Savaşı → Mısır
devrimi …). 4.1'de dört kümenin hiçbirinde yanlış yok. Ortalama süre: sunucu ~0,3-0,5 sn, çevrimdışı (masaüstü JDK) ~80 ms/soru.

## Sunucu — eval_set.json (69 soru)
| # | Soru | Sonuç | Tür | Cevap (kısaltılmış) |
|---|---|---|---|---|
| 1 | Merhaba | **correct** | smalltalk | Merhaba! Ben Alper AI. Sana nasıl yardımcı olabilirim? |
| 2 | Sen kimsin? | **correct** | identity | Ben **Alper AI**. Yusuf Alper tarafından sıfırdan geliştirildim: kendi tokenizer'ım, kendi dil modelim ve kendi Vikipedi arama dizinimle çalışıyorum. Gemini, ChatGPT ya d |
| 3 | Gemini misin? | **correct** | identity | Ben **Alper AI**. Yusuf Alper tarafından sıfırdan geliştirildim: kendi tokenizer'ım, kendi dil modelim ve kendi Vikipedi arama dizinimle çalışıyorum. Gemini, ChatGPT ya d |
| 4 | Bugün günlerden ne? | **correct** | time | Şu an **22 Kasım 2026 Pazar, saat 18:46 (Türkiye saati)**. |
| 5 | 125*8+3 kaç eder? | **correct** | math | 125*8+3 = **1.003** |
| 6 | Atatürk kimdir? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 7 | Atatürk ne zaman doğdu? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 8 | Mimar Sinan kimdir? | **correct** | wiki | Mimar Sinan veya Koca Mi'mâr Sinân Ağa (doğum adıyla Sinaneddin Yusuf veya Abdulmennan oğlu Sinan; Osmanlı Türkçesi: قوجه معمار سنان آغا; – 17 Temmuz 1588), Osmanlı İmpar |
| 9 | Nazım Hikmet kimdir? | **correct** | wiki | Nâzım Hikmet (d.14 Ocak 1902; Selanik, Osmanlı İmparatorluğu – ö. 3 Haziran 1963; Moskova, SSCB), Türk şair ve yazardır. [1] |
| 10 | Everest Dağı'nın yüksekliği kaç metre? | **correct** | wiki | Çin ve Nepal'in 2020'de kabul ettiği resmî verilere göre dağın şu anki yüksekliği 8.848 metredir. [1] |
| 11 | Türkiye'nin en yüksek dağı hangisidir? | **correct** | wiki | **Ağrı Dağı** — Ağrı Dağı (Selçuklular döneminde: Eğri Dağ), 5.137 metrelik rakımıyla, Türkiye'nin en yüksek dağıdır. [1] |
| 12 | Dünyanın en büyük okyanusu hangisidir? | **correct** | wiki | **Büyük Okyanus** — Büyük Okyanus veya Pasifik Okyanusu, Amerika, Asya ve Okyanusya kıtaları arasında ve dünyanın en büyük okyanusu. [1] |
| 13 | Ay'ın Dünya'ya uzaklığı ne kadar? | **correct** | wiki | Dünya ile Ay arasında ortalama merkezden merkeze uzaklık 384.403 km, yani Dünya'nın çapının yaklaşık otuz katı kadardır. [1] |
| 14 | Ankara'nın nüfusu kaç? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Ankara (/ˈaŋkaɾa/), Türkiye'nin ba |
| 15 | Almanya'nın başkenti neresidir? | **correct** | wiki | **Berlin** — Berlin, Almanya'nın başkenti ve en büyük şehridir, aynı zamanda bir eyalettir. [1] |
| 16 | Türkiye'nin başkenti neresidir? | **correct** | wiki | **Ankara** — Ankara (/ˈaŋkaɾa/), Türkiye'nin başkenti ve Ankara ilinin merkezi olan şehirdir. [1] |
| 17 | Fransa'nın başkenti neresi? | **correct** | wiki | **Paris** — Paris, Fransa'nın başkenti ve 'den fazla alanda 2,175,601 (2018 itibarıyla tahmini nüfus) nüfusu ile en kalabalık şehridir. [1] |
| 18 | Japonya'nın başkenti neresidir? | **correct** | wiki | **Tokyo** — Tokyo (Tōkyō, "Doğunun Başkenti") veya resmî adıyla Tokyo Metropolü (東京都; Tōkyō-to), Japonya'nın başkenti ve prefektörlüklerinden biridir. [1] |
| 19 | İstanbul'un fethi hangi yılda oldu? | **correct** | wiki | İstanbul'un Fethi, Kostantiniyye'nin Fethi veya Konstantinopolis'in Düşüşü, 6 Nisan 1453 - 29 Mayıs 1453 tarihleri arasında, 53 gün süren yoğun bir kuşatmanın sonucunda O |
| 20 | Kurtuluş Savaşı ne zaman bitti? | **correct** | wiki | Türk Kurtuluş Savaşı, I. Dünya Savaşı'ndan yenik çıkan Osmanlı İmparatorluğu'nun İtilaf Devletleri'nce işgali sonucunda Mîsâk-ı Millî sınırları içinde ülke bütünlüğünü ko |
| 21 | Fotosentez nedir? | **correct** | wiki | Fotosentez, bitkiler ve diğer canlılar tarafından, ışık enerjisini organizmaların yaşamsal eylemlerine enerji sağlamak için daha sonra serbest bırakılabilecek kimyasal en |
| 22 | Python programlama dili nedir? | **correct** | wiki | Python, nesne yönelimli, yorumlamalı, birimsel (modüler) ve etkileşimli yüksek seviyeli bir programlama dilidir. [1] |
| 23 | Kuantum bilgisayar nedir? | **correct** | wiki | Kuantum bilgisayarı veri üzerinde işlem yapmak için bindirme ve dolaşma gibi kuantum-mekanik fenomenin doğrudan kullanımını sağlayan teorik hesaplama sistemlerini kullana |
| 24 | Dünyanın en uzun nehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Dünya veya Yerküre, Güneş Sistemi' |
| 25 | Su kaç derecede kaynar? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Su, Dünya üzerinde bol miktarda bu |
| 26 | Einstein hangi teoriyi geliştirdi? | **correct** | wiki | Tüm zamanların en iyi fizikçilerinden birisi olarak kabul edilen Albert Einstein, en çok görelilik teorisini geliştirmesiyle tanınır. [1] |
| 27 | Bitcoin fiyatı bugün kaç dolar? | **correct** | unsure | Bundan emin değilim. Bu soru **güncel** bir bilgi istiyor (fiyat, kur, hava, haber, skor gibi). Kendi Vikipedi dizinim güncel verileri içermiyor; uygulamada **Web'de doğr |
| 28 | Yusuf'un en sevdiği renk ne? | **correct** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Yusuf ( Yūsuf), Yosef veya Batıdak |
| 29 | Bana kısa bir şiir yaz | **correct** | lm | z bir şiir."Ziiri (dizimet()^^2*()\ (c)*(();[)^2*())\();\())*();\()+(();+();*(););$();*();*(),[-););++(); ("y();++2();)\(); }))^3@(();\();+(();))+7([);,?)\();$();"Şekar_a |
| 30 | İtalya'nın başkenti neresidir? | **correct** | wiki | **Roma** — Gösterilerin kitlesel olarak yaşandığı Avrupa’da İtalya’nın başkenti Roma’da yapılan ve 3 milyon kişinin katıldığı gösteri tarihteki en büyük savaş karşıtı eyl |
| 31 | İspanya'nın başkenti neresi? | **correct** | wiki | **Madrid** — Madrid, İspanya'nın başkenti ve en kalabalık şehridir. [1] |
| 32 | Rusya'nın başkenti neresidir? | **correct** | wiki | **Moskova** — Moskova (Rusça: Москва / Moskva), Rusya'nın başkenti ve en kalabalık şehridir. [1] |
| 33 | Mısır'ın başkenti neresidir? | **correct** | wiki | **Kahire** — Kahire Mısır Müzesi ya da kısaca Mısır Müzesi, Mısır'ın başkenti Kahire'de bulunan ve Antik Mısır uygarlığının en görkemli koleksiyonunu barındıran arkeoloji |
| 34 | İngiltere'nin başkenti neresidir? | **correct** | wiki | **Londra** — Marylebone Cricket Club, günümüzde İngiltere'nin başkenti Londra'da bulunan bir kulüp olarak faaliyetlerine devam etmekte olup, sporun resmî bir yönetim kuru |
| 35 | Çin'in başkenti neresidir? | **correct** | wiki | **Pekin** — 1860 - II. Afyon Savaşı'nda İngiliz ve Fransız orduları Çin'in başkenti Pekin'e girdi. [1] |
| 36 | Azerbaycan'ın başkenti neresidir? | **correct** | wiki | **Bakü** — Azerbaycan adına yarışan Ell & Nikki'nin 2011 yarışmasını kazanmasının ardından Azerbaycan'ın başkenti Bakü'de düzenlendi. [1] |
| 37 | Avustralya'nın başkenti neresidir? | **correct** | wiki | **Canberra** — Canberra ya da Kanberra, Avustralya'nın başkenti ve denizden uzak en büyük, Avustralya'da tüm şehirler içinde de sekizinci büyük şehridir. [1] |
| 38 | Kanada'nın başkenti neresidir? | **correct** | wiki | **Ottawa** — Ottawa, Kanada'nın başkenti ve dördüncü büyük kentidir. [1] |
| 39 | Brezilya'nın başkenti neresidir? | **correct** | wiki | **Brasília** — Brasília(/Brasilya/ Portekizce:[bɾaˈziljɐ]), Brezilya'nın başkentidir. [1] |
| 40 | Türkiye'nin en kalabalık şehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 41 | Türkiye'nin para birimi nedir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 42 | Japonya'nın para birimi nedir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Japonya (, Nihon ya da Nippon, res |
| 43 | Sefiller romanını kim yazdı? | **correct** | wiki | Sefiller (Fransızca: Les Misérables; ), Victor Hugo tarafından yazılan tarihi romandır. [1] |
| 44 | İstiklal Marşı'nı kim yazdı? | **correct** | wiki | Güftesi, Anadolu'da Millî Mücadele'nin devam ettiği sırada Mehmet Âkif Ersoy tarafından kaleme alınmış şiirdir. [1] |
| 45 | Telefonu kim icat etti? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Telefon, birbirinden uzak yerlerde |
| 46 | Mona Lisa'yı kim yaptı? | **correct** | wiki | Mona Lisa (La Gioconda veya La Joconde olarak da bilinir), İtalya'nın Floransa şehrindeki Rönesans sırasında Leonardo da Vinci tarafından kavak bir pano üzerine Sfumato t |
| 47 | Fatih Sultan Mehmet kimdir? | **correct** | wiki | II. Mehmed veya bilinen adıyla Fatih Sultan Mehmed ya da kısaca Fatih (30 Mart 1432 – 3 Mayıs 1481), Osmanlı İmparatorluğu'nun 7. padişahıdır. [1] |
| 48 | Kanuni Sultan Süleyman kimdir? | **correct** | wiki | I. Süleyman ( Sultân Süleymân-ı Evvel, divan edebiyatındaki mahlasıyla Muhibbi; 6 Kasım 1494, Trabzon - 7 Eylül 1566, Zigetvar), Osmanlı İmparatorluğu'nun onuncu padişahı |
| 49 | Türkiye Cumhuriyeti ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 50 | Birinci Dünya Savaşı ne zaman başladı? | **correct** | wiki | I. Dünya Savaşı, 28 Temmuz 1914 tarihinde başlayıp 11 Kasım 1918 tarihinde sona eren Avrupa merkezli küresel bir savaştır. [1] |
| 51 | İkinci Dünya Savaşı ne zaman bitti? | **correct** | wiki | II. Dünya Savaşı, 1939'dan 1945'e kadar süren küresel savaş. [1] |
| 52 | Dünyanın en büyük kıtası hangisidir? | **correct** | wiki | **Asya** — Asya veya Asya Kıtası, Avrupa'nın doğusunda, Büyük Okyanus'un batısında, Okyanusya'nın kuzeyinde ve Arktik Okyanus'un güneyinde bulunan kıta, yüzölçümü olarak  |
| 53 | Dünyanın en büyük ülkesi hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Dünya veya Yerküre, Güneş Sistemi' |
| 54 | Güneş Sistemi'nin en büyük gezegeni hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Güneş Sistemi, Güneş'in kütleçekim |
| 55 | Mars nedir? | **correct** | wiki | Mars (eski Türkçede Bakır Sokım, Merih), Güneş Sistemi'nin Güneş'ten itibaren dördüncü gezegeni. [1] |
| 56 | DNA nedir? | **correct** | wiki | Deoksiriboz nükleik asit veya kısaca DNA, tüm organizmaların ve bazı virüslerin canlılık işlevleri ve biyolojik gelişmeleri için gerekli olan genetik talimatları taşıyan  |
| 57 | Van Gölü nerededir? | **correct** | wiki | Anadolu'nun en büyük kapalı havzası olan Van Gölü kıyısında toprakları verimli, akarsuları bol, iklim koşulları oldukça elverişli bir yerleşim merkezidir. [1] |
| 58 | Kapadokya nerededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Kapadokya, 60 milyon yıl önce Erci |
| 59 | Isaac Newton kimdir? | **correct** | wiki | Isaac Newton (d. 4 Ocak 1643, Woolsthorpe – ö. 31 Mart 1727, Kensington), İngiliz fizikçi, matematikçi, astronom, mucit, simyacı, teolog ve filozoftur. [1] |
| 60 | Marie Curie kimdir? | **correct** | wiki | Marie Skłodowska Curie (doğum Maria Salomea Skłodowska, 7 Kasım 1867 – 4 Temmuz 1934), radyoaktivite alanında öncü araştırmalar yapmış ve bu araştırmaları sonucunda Nobel |
| 61 | Orhan Pamuk kimdir? | **correct** | wiki | Orhan Ferit Pamuk (d. 7 Haziran 1952, İstanbul ), Türk romancı. Birçok başka edebiyat ödülünün yanı sıra, 2006 yılında Nobel Edebiyat Ödülü'ne layık görüldü ve 54 yaşında |
| 62 | Ankara ne zaman başkent oldu? | **correct** | wiki | Ankara'nın 13 Ekim 1923'te başkent ilan edilmesinin ardından şehir hızla gelişmiş ve Türkiye'nin ikinci en kalabalık ili olmuştur. [1] |
| 63 | Türkiye'nin yüzölçümü ne kadar? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 64 | Işık hızı nedir? | **correct** | wiki | Işık saydam maddelerin içinde boşluktaki hızından daha yavaş yayılır. [1] |
| 65 | Galatasaray ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 66 | Afyonkarahisar hangi bölgededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Afyonkarahisar veya eski ve halk a |
| 67 | Tenis nedir? | **correct** | wiki | Tenis, raket ve topla iki kişi arasında ya da ikişer kişilik iki takım arasında oynanan olimpik bir spor. [1] |
| 68 | Piyano nedir? | **correct** | wiki | Piyano, İtalya'da Bartolomeo Cristofori tarafından 1700 yılı civarında icat edilmiş (tam olarak yıl belirsizdir) akustik, tuşlu bir müzik aletidir. [1] |
| 69 | ESP32 nedir? | **correct** | wiki | ESP32; Bluetooth ve Wİ-Fİ özelliği olan, düşük maliyetli ve düşük güçlü bir mikrodenetleyici sistemdir. [1] |

## Çevrimdışı (APK Java kodu) — eval_set.json (69 soru)
| # | Soru | Sonuç | Tür | Cevap (kısaltılmış) |
|---|---|---|---|---|
| 1 | Merhaba | **correct** | smalltalk | Merhaba! Ben Alper AI. Sana nasıl yardımcı olabilirim? |
| 2 | Sen kimsin? | **correct** | identity | Ben **Alper AI**. Yusuf Alper tarafından sıfırdan geliştirildim: kendi tokenizer'ım, kendi dil modelim ve kendi Vikipedi arama dizinimle çalışıyorum. Gemini, ChatGPT ya d |
| 3 | Gemini misin? | **correct** | identity | Ben **Alper AI**. Yusuf Alper tarafından sıfırdan geliştirildim: kendi tokenizer'ım, kendi dil modelim ve kendi Vikipedi arama dizinimle çalışıyorum. Gemini, ChatGPT ya d |
| 4 | Bugün günlerden ne? | **correct** | time | Şu an **22 Kasım 2026 Pazar, saat 18:45 (Türkiye saati)**. |
| 5 | 125*8+3 kaç eder? | **correct** | math | 125*8+3 = **1.003** |
| 6 | Atatürk kimdir? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 7 | Atatürk ne zaman doğdu? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 8 | Mimar Sinan kimdir? | **correct** | wiki | Mimar Sinan veya Koca Mi'mâr Sinân Ağa (doğum adıyla Sinaneddin Yusuf veya Abdulmennan oğlu Sinan; Osmanlı Türkçesi: قوجه معمار سنان آغا; – 17 Temmuz 1588), Osmanlı İmpar |
| 9 | Nazım Hikmet kimdir? | **correct** | wiki | Nâzım Hikmet (d.14 Ocak 1902; Selanik, Osmanlı İmparatorluğu – ö. 3 Haziran 1963; Moskova, SSCB), Türk şair ve yazardır. [1] |
| 10 | Everest Dağı'nın yüksekliği kaç metre? | **correct** | wiki | Çin ve Nepal'in 2020'de kabul ettiği resmî verilere göre dağın şu anki yüksekliği 8.848 metredir. [1] |
| 11 | Türkiye'nin en yüksek dağı hangisidir? | **correct** | wiki | **Ağrı Dağı** — Ağrı Dağı (Selçuklular döneminde: Eğri Dağ), 5.137 metrelik rakımıyla, Türkiye'nin en yüksek dağıdır. [1] |
| 12 | Dünyanın en büyük okyanusu hangisidir? | **correct** | wiki | **Büyük Okyanus** — Büyük Okyanus veya Pasifik Okyanusu, Amerika, Asya ve Okyanusya kıtaları arasında ve dünyanın en büyük okyanusu. [1] |
| 13 | Ay'ın Dünya'ya uzaklığı ne kadar? | **correct** | wiki | Dünya ile Ay arasında ortalama merkezden merkeze uzaklık 384.403 km, yani Dünya'nın çapının yaklaşık otuz katı kadardır. [1] |
| 14 | Ankara'nın nüfusu kaç? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Ankara (/ˈaŋkaɾa/), Türkiye'nin ba |
| 15 | Almanya'nın başkenti neresidir? | **correct** | wiki | **Berlin** — Berlin, Almanya'nın başkenti ve en büyük şehridir, aynı zamanda bir eyalettir. [1] |
| 16 | Türkiye'nin başkenti neresidir? | **correct** | wiki | **Ankara** — Ankara (/ˈaŋkaɾa/), Türkiye'nin başkenti ve Ankara ilinin merkezi olan şehirdir. [1] |
| 17 | Fransa'nın başkenti neresi? | **correct** | wiki | **Paris** — Paris, Fransa'nın başkenti ve 'den fazla alanda 2,175,601 (2018 itibarıyla tahmini nüfus) nüfusu ile en kalabalık şehridir. [1] |
| 18 | Japonya'nın başkenti neresidir? | **correct** | wiki | **Tokyo** — Tokyo (Tōkyō, "Doğunun Başkenti") veya resmî adıyla Tokyo Metropolü (東京都; Tōkyō-to), Japonya'nın başkenti ve prefektörlüklerinden biridir. [1] |
| 19 | İstanbul'un fethi hangi yılda oldu? | **correct** | wiki | İstanbul'un Fethi, Kostantiniyye'nin Fethi veya Konstantinopolis'in Düşüşü, 6 Nisan 1453 - 29 Mayıs 1453 tarihleri arasında, 53 gün süren yoğun bir kuşatmanın sonucunda O |
| 20 | Kurtuluş Savaşı ne zaman bitti? | **correct** | wiki | Türk Kurtuluş Savaşı, I. Dünya Savaşı'ndan yenik çıkan Osmanlı İmparatorluğu'nun İtilaf Devletleri'nce işgali sonucunda Mîsâk-ı Millî sınırları içinde ülke bütünlüğünü ko |
| 21 | Fotosentez nedir? | **correct** | wiki | Fotosentez, bitkiler ve diğer canlılar tarafından, ışık enerjisini organizmaların yaşamsal eylemlerine enerji sağlamak için daha sonra serbest bırakılabilecek kimyasal en |
| 22 | Python programlama dili nedir? | **correct** | wiki | Python, nesne yönelimli, yorumlamalı, birimsel (modüler) ve etkileşimli yüksek seviyeli bir programlama dilidir. [1] |
| 23 | Kuantum bilgisayar nedir? | **correct** | wiki | Kuantum bilgisayarı veri üzerinde işlem yapmak için bindirme ve dolaşma gibi kuantum-mekanik fenomenin doğrudan kullanımını sağlayan teorik hesaplama sistemlerini kullana |
| 24 | Dünyanın en uzun nehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Dünya veya Yerküre, Güneş Sistemi' |
| 25 | Su kaç derecede kaynar? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Su, Dünya üzerinde bol miktarda bu |
| 26 | Einstein hangi teoriyi geliştirdi? | **correct** | wiki | Tüm zamanların en iyi fizikçilerinden birisi olarak kabul edilen Albert Einstein, en çok görelilik teorisini geliştirmesiyle tanınır. [1] |
| 27 | Bitcoin fiyatı bugün kaç dolar? | **correct** | unsure | Bundan emin değilim. Bu soru **güncel** bir bilgi istiyor (fiyat, kur, hava, haber, skor gibi). Çevrimdışı bilgi dizinim güncel verileri içermiyor; internet bağlantısı va |
| 28 | Yusuf'un en sevdiği renk ne? | **correct** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Yusuf ( Yūsuf), Yosef veya Batıdak |
| 29 | Bana kısa bir şiir yaz | **correct** | lm |  |
| 30 | İtalya'nın başkenti neresidir? | **correct** | wiki | **Roma** — Gösterilerin kitlesel olarak yaşandığı Avrupa’da İtalya’nın başkenti Roma’da yapılan ve 3 milyon kişinin katıldığı gösteri tarihteki en büyük savaş karşıtı eyl |
| 31 | İspanya'nın başkenti neresi? | **correct** | wiki | **Madrid** — Madrid, İspanya'nın başkenti ve en kalabalık şehridir. [1] |
| 32 | Rusya'nın başkenti neresidir? | **correct** | wiki | **Moskova** — Moskova (Rusça: Москва / Moskva), Rusya'nın başkenti ve en kalabalık şehridir. [1] |
| 33 | Mısır'ın başkenti neresidir? | **correct** | wiki | **Kahire** — Kahire Mısır Müzesi ya da kısaca Mısır Müzesi, Mısır'ın başkenti Kahire'de bulunan ve Antik Mısır uygarlığının en görkemli koleksiyonunu barındıran arkeoloji |
| 34 | İngiltere'nin başkenti neresidir? | **correct** | wiki | **Londra** — Marylebone Cricket Club, günümüzde İngiltere'nin başkenti Londra'da bulunan bir kulüp olarak faaliyetlerine devam etmekte olup, sporun resmî bir yönetim kuru |
| 35 | Çin'in başkenti neresidir? | **correct** | wiki | **Pekin** — 1860 - II. Afyon Savaşı'nda İngiliz ve Fransız orduları Çin'in başkenti Pekin'e girdi. [1] |
| 36 | Azerbaycan'ın başkenti neresidir? | **correct** | wiki | **Bakü** — Azerbaycan adına yarışan Ell & Nikki'nin 2011 yarışmasını kazanmasının ardından Azerbaycan'ın başkenti Bakü'de düzenlendi. [1] |
| 37 | Avustralya'nın başkenti neresidir? | **correct** | wiki | **Canberra** — Canberra ya da Kanberra, Avustralya'nın başkenti ve denizden uzak en büyük, Avustralya'da tüm şehirler içinde de sekizinci büyük şehridir. [1] |
| 38 | Kanada'nın başkenti neresidir? | **correct** | wiki | **Ottawa** — Ottawa, Kanada'nın başkenti ve dördüncü büyük kentidir. [1] |
| 39 | Brezilya'nın başkenti neresidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Brezilya (Portekizce: Brasil) ya d |
| 40 | Türkiye'nin en kalabalık şehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 41 | Türkiye'nin para birimi nedir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 42 | Japonya'nın para birimi nedir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Japonya (, Nihon ya da Nippon, res |
| 43 | Sefiller romanını kim yazdı? | **correct** | wiki | Sefiller (Fransızca: Les Misérables; ), Victor Hugo tarafından yazılan tarihi romandır. [1] |
| 44 | İstiklal Marşı'nı kim yazdı? | **correct** | wiki | Güftesi, Anadolu'da Millî Mücadele'nin devam ettiği sırada Mehmet Âkif Ersoy tarafından kaleme alınmış şiirdir. [1] |
| 45 | Telefonu kim icat etti? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Telefon, birbirinden uzak yerlerde |
| 46 | Mona Lisa'yı kim yaptı? | **correct** | wiki | Mona Lisa (La Gioconda veya La Joconde olarak da bilinir), İtalya'nın Floransa şehrindeki Rönesans sırasında Leonardo da Vinci tarafından kavak bir pano üzerine Sfumato t |
| 47 | Fatih Sultan Mehmet kimdir? | **correct** | wiki | II. Mehmed veya bilinen adıyla Fatih Sultan Mehmed ya da kısaca Fatih (30 Mart 1432 – 3 Mayıs 1481), Osmanlı İmparatorluğu'nun 7. padişahıdır. [1] |
| 48 | Kanuni Sultan Süleyman kimdir? | **correct** | wiki | I. Süleyman ( Sultân Süleymân-ı Evvel, divan edebiyatındaki mahlasıyla Muhibbi; 6 Kasım 1494, Trabzon - 7 Eylül 1566, Zigetvar), Osmanlı İmparatorluğu'nun onuncu padişahı |
| 49 | Türkiye Cumhuriyeti ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 50 | Birinci Dünya Savaşı ne zaman başladı? | **correct** | wiki | I. Dünya Savaşı, 28 Temmuz 1914 tarihinde başlayıp 11 Kasım 1918 tarihinde sona eren Avrupa merkezli küresel bir savaştır. [1] |
| 51 | İkinci Dünya Savaşı ne zaman bitti? | **correct** | wiki | II. Dünya Savaşı, 1939'dan 1945'e kadar süren küresel savaş. [1] |
| 52 | Dünyanın en büyük kıtası hangisidir? | **correct** | wiki | **Asya** — Asya veya Asya Kıtası, Avrupa'nın doğusunda, Büyük Okyanus'un batısında, Okyanusya'nın kuzeyinde ve Arktik Okyanus'un güneyinde bulunan kıta, yüzölçümü olarak  |
| 53 | Dünyanın en büyük ülkesi hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Dünya veya Yerküre, Güneş Sistemi' |
| 54 | Güneş Sistemi'nin en büyük gezegeni hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Güneş Sistemi, Güneş'in kütleçekim |
| 55 | Mars nedir? | **correct** | wiki | Mars (eski Türkçede Bakır Sokım, Merih), Güneş Sistemi'nin Güneş'ten itibaren dördüncü gezegeni. [1] |
| 56 | DNA nedir? | **correct** | wiki | Deoksiriboz nükleik asit veya kısaca DNA, tüm organizmaların ve bazı virüslerin canlılık işlevleri ve biyolojik gelişmeleri için gerekli olan genetik talimatları taşıyan  |
| 57 | Van Gölü nerededir? | **correct** | wiki | Anadolu'nun en büyük kapalı havzası olan Van Gölü kıyısında toprakları verimli, akarsuları bol, iklim koşulları oldukça elverişli bir yerleşim merkezidir. [1] |
| 58 | Kapadokya nerededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Kapadokya, 60 milyon yıl önce Erci |
| 59 | Isaac Newton kimdir? | **correct** | wiki | Isaac Newton (d. 4 Ocak 1643, Woolsthorpe – ö. 31 Mart 1727, Kensington), İngiliz fizikçi, matematikçi, astronom, mucit, simyacı, teolog ve filozoftur. [1] |
| 60 | Marie Curie kimdir? | **correct** | wiki | Marie Skłodowska Curie (doğum Maria Salomea Skłodowska, 7 Kasım 1867 – 4 Temmuz 1934), radyoaktivite alanında öncü araştırmalar yapmış ve bu araştırmaları sonucunda Nobel |
| 61 | Orhan Pamuk kimdir? | **correct** | wiki | Orhan Ferit Pamuk (d. 7 Haziran 1952, İstanbul ), Türk romancı. Birçok başka edebiyat ödülünün yanı sıra, 2006 yılında Nobel Edebiyat Ödülü'ne layık görüldü ve 54 yaşında |
| 62 | Ankara ne zaman başkent oldu? | **correct** | wiki | Ankara'nın 13 Ekim 1923'te başkent ilan edilmesinin ardından şehir hızla gelişmiş ve Türkiye'nin ikinci en kalabalık ili olmuştur. [1] |
| 63 | Türkiye'nin yüzölçümü ne kadar? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 64 | Işık hızı nedir? | **correct** | wiki | Işık saydam maddelerin içinde boşluktaki hızından daha yavaş yayılır. [1] |
| 65 | Galatasaray ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 66 | Afyonkarahisar hangi bölgededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Afyonkarahisar veya eski ve halk a |
| 67 | Tenis nedir? | **correct** | wiki | Tenis, raket ve topla iki kişi arasında ya da ikişer kişilik iki takım arasında oynanan olimpik bir spor. [1] |
| 68 | Piyano nedir? | **correct** | wiki | Piyano, İtalya'da Bartolomeo Cristofori tarafından 1700 yılı civarında icat edilmiş (tam olarak yıl belirsizdir) akustik, tuşlu bir müzik aletidir. [1] |
| 69 | ESP32 nedir? | **correct** | wiki | ESP32; Bluetooth ve Wİ-Fİ özelliği olan, düşük maliyetli ve düşük güçlü bir mikrodenetleyici sistemdir. [1] |

## Kör küme — eval_blind.json (32 soru)
### Sunucu
| # | Soru | Sonuç | Tür | Cevap (kısaltılmış) |
|---|---|---|---|---|
| 1 | Yunanistan'ın başkenti neresidir? | **correct** | wiki | **Atina** — Atina (Yunanca: Αθήνα Athína, Grekçe: Ἀθῆναι Athênai), Yunanistan'ın başkenti ve yaklaşık 4 milyon kişilik nüfusuyla en büyük, Avrupa Birliği'nin yedinci büyü |
| 2 | Macaristan'ın başkenti neresidir? | **correct** | wiki | **Budapeşte** — Budapeşte, Macaristan'ın başkenti ve en kalabalık şehridir. [1] |
| 3 | Hindistan'ın başkenti neresidir? | **correct** | wiki | **Yeni Delhi** — Yeni Delhi, Hindistan'ın başkenti, 321.883 şehir içi nüfusu ile yerleşim alanı olarak nüfusu 17.753.087 kişidir (1 Ocak 2006 verilerine göre). [1] |
| 4 | İran'ın başkenti neresidir? | **correct** | wiki | **Tahran** — Başkenti Tahran'dır. [1] |
| 5 | Arjantin'in başkenti neresidir? | **correct** | wiki | **Buenos Aires** — Buenos Aires (İspanyolca telaffuzu: [ˈbwenos ˈajɾes]), resmî olarak Buenos Aires Özerk Şehri, Arjantin'in başkenti ve en büyük şehridir. [1] |
| 6 | Güney Kore'nin başkenti neresidir? | **correct** | wiki | **Seul** — Seul (, Seoul; başkent) veya resmî adıyla Özel Seul Şehri (, hanja: 서울特別市, Gözden Geçirilmiş Latinceleştirme: Seoul Teukbyeolsi), Güney Kore'nin başkenti ve en |
| 7 | Portekiz'in başkenti neresidir? | **correct** | wiki | **Lizbon** — Lizbon, Portekiz’in başkenti ve en büyük şehridir. [1] |
| 8 | Norveç'in başkenti neresidir? | **correct** | wiki | **Oslo** — Oslo (1624 - 1878 arasında Christiania, 1878 - 1924 arasında Kristiania), Norveç'in başkenti ve en büyük şehridir. [1] |
| 9 | Bursa'nın nüfusu kaç? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Bursa ( Prussa, ), Türkiye'de Burs |
| 10 | Mustafa Kemal Atatürk ne zaman öldü? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 11 | Cengiz Han kimdir? | **correct** | wiki | Cengiz Han (doğum adıyla Temuçin, – 18 Ağustos 1227), Moğol İmparatorluğu'nun kurucusu ve ilk Kağanı olan Moğol komutan ve hükümdardır. [1] |
| 12 | Leonardo da Vinci kimdir? | **correct** | wiki | Leonardo da Vinci, Rönesans dönemi İtalyan mimarı, mühendisi, mucidi, matematikçisi, anatomisti, müzisyeni, heykeltıraşı ve ressamıdır. [1] |
| 13 | Ludwig van Beethoven kimdir? | **correct** | wiki | Ludwig van Beethoven (vaftiz: 17 Aralık 1770, ölüm: 26 Mart 1827), Klasik dönemden Romantik döneme geçiş sürecine büyük katkı sağlamış ve gelmiş geçmiş en ünlü ve en etki |
| 14 | Fizik nedir? | **correct** | wiki | Fizik (, romanize: physikḗ (epistḗmē), lit. "doğa bilgisi"), maddeyi, maddenin uzay-zaman boyunca hareketini ve davranışını, ilgili enerji ve kuvvetlerin varlığını incele |
| 15 | Matematik nedir? | **correct** | wiki | Matematik (Yunanca μάθημα máthēma, "bilgi, çalışma, öğrenme"); sayılar, felsefe, uzay ve fizik gibi konularla ilgilenir. [1] |
| 16 | Yapay zeka nedir? | **correct** | wiki | Yapay zekâ (YZ,, AI), insanlar da dahil olmak üzere hayvanlar tarafından, doğal zekânın aksine makineler tarafından görüntülenen zekâ çeşididir. [1] |
| 17 | Linux nedir? | **correct** | wiki | Linux (telaffuz: Lin-uks); Linux çekirdeğine dayalı, açık kaynak kodlu, Unix benzeri bir işletim sistemi ailesidir. [1] |
| 18 | Kali Linux nedir? | **correct** | wiki | Kali; Linux tabanlı, CD'den başlatma seçenekli BackTrack yapımcıları tarafından 2013 yılında oluşturulmuş olan bir güvenlik kontrol işletim sistemi. [1] |
| 19 | Yüzme nedir? | **correct** | wiki | Yüzme, bir kişinin su veya başka bir sıvı üzerinde genellikle rekreasyon, spor, egzersiz veya hayatta kalmak için hareket etmesidir. [1] |
| 20 | Osmanlı İmparatorluğu ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Osmanlı İmparatorluğu, Osmanlı Dev |
| 21 | Bizans İmparatorluğu ne zaman yıkıldı? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Bizans İmparatorluğu veya Doğu Rom |
| 22 | Fransız Devrimi ne zaman başladı? | **correct** | wiki | Fransız Devrimi veya Fransız İhtilâli (1789-1799), Fransa'daki mutlak monarşinin devrilip yerine cumhuriyetin kurulması ve Katolik Kilisesi'nin ciddi reformlara gitmeye z |
| 23 | Ağrı Dağı'nın yüksekliği kaç metre? | **correct** | wiki | Ağrı Dağı 5137 m'lik yüksekliği ile sadece ülkenin en yüksek zirvesi olmayıp aynı zamanda üzerinde 10 km²lik güncel bir buz takkesi (ice cap) bulunduran tek dağıdır. [1] |
| 24 | Tuz Gölü nerededir? | **correct** | wiki | Tuz Gölü, Türkiye'nin İç Anadolu Bölgesi'nde Ankara, Konya ve Aksaray illerinin sınırının kesiştiği yerde yer alan tuz gölüdür. [1] |
| 25 | Efes Antik Kenti nerededir? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 26 | Romeo ve Juliet'i kim yazdı? | **correct** | wiki | Romeo ve Juliet (İngilizce özgün adı: The Most Excellent and Lamentable Tragedy of Romeo and Juliet), İngiliz oyun yazarı William Shakespeare tarafından yazılmış bir oyun |
| 27 | Suç ve Ceza romanını kim yazdı? | **correct** | wiki | Suç ve Ceza (Rus Reformu öncesi; Rus Reformu sonrası ), Rus yazar Fyodor Dostoyevski tarafından yazılan psikolojik ve dram türündeki romandır. [1] |
| 28 | Dünyanın en yüksek dağı hangisidir? | **correct** | wiki | **Everest Dağı** — Everest Dağı (Tibetçe: ཇོ་མོ་གླང་མ, Çomolungma; Nepalce: सगरमाथा, Sagarmāthā), dünyanın deniz seviyesi üzerindeki en yüksek dağı. [1] |
| 29 | Avrupa'nın en uzun nehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Avrupa, kuzeyde Arktik Okyanusu, b |
| 30 | Türkiye'nin en büyük gölü hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 31 | Euro nedir? | **unsure** | unsure | Bundan emin değilim. Bu soru **güncel** bir bilgi istiyor (fiyat, kur, hava, haber, skor gibi). Kendi Vikipedi dizinim güncel verileri içermiyor; uygulamada **Web'de doğr |
| 32 | Afyon Kocatepe Üniversitesi nerededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Afyon Kocatepe Üniversitesi (AKÜ), |
### Çevrimdışı
| # | Soru | Sonuç | Tür | Cevap (kısaltılmış) |
|---|---|---|---|---|
| 1 | Yunanistan'ın başkenti neresidir? | **correct** | wiki | **Atina** — Atina (Yunanca: Αθήνα Athína, Grekçe: Ἀθῆναι Athênai), Yunanistan'ın başkenti ve yaklaşık 4 milyon kişilik nüfusuyla en büyük, Avrupa Birliği'nin yedinci büyü |
| 2 | Macaristan'ın başkenti neresidir? | **correct** | wiki | **Budapeşte** — Budapeşte, Macaristan'ın başkenti ve en kalabalık şehridir. [1] |
| 3 | Hindistan'ın başkenti neresidir? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 4 | İran'ın başkenti neresidir? | **correct** | wiki | **Tahran** — Başkenti Tahran'dır. [1] |
| 5 | Arjantin'in başkenti neresidir? | **correct** | wiki | **Buenos Aires** — Buenos Aires (İspanyolca telaffuzu: [ˈbwenos ˈajɾes]), resmî olarak Buenos Aires Özerk Şehri, Arjantin'in başkenti ve en büyük şehridir. [1] |
| 6 | Güney Kore'nin başkenti neresidir? | **correct** | wiki | **Seul** — Seul (, Seoul; başkent) veya resmî adıyla Özel Seul Şehri (, hanja: 서울特別市, Gözden Geçirilmiş Latinceleştirme: Seoul Teukbyeolsi), Güney Kore'nin başkenti ve en |
| 7 | Portekiz'in başkenti neresidir? | **correct** | wiki | **Lizbon** — Lizbon, Portekiz’in başkenti ve en büyük şehridir. [1] |
| 8 | Norveç'in başkenti neresidir? | **correct** | wiki | **Oslo** — Oslo (1624 - 1878 arasında Christiania, 1878 - 1924 arasında Kristiania), Norveç'in başkenti ve en büyük şehridir. [1] |
| 9 | Bursa'nın nüfusu kaç? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Bursa ( Prussa, ), Türkiye'de Burs |
| 10 | Mustafa Kemal Atatürk ne zaman öldü? | **correct** | wiki | Mustafa Kemal Atatürk (1881, Selanik, Osmanlı İmparatorluğu - 10 Kasım 1938, İstanbul, Türkiye), Türk asker ve devlet adamı. [1] |
| 11 | Cengiz Han kimdir? | **correct** | wiki | Cengiz Han (doğum adıyla Temuçin, – 18 Ağustos 1227), Moğol İmparatorluğu'nun kurucusu ve ilk Kağanı olan Moğol komutan ve hükümdardır. [1] |
| 12 | Leonardo da Vinci kimdir? | **correct** | wiki | Leonardo di ser Piero da Vinci (15 Nisan 1452 - 2 Mayıs 1519), Rönesans döneminde yaşamış İtalyan hezârfen, döneminin önemli bir filozofu, astronomu, mimarı, mühendisi, m |
| 13 | Ludwig van Beethoven kimdir? | **correct** | wiki | Ludwig van Beethoven (vaftiz: 17 Aralık 1770, ölüm: 26 Mart 1827), Klasik dönemden Romantik döneme geçiş sürecine büyük katkı sağlamış ve gelmiş geçmiş en ünlü ve en etki |
| 14 | Fizik nedir? | **correct** | wiki | Fizik (, romanize: physikḗ (epistḗmē), lit. "doğa bilgisi"), maddeyi, maddenin uzay-zaman boyunca hareketini ve davranışını, ilgili enerji ve kuvvetlerin varlığını incele |
| 15 | Matematik nedir? | **correct** | wiki | Matematik (Yunanca μάθημα máthēma, "bilgi, çalışma, öğrenme"); sayılar, felsefe, uzay ve fizik gibi konularla ilgilenir. [1] |
| 16 | Yapay zeka nedir? | **correct** | wiki | Yapay zekâ (YZ,, AI), insanlar da dahil olmak üzere hayvanlar tarafından, doğal zekânın aksine makineler tarafından görüntülenen zekâ çeşididir. [1] |
| 17 | Linux nedir? | **correct** | wiki | Linux (telaffuz: Lin-uks); Linux çekirdeğine dayalı, açık kaynak kodlu, Unix benzeri bir işletim sistemi ailesidir. [1] |
| 18 | Kali Linux nedir? | **correct** | wiki | Kali; Linux tabanlı, CD'den başlatma seçenekli BackTrack yapımcıları tarafından 2013 yılında oluşturulmuş olan bir güvenlik kontrol işletim sistemi. [1] |
| 19 | Yüzme nedir? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 20 | Osmanlı İmparatorluğu ne zaman kuruldu? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Osmanlı İmparatorluğu, Osmanlı Dev |
| 21 | Bizans İmparatorluğu ne zaman yıkıldı? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Bizans İmparatorluğu veya Doğu Rom |
| 22 | Fransız Devrimi ne zaman başladı? | **correct** | wiki | Fransız Devrimi veya Fransız İhtilâli (1789-1799), Fransa'daki mutlak monarşinin devrilip yerine cumhuriyetin kurulması ve Katolik Kilisesi'nin ciddi reformlara gitmeye z |
| 23 | Ağrı Dağı'nın yüksekliği kaç metre? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Ağrı Dağı (Selçuklular döneminde:  |
| 24 | Tuz Gölü nerededir? | **correct** | wiki | Tuz Gölü, Türkiye'nin İç Anadolu Bölgesi'nde Ankara, Konya ve Aksaray illerinin sınırının kesiştiği yerde yer alan tuz gölüdür. [1] |
| 25 | Efes Antik Kenti nerededir? | **unsure** | unsure | Bundan emin değilim. Bu konuda güvenilir bir kaynak bulamadım, bu yüzden tahmin yürütmek istemiyorum. Soruyu biraz farklı ya da daha ayrıntılı sorabilir misin? |
| 26 | Romeo ve Juliet'i kim yazdı? | **correct** | wiki | Romeo ve Juliet (İngilizce özgün adı: The Most Excellent and Lamentable Tragedy of Romeo and Juliet), İngiliz oyun yazarı William Shakespeare tarafından yazılmış bir oyun |
| 27 | Suç ve Ceza romanını kim yazdı? | **correct** | wiki | Suç ve Ceza (Rus Reformu öncesi; Rus Reformu sonrası ), Rus yazar Fyodor Dostoyevski tarafından yazılan psikolojik ve dram türündeki romandır. [1] |
| 28 | Dünyanın en yüksek dağı hangisidir? | **correct** | wiki | **Everest Dağı** — Everest Dağı (Tibetçe: ཇོ་མོ་གླང་མ, Çomolungma; Nepalce: सगरमाथा, Sagarmāthā), dünyanın deniz seviyesi üzerindeki en yüksek dağı. [1] |
| 29 | Avrupa'nın en uzun nehri hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Avrupa, kuzeyde Arktik Okyanusu, b |
| 30 | Türkiye'nin en büyük gölü hangisidir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Türkiye veya resmî adıyla Türkiye  |
| 31 | Euro nedir? | **unsure** | unsure | Bundan emin değilim. Bu soru **güncel** bir bilgi istiyor (fiyat, kur, hava, haber, skor gibi). Çevrimdışı bilgi dizinim güncel verileri içermiyor; internet bağlantısı va |
| 32 | Afyon Kocatepe Üniversitesi nerededir? | **unsure** | unsure | Bundan emin değilim. Sorunun tam cevabını kaynaklarımda doğrulayamadım. Konuyla ilgili bulduğum bilgi şu (cevap olarak doğrulanmadı): > Afyon Kocatepe Üniversitesi (AKÜ), |
