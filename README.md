# مولّد فيديوهات القرآن

ينشئ المشروع فيديوهات السور بأسلوبه البصري الأصلي: زخرفة SVG متحركة بهدوء، خلفية فاتحة، خط Amiri، واسم القناة. كما يدعم الآن إنشاء مقطع عمودي قصير يحافظ على التلاوة والنص والتوقيت الأصلي للآيات.

## المتطلبات على Kali Linux

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg fontconfig fonts-hosny-amiri
```

يلزم وجود `resvg` لأجل تحويل زخرفة SVG. نزّل إصدار Linux x86_64 من صفحة [إصدارات resvg](https://github.com/linebender/resvg/releases)، وفكّه، ثم ضع الملف التنفيذي `resvg` في مجلد موجود ضمن `PATH` واجعله قابلًا للتنفيذ (`chmod +x resvg`). إذا كان في مكان آخر، مرّر مساره عبر `RESVG_BIN=/المسار/إلى/resvg`.

ثبّت مكتبات Python داخل بيئة افتراضية:

```bash
git clone https://github.com/drobzila/Long_videos_Quran.git
cd Long_videos_Quran
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## إنشاء فيديو قصير

```bash
python quran_final.py --surah 108 --reciter ar.minshawi --svg assets/Tile-Derivative-9.svg --format shorts --out short.mp4
```

يختار البرنامج عشوائيًا مقطعًا متصلًا من آيات السورة تكون مدته بين 4 و20 ثانية، ويفضّل مدة قريبة من 12 ثانية. الاختيار يقع عند حدود الآيات؛ لا تُقصّ التلاوة داخل الآية. يبقى النص المعروض مطابقًا للآيات المختارة، وتظهر صورة نهاية لمدة صفر افتراضيًا كي تبقى المدة قريبة من الشورت المرجعي.

لضبط المدة أو تكرار اختيار المقطع:

```bash
python quran_final.py --surah 108 --format shorts --min-duration 6 --max-duration 18 --seed 42 --out short.mp4
```

يمكن إضافة `--end-image path/to/image.png --end-duration 3` لبطاقة نهاية مدتها 3 ثوانٍ. المقاس في هذا الوضع 1080×1920. ويظل الوضع الأصلي الأفقي متاحًا كما كان:

```bash
python quran_final.py --surah 108 --reciter ar.minshawi --svg assets/Tile-Derivative-9.svg --out surah.mp4
```

### خيارات مهمة

- `--surah`: رقم السورة من 1 إلى 114.
- `--reciter`: معرّف القارئ في AlQuran Cloud؛ الافتراضي `ar.husary`.
- `--format`: `landscape` للفيديو الكامل أو `shorts` للمقطع العمودي.
- `--min-duration` و`--max-duration`: حدود مدة المقطع القصير بالثواني.
- `--seed`: قيمة اختيار اختيارية لإعادة إنتاج المقطع نفسه.
- `--gpu`: `none` أو `nvidia` أو `qsv` حسب ترميز FFmpeg المتاح.

يلزم اتصال بالإنترنت لجلب صوت الآيات. تُحفظ الملفات الصوتية مؤقتًا داخل `audio_temp`. لا يرفع البرنامج الفيديو تلقائيًا إلى أي خدمة.
