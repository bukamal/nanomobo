# NanoMobo

أداة صيانة وتفليش أجهزة Android عبر USB Host، مبنية بـ Python و Flet — واجهة عربية،
مصممة بمبدأ **القراءة فقط** في هذه المرحلة: لا كتابة، لا فلاش، ولا تعديل معرفات
حيث يتم توثيق البروتوكولات والتحقق منها أولًا.

## المزايا الحالية

- **اكتشاف أجهزة USB** عبر Android USB Host (pyjnius) مع تصنيف وضع الجهاز:
  Qualcomm EDL 9008، MediaTek USB، Fastboot (Samsung/Google)، ADB، CDC،
  Mass Storage، Vendor Protocol.
- **طلب صلاحية USB** مع انتظار موافقة Android ومهلة زمنية.
- **فحص البروتوكول** من الـ descriptors فقط (قراءة فقط) مع حالة
  معروف/تجريبي/غير موثق.
- **تحليل ذكي للجهاز**: نسبة ثقة ومستوى (عالي/متوسط/منخفض) مع أسباب التصنيف
  وتوصيات آمنة، وبصمة SHA-256 ثابتة لكل جهاز.
- **مساعد الإصلاح**: اختر العَرَض (لا يشغل، معلق على الشعار، USB غير مكتشف،
  IMEI غير صالح، بطارية/حساسات) فيُبنى تقرير خطة قراءة فقط بمستوى مخاطر
  وخطوات مصنفة (تحقق/آمن/حذر) وتحذيرات، مع تقرير نصي كامل قابل للنسخ.
- **تشخيص الهوية**: تحقق من صيغة IMEI (Luhn) و MEID ومقارنة نسختين — قراءة
  ومقارنة فقط.
- **وضع فاتح/داكن/تلقائي** حسب النظام مع جدولة ليلية اختيارية، ونظام تصميم
  موحد (tokens) في `core/theme.py`.
- **إشعارات toast** مدمجة في الواجهة لمسارات التغذية الراجعة.

## بنية المشروع

```
src/
  main.py                     نقطة الدخول (Flet app)
  nanomobo/
    core/
      usb_bridge.py           جسر pyjnius إلى android.hardware.usb (جلسات، bulk/control)
      device_db.py            قاعدة أوضاع الأجهزة والـ VID/PID
      device_service.py       (services) خدمة الأجهزة بمستوى أعلى
      protocol_service.py     (services) تشغيل فحص البروتوكول
      capabilities.py         مصفوفة القدرات لكل وضع (جاهز/تجريبي/محجوب)
      device_intelligence.py  محرك التحليل والثقة
      repair_assistant.py     توليد خطط الإصلاح (قراءة فقط)
      identity.py             التحقق من IMEI/MEID
      theme.py / theme_settings.py / settings_store.py  نظام التصميم والإعدادات
      toast.py                إشعارات
    protocols/                بروب ProtocolProbe + descriptor probe
    views/home_view.py        الواجهة الرئيسية
tests/  unit/ integration/ contract/
```

## التشغيل

```bash
# تثبيت التبعيات
python -m pip install -e ".[dev]"

# تشغيل الاختبارات وفحوصات الجودة
python -m pytest
python -m ruff check . && python -m ruff format --check .
python -m mypy src tests

# تشغيل التطبيق على الحاسوب (اكتشاف USB معطل خارج Android)
flet run
```

## بناء APK لأندرويد

```bash
flet build apk --split-per-abi
```

يُعلن التطبيق عن ميزة `android.hardware.usb.host` كإلزامية، ومع `pyjnius`
كنهيدج JNI للوصول إلى `android.hardware.usb.*`. راجع
`[tool.flet]` في `pyproject.toml` وعقد التغليف في
`tests/contract/test_packaging_contract.py`.

## ضمانات الأمان

- جميع العمليات **قراءة فقط** افتراضيًا؛ كتابة EFS/IMEI/الفلاش محجوبة في
  `capabilities.py` ولا يوجد مسار كود يرسل أوامر كتابة.
- لا يتم إرسال أي أمر إلى الجهاز قبل توثيق بروتوكوله؛ فحص البروتوكول يقرأ
  descriptors الـ USB فقط.
- حالة التطبيق (`allowBackup=false`) لا تُنسخ احتياطيًا عبر النظام.

## CI

- `quality.yml`: ruff + mypy (strict) + pytest مع تغطية على Python 3.10–3.14.
- `android.yml`: بناء APK عند الوسوم `v*` أو تشغيل يدوي.
