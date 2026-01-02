# Darsi Bot - نظام إدارة الشعب الدراسية

نظام إدارة الشعب الدراسية عبر Telegram Bot مبني باستخدام Python و Aiogram.

## المميزات

- إدارة الشعب الدراسية
- تسجيل الطلاب
- متابعة التقارير والامتحانات
- نظام التذكيرات الذكية
- إدارة المقررات الدراسية
- نظام الصلاحيات المتقدم

## المتطلبات

- Python 3.8+
- Telegram Bot Token

## التثبيت

1. استنسخ المستودع:
```bash
git clone <repository-url>
cd darsi-bot0
```

2. ثبت المتطلبات:
```bash
pip install -r requirements.txt
```

3. قم بإنشاء ملف `config.json` من `config.json.example` واملأ البيانات المطلوبة:
```bash
cp config.json.example config.json
```

4. عدّل `config.json` وأضف:
   - `bot_token`: رمز البوت من BotFather
   - `superadmin_id`: معرف المشرف الرئيسي
   - البيانات الأخرى المطلوبة

5. شغّل البوت:
```bash
python main.py
```

## البنية

```
darsi-bot0/
├── main.py              # نقطة البداية
├── config.json          # ملف الإعدادات (غير متضمن في Git)
├── config.json.example  # قالب ملف الإعدادات
├── requirements.txt     # المتطلبات
├── database/            # إدارة قاعدة البيانات
├── handlers/            # معالجات الأوامر
├── keyboards/           # لوحات المفاتيح
├── middlewares/         # الوسطاء
├── states/              # حالات FSM
└── utils/               # الأدوات المساعدة
```

## الترخيص

انظر ملف LICENSE

