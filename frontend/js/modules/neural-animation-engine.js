/* ============================================================
   Sovereign AI — neural-animation-engine.js
   الإصدار: 4.0.0
   محرك الأنيميشن العصبي السيادي
   ============================================================ */

class SovereignNeuralAnimationEngine {

    constructor() {

        this.animations = new Map();

        this.activeAnimations = new Set();

        this.frame = null;

        this.lastTime = performance.now();

        this.delta = 0;

        this.fps = 60;

        this.isRunning = true;

        console.log(
            '🧠 Neural Animation Engine Initialized'
        );

        this.start();
    }

    /* ========================================================
       START LOOP
    ======================================================== */

    start() {

        const loop = (time) => {

            if (!this.isRunning) return;

            this.delta = time - this.lastTime;

            this.fps =
                Math.round(1000 / this.delta);

            this.lastTime = time;

            this.update();

            this.frame =
                requestAnimationFrame(loop);
        };

        this.frame =
            requestAnimationFrame(loop);
    }

    /* ========================================================
       UPDATE
    ======================================================== */

    update() {

        this.activeAnimations.forEach(
            animation => {

                try {

                    animation.update(
                        this.delta
                    );

                } catch (error) {

                    console.error(
                        'Animation Error:',
                        error
                    );
                }
            }
        );

        this.syncPerformance();
    }

    /* ========================================================
       PERFORMANCE SYNC
    ======================================================== */

    syncPerformance() {

        if (
            window.SOVEREIGN_STATE
        ) {

            window.SOVEREIGN_STATE.mergeState(
                'metrics',
                {
                    fps: this.fps
                }
            );
        }

        if (
            window.SOVEREIGN_CORE
        ) {

            window.SOVEREIGN_CORE.performance.fps =
                this.fps;
        }
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    register(name, animationObject) {

        this.animations.set(
            name,
            animationObject
        );
    }

    /* ========================================================
       PLAY
    ======================================================== */

    play(name) {

        const animation =
            this.animations.get(name);

        if (!animation) return;

        this.activeAnimations.add(
            animation
        );

        if (
            animation.start
        ) {

            animation.start();
        }
    }

    /* ========================================================
       STOP
    ======================================================== */

    stop(name) {

        const animation =
            this.animations.get(name);

        if (!animation) return;

        this.activeAnimations.delete(
            animation
        );

        if (
            animation.stop
        ) {

            animation.stop();
        }
    }

    /* ========================================================
       CREATE FLOAT EFFECT
    ======================================================== */

    createFloatEffect(
        element,
        intensity = 2
    ) {

        return {

            update: () => {

                const time =
                    performance.now() * 0.001;

                const y =
                    Math.sin(time) * intensity;

                element.style.transform =
                    `translateY(${y}px)`;
            }
        };
    }

    /* ========================================================
       CREATE PULSE EFFECT
    ======================================================== */

    createPulseEffect(
        element,
        intensity = 1
    ) {

        return {

            update: () => {

                const time =
                    performance.now() * 0.002;

                const scale =
                    1 +
                    Math.sin(time) *
                    0.03 *
                    intensity;

                element.style.transform =
                    `scale(${scale})`;
            }
        };
    }

    /* ========================================================
       CREATE GLOW EFFECT
    ======================================================== */

    createGlowEffect(
        element
    ) {

        return {

            update: () => {

                const time =
                    performance.now() * 0.0015;

                const glow =
                    10 +
                    Math.sin(time) * 10;

                element.style.boxShadow =
                    `
                    0 0 ${glow}px
                    rgba(79,209,197,0.5)
                    `;
            }
        };
    }

    /* ========================================================
       MASS OPTIMIZATION
    ======================================================== */

    optimize() {

        if (
            this.fps < 30
        ) {

            document.body.classList.add(
                'neural-safe-mode'
            );

        } else {

            document.body.classList.remove(
                'neural-safe-mode'
            );
        }
    }

    /* ========================================================
       STOP ENGINE
    ======================================================== */

    shutdown() {

        this.isRunning = false;

        cancelAnimationFrame(
            this.frame
        );

        this.activeAnimations.clear();

        console.log(
            '🛑 Neural Animation Engine Stopped'
        );
    }
}

/* ============================================================
   إنشاء المحرك العالمي
============================================================ */

window.SOVEREIGN_ANIMATION_ENGINE =
    new SovereignNeuralAnimationEngine();
