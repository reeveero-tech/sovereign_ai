/* ============================================================
   Sovereign AI — cinematic-engine.js
   الإصدار: 4.0.0
   المحرك السينمائي السيادي
   ============================================================ */

class SovereignCinematicEngine {

    constructor() {

        this.activeScene = 'idle';

        this.isTransitioning = false;

        this.sceneHistory = [];

        this.currentIntensity = 1;

        console.log(
            '🎬 Cinematic Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindCoreEvents();

        this.initializeAtmosphere();
    }

    /* ========================================================
       CORE EVENTS
    ======================================================== */

    bindCoreEvents() {

        const core =
            window.SOVEREIGN_CORE;

        if (!core) return;

        core.on(
            'core:initialized',
            () => {

                this.enterScene('awakening');
            }
        );

        core.on(
            'state:changed',
            (data) => {

                this.reactToState(data);
            }
        );
    }

    /* ========================================================
       INITIAL ATMOSPHERE
    ======================================================== */

    initializeAtmosphere() {

        document.body.classList.add(
            'cinematic-ready'
        );

        document.body.style.setProperty(
            '--cinematic-intensity',
            '1'
        );
    }

    /* ========================================================
       ENTER SCENE
    ======================================================== */

    enterScene(scene) {

        if (this.isTransitioning) return;

        this.isTransitioning = true;

        this.sceneHistory.push({
            from: this.activeScene,
            to: scene,
            timestamp: Date.now()
        });

        document.body.dataset.scene = scene;

        this.applySceneEffects(scene);

        this.activeScene = scene;

        setTimeout(() => {

            this.isTransitioning = false;

        }, 1200);

        console.log(
            `🎞 Scene: ${scene}`
        );
    }

    /* ========================================================
       SCENE EFFECTS
    ======================================================== */

    applySceneEffects(scene) {

        switch (scene) {

            case 'awakening':

                this.awakeningSequence();

                break;

            case 'thinking':

                this.thinkingSequence();

                break;

            case 'response':

                this.responseSequence();

                break;

            case 'critical':

                this.criticalSequence();

                break;

            case 'idle':

                this.idleSequence();

                break;
        }
    }

    /* ========================================================
       AWAKENING
    ======================================================== */

    awakeningSequence() {

        this.flash(
            'rgba(79,209,197,0.12)'
        );

        document.body.classList.add(
            'scene-awakening'
        );

        setTimeout(() => {

            document.body.classList.remove(
                'scene-awakening'
            );

        }, 3000);
    }

    /* ========================================================
       THINKING
    ======================================================== */

    thinkingSequence() {

        document.body.classList.add(
            'scene-thinking'
        );

        this.pulse(
            1.2
        );

        setTimeout(() => {

            document.body.classList.remove(
                'scene-thinking'
            );

        }, 2000);
    }

    /* ========================================================
       RESPONSE
    ======================================================== */

    responseSequence() {

        this.flash(
            'rgba(129,140,248,0.08)'
        );

        document.body.classList.add(
            'scene-response'
        );

        setTimeout(() => {

            document.body.classList.remove(
                'scene-response'
            );

        }, 1500);
    }

    /* ========================================================
       CRITICAL
    ======================================================== */

    criticalSequence() {

        this.flash(
            'rgba(239,68,68,0.12)'
        );

        document.body.classList.add(
            'scene-critical'
        );

        navigator.vibrate?.(120);

        setTimeout(() => {

            document.body.classList.remove(
                'scene-critical'
            );

        }, 2000);
    }

    /* ========================================================
       IDLE
    ======================================================== */

    idleSequence() {

        document.body.classList.add(
            'scene-idle'
        );

        setTimeout(() => {

            document.body.classList.remove(
                'scene-idle'
            );

        }, 1000);
    }

    /* ========================================================
       FLASH EFFECT
    ======================================================== */

    flash(color) {

        const flash =
            document.createElement('div');

        flash.style.cssText = `
            position: fixed;
            inset: 0;
            z-index: 999999;
            pointer-events: none;
            background: radial-gradient(
                circle,
                ${color},
                transparent 70%
            );
            opacity: 0;
            transition: opacity 0.5s ease;
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

                }, 600);

            }, 150);
        });
    }

    /* ========================================================
       PULSE
    ======================================================== */

    pulse(intensity = 1) {

        document.body.style.setProperty(
            '--system-pulse-scale',
            intensity
        );

        document.body.classList.add(
            'system-pulse-active'
        );

        setTimeout(() => {

            document.body.classList.remove(
                'system-pulse-active'
            );

        }, 1000);
    }

    /* ========================================================
       REACT TO STATE
    ======================================================== */

    reactToState(data) {

        if (!data) return;

        const key =
            data.key;

        if (key === 'system') {

            const state =
                data.newValue;

            if (state.connected) {

                this.enterScene(
                    'response'
                );

            } else {

                this.enterScene(
                    'critical'
                );
            }
        }

        if (key === 'metrics') {

            const metrics =
                data.newValue;

            if (
                metrics.fps &&
                metrics.fps < 25
            ) {

                this.enterScene(
                    'critical'
                );
            }
        }
    }

    /* ========================================================
       GLOBAL MOMENT
    ======================================================== */

    createMoment(type = 'epic') {

        switch (type) {

            case 'epic':

                this.flash(
                    'rgba(79,209,197,0.18)'
                );

                this.pulse(1.5);

                break;

            case 'warning':

                this.enterScene(
                    'critical'
                );

                break;

            case 'success':

                this.enterScene(
                    'response'
                );

                break;
        }
    }
}

/* ============================================================
   إنشاء المحرك العالمي
============================================================ */

window.SOVEREIGN_CINEMA =
    new SovereignCinematicEngine();
