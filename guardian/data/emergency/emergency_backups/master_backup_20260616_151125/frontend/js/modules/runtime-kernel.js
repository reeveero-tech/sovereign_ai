/* ============================================================
   Sovereign AI — runtime-kernel.js
   الإصدار: 7.0.0 (Hybrid Migration Phase)
   النواة السيادية المركزية
   الوظيفة: التنسيق، المراقبة، إدارة دورة الحياة.
   ملاحظة: Kernel ينسق ولا يحتوي Business Logic ثقيل.
   ============================================================ */

class SovereignRuntimeKernel {

    constructor() {

        this.systemHealth = 100;

        this.runtimeState = 'initializing';

        this.activeSystems = [];

        this.lastHeartbeat = Date.now();

        // REFACTOR: الحصول على مرجع للـ Bus من الـ Unified Registry
        // يتم ذلك بعد التأكد من وجود الـ Registry وبعد اكتمال تسجيل الـ Bus نفسه.
        this.runtimeBus = null;

        console.log(
            '🧠 Runtime Kernel Initialized (Hybrid Mode)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.detectSystems();

        // REFACTOR: محاولة الحصول على الـ Bus بعد تهيئة الـ Registry
        this.initBusReference();

        this.startHeartbeat();

        this.monitorPerformance();

        this.bindSignals();

        this.completeInitialization();
    }

    /* ========================================================
       BUS REFERENCE
    ======================================================== */

    initBusReference() {
        // الوصول إلى Bus عبر الـ Unified Registry (النمط الجديد)
        if (window.SOVEREIGN?.get) {
            this.runtimeBus = window.SOVEREIGN.get('bus');
            if (this.runtimeBus) {
                console.log('✅ Kernel connected to Runtime Bus');
            } else {
                console.warn('⚠️ Runtime Bus not yet registered in Unified Registry');
            }
        } else {
            console.warn('⚠️ Unified Registry (window.SOVEREIGN) not available');
        }
    }

    /* ========================================================
       DETECT SYSTEMS
    ======================================================== */

    detectSystems() {

        const systems = [

            'SOVEREIGN_CORE',

            'SOVEREIGN_STATE',

            'SOVEREIGN_RENDER',

            'SOVEREIGN_CINEMA',

            'SOVEREIGN_AI',

            'SOVEREIGN_SOCKET',

            'SOVEREIGN_EVENTS',

            'SOVEREIGN_CHAT',

            'SOVEREIGN_NOTIFY'
        ];

        systems.forEach(system => {

            if (window[system]) {

                this.activeSystems.push(
                    system
                );
            }
        });

        console.log(
            '✅ Active Legacy Systems Detected:',
            this.activeSystems
        );
    }

    /* ========================================================
       HEARTBEAT
    ======================================================== */

    startHeartbeat() {

        setInterval(() => {

            this.lastHeartbeat =
                Date.now();

            // ============================================
            // 1. Legacy Event System (للتوافق مع الأنظمة القديمة)
            // ============================================
            window.SOVEREIGN_EVENTS
                ?.emit(
                    'kernel:heartbeat',
                    {
                        timestamp:
                            this.lastHeartbeat
                    }
                );

            // ============================================
            // 2. New Runtime Bus (النمط الجديد)
            // ============================================
            if (this.runtimeBus) {
                this.runtimeBus.publish('kernel:heartbeat', {
                    timestamp: this.lastHeartbeat,
                    source: 'kernel',
                    state: this.runtimeState
                });
            }

        }, 3000);
    }

    /* ========================================================
       PERFORMANCE MONITORING
    ======================================================== */

    monitorPerformance() {

        setInterval(() => {

            const fps =
                window.SOVEREIGN_ANIMATION_ENGINE
                    ?.fps || 60;

            let previousState = this.runtimeState;
            let previousHealth = this.systemHealth;

            if (fps < 25) {

                this.systemHealth -= 5;
                if (this.systemHealth < 0) this.systemHealth = 0;

                if (this.runtimeState !== 'degraded') {
                    this.runtimeState = 'degraded';
                }

                // ============================================
                // 1. Legacy Event
                // ============================================
                window.SOVEREIGN_EVENTS
                    ?.emit(
                        'kernel:degraded',
                        { fps, health: this.systemHealth }
                    );

                // ============================================
                // 2. New Runtime Bus
                // ============================================
                if (this.runtimeBus) {
                    this.runtimeBus.publish('kernel:state:degraded', {
                        fps,
                        health: this.systemHealth,
                        state: this.runtimeState,
                        source: 'kernel'
                    });
                }

            } else {

                // تعافي تدريجي (يشبه "نظام المناعة")
                this.systemHealth =
                    Math.min(
                        100,
                        this.systemHealth + 1
                    );

                if (this.systemHealth >= 80 && this.runtimeState !== 'stable') {
                    this.runtimeState = 'stable';
                    
                    // ============================================
                    // 1. Legacy Event
                    // ============================================
                    window.SOVEREIGN_EVENTS
                        ?.emit('kernel:stable', { health: this.systemHealth });
                    
                    // ============================================
                    // 2. New Runtime Bus
                    // ============================================
                    if (this.runtimeBus) {
                        this.runtimeBus.publish('kernel:state:stable', {
                            health: this.systemHealth,
                            state: this.runtimeState,
                            source: 'kernel'
                        });
                    }
                }
            }

            // فقط إذا تغيرت القيم، قم بتحديث الـ DOM
            if (previousState !== this.runtimeState || previousHealth !== this.systemHealth) {
                this.syncBodyState();
            }

        }, 4000);
    }

    /* ========================================================
       BODY STATE SYNC
    ======================================================== */

    syncBodyState() {

        document.body.dataset.runtimeState =
            this.runtimeState;

        document.body.dataset.runtimeHealth =
            this.systemHealth;
    }

    /* ========================================================
       SIGNALS (ربط الأحداث الخارجية)
    ======================================================== */

    bindSignals() {

        // ============================================
        // 1. Legacy Event System (للاتصال بالأنظمة القديمة)
        // ============================================
        const events =
            window.SOVEREIGN_EVENTS;

        if (events) {
            events.on(
                'socket:disconnected',
                () => {

                    this.runtimeState =
                        'offline';

                    this.systemHealth -= 10;
                    if (this.systemHealth < 0) this.systemHealth = 0;

                    this.syncBodyState();
                }
            );

            events.on(
                'socket:connected',
                () => {

                    this.runtimeState =
                        'stable';

                    this.systemHealth =
                        Math.min(
                            100,
                            this.systemHealth + 10
                        );

                    this.syncBodyState();
                }
            );
        }

        // ============================================
        // 2. New Runtime Bus (استقبال أوامر من الأنظمة الجديدة)
        // ============================================
        if (this.runtimeBus) {
            // الاشتراك لمعرفة صحة النظام
            this.runtimeBus.subscribe('system:health:request', (payload, meta) => {
                this.runtimeBus.publish('system:health:response', {
                    source: 'kernel',
                    health: this.systemHealth,
                    state: this.runtimeState,
                    systems: this.activeSystems,
                    timestamp: Date.now(),
                    requestId: meta?.messageId
                });
            });

            // الاشتراك لاستقبال أوامر إعادة الضبط
            this.runtimeBus.subscribe('system:reset', () => {
                console.log('🔄 Kernel received reset command via Bus');
                this.systemHealth = 100;
                this.runtimeState = 'online';
                this.syncBodyState();
                
                this.runtimeBus.publish('system:reset:ack', {
                    source: 'kernel',
                    success: true,
                    timestamp: Date.now()
                });
            });
        }
    }

    /* ========================================================
       COMPLETE INITIALIZATION
    ======================================================== */

    completeInitialization() {

        this.runtimeState =
            'online';

        this.syncBodyState();

        console.log(
            `
👑 SOVEREIGN KERNEL ONLINE
==========================
HEALTH: ${this.systemHealth}
SYSTEMS: ${this.activeSystems.length}
STATE: ${this.runtimeState}
BUS CONNECTED: ${!!this.runtimeBus}
            `
        );

        // ============================================
        // 1. Legacy Notification
        // ============================================
        window.SOVEREIGN_NOTIFY
            ?.success(
                'Runtime Kernel Online'
            );

        // ============================================
        // 2. New Runtime Bus Event
        // ============================================
        if (this.runtimeBus) {
            this.runtimeBus.publish('kernel:ready', {
                health: this.systemHealth,
                state: this.runtimeState,
                systems: this.activeSystems,
                timestamp: Date.now(),
                source: 'kernel'
            });
        }
    }

    /* ========================================================
       PUBLIC API
    ======================================================== */

    getStatus() {

        return {

            health:
                this.systemHealth,

            state:
                this.runtimeState,

            systems:
                this.activeSystems,

            heartbeat:
                this.lastHeartbeat,

            busConnected:
                !!this.runtimeBus
        };
    }
}

/* ============================================================
   HYBRID MIGRATION PHASE
   - Legacy Global: الحفاظ على التوافق القديم (لا يمكن حذفه الآن)
   - Unified Registry: التسجيل في النواة الموحدة (البداية الحقيقية لـ Runtime Operating Fabric)
   ============================================================ */

const sovereignKernel =
    new SovereignRuntimeKernel();

/* =========================================
   1. Legacy Global (للتوافق مع الأنظمة القديمة)
   ========================================= */

window.SOVEREIGN_KERNEL =
    sovereignKernel;

/* =========================================
   2. Unified Registry (التسجيل في النواة الموحدة)
   ========================================= */

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register(
        'kernel',
        sovereignKernel
    );
    console.log('✅ Kernel registered in Unified Registry');
} else {
    console.warn(
        '⚠️ Unified Registry not yet available. Kernel registered as legacy global only (Hybrid Mode).'
    );
}
