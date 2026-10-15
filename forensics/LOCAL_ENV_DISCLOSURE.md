# forensics/LOCAL_ENV_DISCLOSURE.md — إفصاح البيئة المحلية للوكيل

**التاريخ:** 2026-10-16 — جولة R-682 الشاملة (البند ١٠)

## التصريح الحاكم

**النجاح المحلي للوكيل ليس على البيئة المُعلنة للمشروع.** كل تشغيلات الوكيل
المحلية (410/412 اختبارًا ناجحًا، القياسات، الاختبارات السلوكية) جرت على
Python 3.14.3 بحزم أحدث من المثبتة — بينما البيئة المُعلنة في CI هي
**Python 3.11.x + requirements.txt حرفيًا**. الدليل القاطع على المطابقة
المعلنة يبقى تشغيلات CI على الالتزام نفسه (انظر PY311_VERIFICATION.md).

## إصدار Python المحلي

```
Python 3.14.3 (main, Mar 10 2026, 18:18:50) [Clang 21.1.4]
```

## مقارنة صفًّا بصف مع requirements.txt (المعلن)

| الحزمة | requirements.txt (المعلن) | المحلي الفعلي | تطابق؟ |
|---|---|---|---|
| fastapi | 0.115.0 | 0.143.1 | ❌ أحدث |
| uvicorn | 0.30.0 (standard) | 0.54.0 | ❌ أحدث |
| websockets | 13.0 | (غير مثبتة كحزمة مستقلة) | ❌ |
| pydantic | 2.9.0 | 2.12.5 | ❌ أحدث |
| python-multipart | 0.0.12 | (غير مثبتة) | ❌ |
| httpx | 0.27.0 | httpx2 2.13.1 (بديل) | ❌ |
| numpy | 1.26.4 | (غير مثبتة محليًا) | ❌ |
| scikit-learn | 1.3.0 | (غير مثبتة محليًا) | ❌ |
| scipy | 1.13.0 | (غير مثبتة محليًا) | ❌ |
| pycryptodome | 3.24.1 | 3.24.1 | ✅ |
| pytest | 9.1.1 | 9.1.1 | ✅ |

ملاحظة: غياب numpy/scikit-learn/scipy محليًا لم يمنع الاختبارات لأن الوحدات
المستخدمة في الحزمة لا تستوردها في مسارات الاختبار (أو تستوردها بكفالة).

## قائمة pip freeze المحلية الكاملة (الفعلية)

