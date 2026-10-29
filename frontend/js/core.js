/* ============================================================
   Sovereign AI — core.js
   الإصدار: 4.0.0
   النواة المركزية المركزية
   ============================================================ */

class SovereignCore {
    constructor() {

        /* =========================================
           الحالة العامة للنظام
        ========================================= */

        this.state = {

            system: {
                initialized: false,
                mode: 'cinematic',
                performanceMode: 'adaptive',
                deviceTier: 'unknown',
                fps: 60,
                alive: true
            },

            visual: {
                holographic: true,
                particles: true,
                glow: true,
                motion: true,
                intensity: 1
            },

            network: {
                connected: false,
                latency: 0
            },

            ui: {
                activeTab: 'monitor',
                modals: [],
                notifications: []
            }
        };

        /* =========================================
           Event Bus
        ========================================= */

        this.events = {};

        /* =========================================
           Performance Monitor
        ========================================= */

        this.performance = {
            fps: 60,
            frameTime: 16.6,
            gpuStress: 0,
            memoryPressure: 0
        };

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        console.log('🧠 Sovereign Core Initialized');

        this.detectDeviceTier();

        this.startPerformanceMonitor();

        this.state.system.initialized = true;

        this.emit('core:initialized', this.state);
    }

    /* ========================================================
       EVENT BUS
    ======================================================== */

    on(event, callback) {

        if (!this.events[event]) {
            this.events[event] = [];
        }

        this.events[event].push(callback);
    }

    emit(event, data = null) {

        if (!this.events[event]) return;

        this.events[event].forEach(callback => {
            callback(data);
        });
    }

    off(event, callback) {

        if (!this.events[event]) return;

        this.events[event] =
            this.events[event].filter(cb => cb !== callback);
    }

    /* ========================================================
       STATE MANAGEMENT
    ======================================================== */

    setState(path, value) {

        const keys = path.split('.');

        let current = this.state;

        for (let i = 0; i < keys.length - 1; i++) {
            current = current[keys[i]];
        }

        current[keys[keys.length - 1]] = value;

        this.emit('state:update', {
            path,
            value
        });
    }

    getState(path) {

        const keys = path.split('.');

        let current = this.state;

        for (const key of keys) {

            if (current[key] === undefined) {
                return null;
            }

            current = current[key];
        }

        return current;
    }

    /* ========================================================
       DEVICE INTELLIGENCE
    ======================================================== */

    detectDeviceTier() {

        const memory = navigator.deviceMemory || 4;

        const cores = navigator.hardwareConcurrency || 4;

        const width = window.innerWidth;

        if (memory >= 16 && cores >= 8 && width >= 1440) {

            this.state.system.deviceTier = 'ultra';

        } else if (memory >= 8) {

            this.state.system.deviceTier = 'high';

        } else if (memory >= 4) {

            this.state.system.deviceTier = 'medium';

        } else {

            this.state.system.deviceTier = 'low';
        }

        console.log(
            '⚡ Device Tier:',
            this.state.system.deviceTier
        );
    }

    /* ========================================================
       PERFORMANCE MONITOR
    ======================================================== */

    startPerformanceMonitor() {

        let lastFrame = performance.now();

        const monitor = (now) => {

            const delta = now - lastFrame;

            this.performance.fps = Math.round(1000 / delta);

            this.performance.frameTime = delta;

            lastFrame = now;

            this.adaptiveOptimization();

            requestAnimationFrame(monitor);
        };

        requestAnimationFrame(monitor);
    }

    /* ========================================================
       ADAPTIVE OPTIMIZATION
    ======================================================== */

    adaptiveOptimization() {

        const fps = this.performance.fps;

        if (fps < 30) {

            this.setState('visual.intensity', 0.4);

            this.emit('performance:critical');

        } else if (fps < 45) {

            this.setState('visual.intensity', 0.7);

            this.emit('performance:degraded');

        } else {

            this.setState('visual.intensity', 1);

            this.emit('performance:stable');
        }
    }
}

/* ============================================================
   إنشاء النواة العالمية
============================================================ */

window.SOVEREIGN_CORE = new SovereignCore();
