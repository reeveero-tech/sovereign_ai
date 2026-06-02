/* ============================================================
   Sovereign AI — adaptive-effects.js
   الإصدار: 4.0.0
   محرك التأثيرات التكيفية السيادي
   ============================================================ */

class SovereignAdaptiveEffects {

    constructor() {

        this.currentMode = 'cinematic';

        this.effectLevel = 1;

        this.activeEffects = new Set();

        this.performanceState = 'stable';

        console.log(
            '✨ Adaptive Effects Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.detectCapabilities();

        this.bindCoreEvents();

        this.startDynamicEffects();
    }

    /* ========================================================
       DEVICE CAPABILITIES
    ======================================================== */

    detectCapabilities() {

        const tier =
            window.SOVEREIGN_CORE
                ?.state
                ?.system
                ?.deviceTier;

        switch (tier) {

            case 'ultra':

                this.currentMode =
                    'cinematic';

                this.effectLevel = 1;

                break;

            case 'high':

                this.currentMode =
                    'immersive';

                this.effectLevel = 0.85;

                break;

            case 'medium':

                this.currentMode =
                    'adaptive';

                this.effectLevel = 0.65;

                break;

            default:

                this.currentMode =
                    'safe';

                this.effectLevel = 0.4;
        }

        document.body.dataset.fxMode =
            this.currentMode;

        console.log(
            '🎛 FX Mode:',
            this.currentMode
        );
    }

    /* ========================================================
       CORE EVENTS
    ======================================================== */

    bindCoreEvents() {

        const core =
            window.SOVEREIGN_CORE;

        if (!core) return;

        core.on(
            'performance:critical',
            () => {

                this.reduceEffects();
            }
        );

        core.on(
            'performance:degraded',
            () => {

                this.optimizeEffects();
            }
        );

        core.on(
            'performance:stable',
            () => {

                this.restoreEffects();
            }
        );
    }

    /* ========================================================
       REDUCE EFFECTS
    ======================================================== */

    reduceEffects() {

        this.performanceState =
            'critical';

        document.body.classList.add(
            'fx-reduced'
        );

        document.body.style.setProperty(
            '--holo-intensity',
            '0.2'
        );

        document.body.style.setProperty(
            '--glow-size',
            '8px'
        );

        console.warn(
            '⚠️ Effects Reduced'
        );
    }

    /* ========================================================
       OPTIMIZE EFFECTS
    ======================================================== */

    optimizeEffects() {

        this.performanceState =
            'degraded';

        document.body.classList.add(
            'fx-optimized'
        );

        document.body.style.setProperty(
            '--holo-intensity',
            '0.5'
        );

        document.body.style.setProperty(
            '--glow-size',
            '14px'
        );

        console.warn(
            '⚡ Effects Optimized'
        );
    }

    /* ========================================================
       RESTORE EFFECTS
    ======================================================== */

    restoreEffects() {

        this.performanceState =
            'stable';

        document.body.classList.remove(
            'fx-reduced'
        );

        document.body.classList.remove(
            'fx-optimized'
        );

        document.body.style.setProperty(
            '--holo-intensity',
            '1'
        );

        document.body.style.setProperty(
            '--glow-size',
            '20px'
        );
    }

    /* ========================================================
       DYNAMIC MOTION
    ======================================================== */

    startDynamicEffects() {

        let mouseX = 0;
        let mouseY = 0;

        window.addEventListener(
            'mousemove',
            (e) => {

                mouseX =
                    e.clientX / window.innerWidth;

                mouseY =
                    e.clientY / window.innerHeight;

                this.updateAmbientLighting(
                    mouseX,
                    mouseY
                );
            },
            {
                passive: true
            }
        );
    }

    /* ========================================================
       AMBIENT LIGHTING
    ======================================================== */

    updateAmbientLighting(x, y) {

        requestAnimationFrame(() => {

            document.body.style.setProperty(
                '--mouse-x',
                `${x * 100}%`
            );

            document.body.style.setProperty(
                '--mouse-y',
                `${y * 100}%`
            );
        });
    }

    /* ========================================================
       ACTIVATE EFFECT
    ======================================================== */

    activateEffect(name) {

        this.activeEffects.add(name);

        document.body.classList.add(
            `fx-${name}`
        );
    }

    /* ========================================================
       DEACTIVATE EFFECT
    ======================================================== */

    deactivateEffect(name) {

        this.activeEffects.delete(name);

        document.body.classList.remove(
            `fx-${name}`
        );
    }

    /* ========================================================
       CINEMATIC FLASH
    ======================================================== */

    cinematicFlash(
        intensity = 1
    ) {

        const flash =
            document.createElement('div');

        flash.className =
            'cinematic-flash';

        flash.style.cssText = `
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 999999;
            background:
                radial-gradient(
                    circle,
                    rgba(79,209,197,${0.15 * intensity}),
                    transparent 70%
                );
            opacity: 0;
            transition: opacity 0.3s ease;
        `;

        document.body.appendChild(
            flash
        );

        requestAnimationFrame(() => {

            flash.style.opacity = '1';

            setTimeout(() => {

                flash.style.opacity = '0';

                setTimeout(() => {

                    flash.remove();

                }, 300);

            }, 120);
        });
    }

    /* ========================================================
       SYSTEM PULSE
    ======================================================== */

    pulseSystem() {

        document.body.classList.add(
            'system-pulse'
        );

        setTimeout(() => {

            document.body.classList.remove(
                'system-pulse'
            );

        }, 1000);
    }
}

/* ============================================================
   إنشاء المحرك العالمي
============================================================ */

window.SOVEREIGN_FX =
    new SovereignAdaptiveEffects();