```
Flask==3.1.3
Jinja2==3.1.6
MarkupSafe==3.0.4
PyGObject==3.48.2
PyYAML==6.0.3
Pygments==2.21.0
Werkzeug==3.1.9
aiohappyeyeballs==2.7.1
aiohttp==3.14.5
aiosignal==1.4.0
annotated-doc==0.0.5
annotated-types==0.8.0
anthropic==1.14.0
anyio==4.15.1
attrs==26.1.0
beautifulsoup4==4.15.0
blinker==1.9.0
boto3==1.43.114
botocore==1.43.114
bytecode==0.19.1
cbor2==6.1.5
certifi==2026.7.22
cffi==2.1.1
charset-normalizer==3.5.2
click==8.5.0
colorlog==6.12.0
contourpy==1.4.0
cryptography==50.0.2
cycler==0.12.1
datadog==0.51.0
ddtrace-internal==0.1.0
ddtrace==4.15.6
defusedxml==0.7.1
docstring_parser==0.18.0
envier==0.6.1
et_xmlfile==2.0.0
fast-langdetect==1.0.1
fastapi==0.143.1
fasttext-predict==0.9.2.4
fire==0.7.1
flatbuffers==25.12.19
fonttools==4.67.0
fpdf2==2.8.9
frozenlist==1.8.0
git-remote-s3==0.4.2
grpcio==1.80.0
grpclib==0.4.9
h11==0.16.0
h2==4.4.1
hanzidentifier==1.3.0
hpack==4.2.0
httpcore2==2.13.1
httptools==0.9.0
httpx2==2.13.1
hyperframe==6.1.0
idl-protobuf-perplexity-llm-api-common-llm-api-common-pyproto==2026.10.15.1792023210+9d31e6b
idl-protobuf-perplexity-llm-api-llm-api-pygrpc @ file:///tmp/asi-template-build/local-wheels/idl-protobuf-perplexity-llm-api-llm-api-pygrpc/idl_protobuf_perplexity_llm_api_llm_api_pygrpc-0.0.0%2Blocal-py3-none-any.whl#sha256=3c52f9a92106543572c496a85feb2ba7df33f3e891898409083dd01c6a77e3d8
idl-protobuf-perplexity-llm-api-llm-api-pyproto @ file:///tmp/asi-template-build/local-wheels/idl-protobuf-perplexity-llm-api-llm-api-pyproto/idl_protobuf_perplexity_llm_api_llm_api_pyproto-0.0.0%2Blocal-py3-none-any.whl#sha256=26fdbb219a808acdab0e8dd067549904302134035d8e0ab4763cddb630303731
idna==3.20
iniconfig==2.3.1
itsdangerous==2.2.0
jiter==0.13.0
jmespath==1.1.0
kiwisolver==1.5.1
lxml==6.1.3
lz4==4.4.5
magika==0.6.3
markdown-it-py==4.2.0
markdownify==1.2.3
markitdown==0.1.8
mat2==0.15.0
matplotlib==3.11.2
mdurl==0.1.2
modal==1.5.2
multidict==7.1.0
mutagen==1.48.1
numpy==2.5.4
onnxruntime==1.31.0
openai==3.31.0
opencv-python-headless==5.0.0.93
openpyxl==3.1.5
opentelemetry-api==1.45.1
orjson==3.11.8
packaging==26.3
pandas==3.0.6
pdf2docx==0.5.13
pdf2image==1.17.0
pdfminer.six==20260107
pdfplumber==0.11.10
pillow==12.3.0
pillow_heif==1.8.0
pluggy==1.7.0
pplx-python-sdks-llm-api @ file:///tmp/asi-template-build/local-wheels/pplx-python-sdks-llm-api/pplx_python_sdks_llm_api-0.0.0%2Blocal-py3-none-any.whl#sha256=aed3ccfa8c24b913c4138e20716d8eb7606138eb1b84ed4263f2101fa03b5201
pplx_sdk @ file:///tmp/asi-template-build/local-wheels/pplx-sdk/pplx_sdk-0.0.0%2Blocal-cp312-abi3-manylinux2014_x86_64.whl#sha256=9a1a3f068c8d3344b247930812be5018147f2d07360c596872678c0baaa358b4
propcache==0.5.4
protobuf==7.35.1
pycairo==1.29.2
pycparser==3.11
pycryptodome==3.24.1
pydantic==2.12.5
pydantic_core==2.41.5
pymupdf==1.28.2
pyparsing==3.3.3
pypdf==6.20.1
pypdfium2==5.14.0
pytesseract==0.3.13
pytest==9.1.1
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.4
python-pptx==1.0.2
pytz==2026.5
pyvips==3.2.0
reportlab==5.0.1
requests==2.34.2
rich==15.0.0
robust-downloader==0.0.2
s3transfer==0.19.2
scipy==1.18.1
six==1.17.0
skills-ref==0.1.1
sniffio==1.3.1
soupsieve==3.0.3
sqlglot==30.23.0
starlette==1.8.0
strictyaml==1.7.3
synchronicity==0.12.6
tenacity==9.1.2
termcolor==3.3.0
toml==0.10.2
tqdm==4.70.1
truststore==0.10.5
types-certifi==2021.10.8.3
types-toml==0.10.8.20260518
typing-inspection==0.4.4
typing_extensions==4.16.0
urllib3==2.8.0
uuid7==0.1.0
uvicorn==0.54.0
uvloop==0.23.0
watchfiles==1.3.0
websockets==17.2
wrapt==2.5.1
xlrd==2.0.2
xlsxwriter==3.2.9
yarl==1.25.1
yt-dlp==2026.8.19
zhon==2.1.1
```

## كيف يعيد المالك إنتاج النتائج على Python 3.11 حرفيًا

الطريق المضمون الموثق (لا يتطلب Docker محليًا):

1. **عبر GitHub Actions (المسار المعتمد في هذه الجولة):** أي دفعة إلى main
   تشغّل CI على Python 3.11.x مع تثبيت requirements.txt حرفيًا. تشغيل
   الاختبارات التشغيلية يتم بـ:
   `gh workflow run ci.yml --repo reeveero-tech/sovereign_ai --ref main -f run_operational=true`
2. **محليًا ببيئة نظيفة:**
   ```bash
   python3.11 -m venv venv311 && source venv311/bin/activate
   pip install -r requirements.txt
   python -m pytest tests/ backend/tests/ -m "not operational"
   bash verify.sh --full   # يتطلب بوابة الإصدار الجديدة: 3.11.x
   ```
   (بوابة الإصدار المضافة في هذه الجولة ترفض أي Python غير 3.11.x —
   راجع البند ١٢.)
3. **بصندوق Docker (إن توفر):** `docker run -it python:3.11-slim bash` ثم
   الخطوات نفسها — لم تكن متاحة للوكيل (لا Docker في بيئة الوكيل).

## حدود هذا الإفصاح

- الوكيل لا يستطيع قراءة أسرار GitHub (KEY_SECRET) — التشغيل التشغيلي
  تم عبر Actions بتفويض المالك للجهاز.
- كل الأرقام المحلية في هذه الجولة موثقة بخام مخرجاتها في ملفات forensics.
