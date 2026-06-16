/* ============================================================
   Sovereign AI — state-manager.js
   الإصدار: 4.0.0
   نظام إدارة الحالة السيادي
   ============================================================ */

class SovereignStateManager {

    constructor() {

        this.store = {};

        this.listeners = {};

        this.history = [];

        this.maxHistory = 100;

        console.log('🧠 Sovereign State Manager Initialized');
    }

    /* ========================================================
       إنشاء حالة
    ======================================================== */

    createState(key, initialValue = null) {

        if (this.store[key] !== undefined) return;

        this.store[key] = initialValue;

        this.listeners[key] = [];
    }

    /* ========================================================
       قراءة حالة
    ======================================================== */

    getState(key) {

        return this.store[key];
    }

    /* ========================================================
       تحديث حالة
    ======================================================== */

    setState(key, value) {

        const oldValue = this.store[key];

        this.store[key] = value;

        this.saveHistory(key, oldValue, value);

        this.notify(key, value, oldValue);
    }

    /* ========================================================
       دمج حالة Object
    ======================================================== */

    mergeState(key, partialState = {}) {

        const current = this.store[key] || {};

        const updated = {
            ...current,
            ...partialState
        };

        this.setState(key, updated);
    }

    /* ========================================================
       الاشتراك في التغييرات
    ======================================================== */

    subscribe(key, callback) {

        if (!this.listeners[key]) {
            this.listeners[key] = [];
        }

        this.listeners[key].push(callback);

        return () => {
            this.unsubscribe(key, callback);
        };
    }

    /* ========================================================
       إلغاء الاشتراك
    ======================================================== */

    unsubscribe(key, callback) {

        if (!this.listeners[key]) return;

        this.listeners[key] =
            this.listeners[key].filter(cb => cb !== callback);
    }

    /* ========================================================
       إرسال التحديثات
    ======================================================== */

    notify(key, newValue, oldValue) {

        if (!this.listeners[key]) return;

        this.listeners[key].forEach(callback => {

            callback({
                key,
                newValue,
                oldValue
            });

        });

        /* =========================================
           ربط مع النواة
        ========================================= */

        if (window.SOVEREIGN_CORE) {

            window.SOVEREIGN_CORE.emit(
                'state:changed',
                {
                    key,
                    newValue,
                    oldValue
                }
            );
        }
    }

    /* ========================================================
       حفظ التاريخ
    ======================================================== */

    saveHistory(key, oldValue, newValue) {

        this.history.push({
            key,
            oldValue,
            newValue,
            timestamp: Date.now()
        });

        if (this.history.length > this.maxHistory) {

            this.history.shift();
        }
    }

    /* ========================================================
       الحصول على السجل
    ======================================================== */

    getHistory() {

        return this.history;
    }

    /* ========================================================
       إعادة تعيين
    ======================================================== */

    reset() {

        this.store = {};

        this.listeners = {};

        this.history = [];

        console.log('♻️ Sovereign State Reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_STATE =
    new SovereignStateManager();

/* ============================================================
   إنشاء الحالات الأساسية
============================================================ */

window.SOVEREIGN_STATE.createState(
    'ui',
    {
        activeTab: 'monitor',
        modals: [],
        notifications: []
    }
);

window.SOVEREIGN_STATE.createState(
    'system',
    {
        connected: false,
        initialized: false,
        mode: 'cinematic'
    }
);

window.SOVEREIGN_STATE.createState(
    'metrics',
    {
        fps: 60,
        cycles: 0,
        health: 100
    }
);

window.SOVEREIGN_STATE.createState(
    'visual',
    {
        holographic: true,
        particles: true,
        glow: true,
        intensity: 1
    }
);
