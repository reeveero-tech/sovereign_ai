/* ============================================================
   Sovereign AI — runtime-security.js
   الإصدار: 7.0.0
   طبقة الحماية السيادية
   ============================================================ */

class SovereignRuntimeSecurity {

    constructor() {

        this.blockedPatterns = [

            '<script',

            'javascript:',

            'onerror=',

            'onload=',

            '<iframe'
        ];

        console.log(
            '🛡 Runtime Security Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.protectRuntime();

        this.bindGuards();
    }

    /* ========================================================
       RUNTIME PROTECTION
    ======================================================== */

    protectRuntime() {

        window.addEventListener(
            'error',
            (event) => {

                this.logThreat(
                    'runtime-error',
                    event.message
                );
            }
        );

        window.addEventListener(
            'unhandledrejection',
            (event) => {

                this.logThreat(
                    'promise-rejection',
                    event.reason
                );
            }
        );
    }

    /* ========================================================
       INPUT VALIDATION
    ======================================================== */

    validateInput(input) {

        if (
            !input ||
            typeof input !== 'string'
        ) {

            return false;
        }

        const lower =
            input.toLowerCase();

        const blocked =
            this.blockedPatterns.some(
                pattern =>
                    lower.includes(pattern)
            );

        if (blocked) {

            this.logThreat(
                'blocked-pattern',
                input
            );

            window.SOVEREIGN_NOTIFY
                ?.warning(
                    'Unsafe Runtime Input Blocked'
                );

            return false;
        }

        return true;
    }

    /* ========================================================
       SANITIZE
    ======================================================== */

    sanitize(input) {

        if (
            typeof input !== 'string'
        ) {

            return '';
        }

        return input
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .trim();
    }

    /* ========================================================
       EVENT GUARDS
    ======================================================== */

    bindGuards() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'chat:user_message',
            ({ text }) => {

                if (
                    !this.validateInput(text)
                ) {

                    throw new Error(
                        'Unsafe Input'
                    );
                }
            }
        );
    }

    /* ========================================================
       THREAT LOG
    ======================================================== */

    logThreat(type, payload) {

        console.warn(
            `
🛡 Runtime Security Alert
TYPE: ${type}
PAYLOAD:
            `,
            payload
        );

        window.SOVEREIGN_CACHE
            ?.set(
                `threat-${Date.now()}`,
                {
                    type,
                    payload
                },
                600000
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            blockedPatterns:
                this.blockedPatterns.length
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_SECURITY =
    new SovereignRuntimeSecurity();
