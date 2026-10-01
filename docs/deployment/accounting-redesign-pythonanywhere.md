# رفع تحديث النظام المحاسبي إلى PythonAnywhere

هذه الخطوات آمنة للبيانات الحالية. لا تستخدم `flush`، ولا تحذف ملف `db.sqlite3`.

## 1. افتح Bash في PythonAnywhere

نفذ الأوامر التالية بالترتيب:

```bash
cd /home/7Mohamed/alshahabi_honey
workon alshahabi_honey_env
cp db.sqlite3 db.sqlite3.backup_before_accounting_redesign
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry -e sessions.Session --indent 2 -o data_backup_before_accounting_redesign.json
git pull origin master
python manage.py migrate
python manage.py collectstatic --no-input
```

## 2. أعد تشغيل الموقع

من تبويب **Web** في PythonAnywhere اضغط **Reload**.

## 3. لو ظهر خطأ

توقف فورًا ولا تنفذ أوامر إضافية. انسخ رسالة الخطأ كاملة وأرسلها لي.

## ممنوع

- لا تشغل `python manage.py flush`.
- لا تحذف `db.sqlite3`.
- لا تستبدل قاعدة البيانات بدون نسخة احتياطية.
