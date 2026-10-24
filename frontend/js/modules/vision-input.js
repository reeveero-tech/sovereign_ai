/* ============================================================
   Sovereign AI — vision-input.js
   R-741 (البند ٢.٢ — الجولة الموثقة «اللاحقة»): رفع الصور في
   الواجهة — زر btn-vision-upload + مدخل vision-file-input + وصف
   عبر POST /vision يسلَّم في مسار المحادثة الحقيقي.
   ============================================================ */

class SovereignVisionInput {

    constructor() {

        /* أنواع الصور المسموحة — نفس قائمة الخادم (app.py) حرفيًا */
        this.allowedTypes = [
            'image/png',
            'image/jpeg',
            'image/webp',
            'image/gif',
            'image/bmp'
        ];

        /* حد الحجم — نفس حد الخادم (10MiB افتراضيًا) */
        this.maxBytes = 10 * 1024 * 1024;

        this.uploading = false;

        console.log(
            '👁 Vision Input Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindUpload();
    }

    /* ========================================================
       UPLOAD — زر الرفع → مدخل الملف → POST /vision
    ======================================================== */

    bindUpload() {

        const button =
            document.getElementById(
                'btn-vision-upload'
            );

        const input =
            document.getElementById(
                'vision-file-input'
            );

        if (!button || !input) return;

        button.addEventListener(
            'click',
            () => input.click()
        );

        input.addEventListener(
            'change',
            () => this.handleFile(input)
        );
    }

    async handleFile(input) {

        const file = input.files?.[0];

        /* إعادة الضبط دائمًا — لا يعلق اختيار سابق */
        input.value = '';

        if (!file || this.uploading) return;

        /* فحص محلي صادق قبل أي طلب — نفس عقد الخادم */
        if (!this.allowedTypes.includes(file.type)) {
            window.SOVEREIGN_NOTIFY
                ?.warning(
                    'نوع الملف غير مسموح — الصور فقط '
                    + `(وصل: ${file.type || 'غير معروف'})`
                );
            return;
        }

        if (file.size > this.maxBytes) {
            window.SOVEREIGN_NOTIFY
                ?.warning(
                    'الصورة أكبر من الحد (10MiB) — راجع الحجم'
                );
            return;
        }

        this.uploading = true;

        try {

            const body = new FormData();
            body.append('file', file);

            const response =
                await fetch('/vision', {
                    method: 'POST',
                    body: body
                });

            if (response.status === 503) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'الرؤية معطلة على الخادم '
                        + '(VISION_ENABLED + VISION_MODEL) — '
                        + 'فعّلها من الأسرار'
                    );
                return;
            }

            if (response.status === 502) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'خدمة الرؤية لم تُرجع وصفًا '
                        + '(نموذج غير متاح) — لا وصف مختلق'
                    );
                return;
            }

            if (response.status === 413) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'الصورة أكبر من حد الخادم (10MiB)'
                    );
                return;
            }

            if (response.status === 415) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'الخادم رفض نوع الصورة (415)'
                    );
                return;
            }

            if (response.status === 429) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'تجاوزت حد طلبات الرؤية — أعد المحاولة لاحقًا'
                    );
                return;
            }

            if (!response.ok) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'تعذر تحليل الصورة '
                        + `(${response.status})`
                    );
                return;
            }

            const data = await response.json();

            if (!data?.description) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'استجابة الرؤية بلا وصف — لا وصف مختلق'
                    );
                return;
            }

            /* التسليم عبر مسار المحادثة الحقيقي — لا كتابة DOM
               مجهولة (المادة ١: لا انتحال) */
            window.SOVEREIGN_CHAT_RUNTIME
                ?.receiveVisionDescription(
                    data.description,
                    file.name
                );

        } catch (error) {

            console.error(
                'Vision Input Failed',
                error
            );

            window.SOVEREIGN_NOTIFY
                ?.error(
                    'فشل رفع الصورة (شبكة/خادم)'
                );

        } finally {

            this.uploading = false;
        }
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_VISION_INPUT =
    new SovereignVisionInput();
