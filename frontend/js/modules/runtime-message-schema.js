/* ============================================================
   Sovereign AI — runtime-message-schema.js
   الإصدار: 8.0.0
   مخطط الرسائل السيادي
   ============================================================ */

class SovereignRuntimeMessageSchema {

    constructor() {

        this.version = '8.0.0';

        console.log(
            '📨 Runtime Message Schema Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.publishReady();
    }

    /* ========================================================
       CREATE MESSAGE
    ======================================================== */

    create({

        type = 'runtime.message',

        source = 'unknown',

        channel = 'runtime',

        payload = {},

        meta = {}
    }) {

        return {

            id:
                crypto.randomUUID(),

            type,

            source,

            channel,

            payload,

            meta,

            timestamp:
                Date.now(),

            version:
                this.version
        };
    }

    /* ========================================================
       VALIDATE
    ======================================================== */

    validate(message) {

        if (
            !message ||
            typeof message !== 'object'
        ) {

            return false;
        }

        const required = [

            'id',

            'type',

            'source',

            'channel',

            'payload',

            'timestamp',

            'version'
        ];

        for (
            const field
            of required
        ) {

            if (
                !(field in message)
            ) {

                console.warn(
                    `
⚠️ Runtime Message Invalid
Missing:
${field}
                    `
                );

                return false;
            }
        }

        return true;
    }

    /* ========================================================
       NORMALIZE
    ======================================================== */

    normalize(message = {}) {

        return {

            id:
                message.id
                || crypto.randomUUID(),

            type:
                message.type
                || 'runtime.message',

            source:
                message.source
                || 'unknown',

            channel:
                message.channel
                || 'runtime',

            payload:
                message.payload
                || {},

            meta:
                message.meta
                || {},

            timestamp:
                message.timestamp
                || Date.now(),

            version:
                message.version
                || this.version
        };
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'schema:ready',
            {

                version:
                    this.version,

                timestamp:
                    Date.now()
            }
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            version:
                this.version
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignMessageSchema =
    new SovereignRuntimeMessageSchema();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SCHEMA =
    sovereignMessageSchema;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'message-schema',
        sovereignMessageSchema
    );
