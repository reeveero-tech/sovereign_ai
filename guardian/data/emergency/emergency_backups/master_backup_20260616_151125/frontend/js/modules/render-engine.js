/* ============================================================
   Sovereign AI — render-engine.js
   الإصدار: 4.0.0
   محرك الرسم السيادي
   ============================================================ */

class SovereignRenderEngine {

    constructor() {

        this.renderQueue = [];

        this.isRendering = false;

        this.frameId = null;

        this.components = new Map();

        this.cachedNodes = new Map();

        console.log('🎨 Sovereign Render Engine Initialized');

        this.start();
    }

    /* ========================================================
       START ENGINE
    ======================================================== */

    start() {

        const loop = () => {

            this.processQueue();

            this.frameId =
                requestAnimationFrame(loop);
        };

        loop();
    }

    /* ========================================================
       REGISTER COMPONENT
    ======================================================== */

    register(name, element) {

        if (!element) return;

        this.components.set(name, element);

        this.cachedNodes.set(name, {
            element,
            html: element.innerHTML
        });
    }

    /* ========================================================
       QUEUE RENDER
    ======================================================== */

    queueRender(task) {

        this.renderQueue.push(task);
    }

    /* ========================================================
       PROCESS QUEUE
    ======================================================== */

    processQueue() {

        if (this.isRendering) return;

        if (!this.renderQueue.length) return;

        this.isRendering = true;

        const start =
            performance.now();

        while (
            this.renderQueue.length &&
            performance.now() - start < 8
        ) {

            const task =
                this.renderQueue.shift();

            try {

                task();

            } catch (error) {

                console.error(
                    'Render Task Error:',
                    error
                );
            }
        }

        this.isRendering = false;
    }

    /* ========================================================
       SAFE TEXT UPDATE
    ======================================================== */

    updateText(id, value) {

        this.queueRender(() => {

            const el =
                document.getElementById(id);

            if (!el) return;

            const text =
                String(value);

            if (el.textContent !== text) {

                el.textContent = text;
            }
        });
    }

    /* ========================================================
       SAFE HTML UPDATE
    ======================================================== */

    updateHTML(id, html) {

        this.queueRender(() => {

            const el =
                document.getElementById(id);

            if (!el) return;

            if (el.innerHTML !== html) {

                el.innerHTML = html;
            }
        });
    }

    /* ========================================================
       SAFE STYLE UPDATE
    ======================================================== */

    updateStyle(id, styles = {}) {

        this.queueRender(() => {

            const el =
                document.getElementById(id);

            if (!el) return;

            Object.entries(styles)
                .forEach(([key, value]) => {

                    el.style[key] = value;
                });
        });
    }

    /* ========================================================
       CLASS TOGGLE
    ======================================================== */

    toggleClass(id, className, force = null) {

        this.queueRender(() => {

            const el =
                document.getElementById(id);

            if (!el) return;

            if (force === null) {

                el.classList.toggle(className);

            } else {

                el.classList.toggle(
                    className,
                    force
                );
            }
        });
    }

    /* ========================================================
       APPEND NODE
    ======================================================== */

    appendNode(parentId, node) {

        this.queueRender(() => {

            const parent =
                document.getElementById(parentId);

            if (!parent) return;

            parent.appendChild(node);
        });
    }

    /* ========================================================
       REMOVE NODE
    ======================================================== */

    removeNode(node) {

        this.queueRender(() => {

            if (
                node &&
                node.parentNode
            ) {

                node.parentNode.removeChild(node);
            }
        });
    }

    /* ========================================================
       BATCH UPDATE
    ======================================================== */

    batch(tasks = []) {

        this.queueRender(() => {

            tasks.forEach(task => {

                try {

                    task();

                } catch (error) {

                    console.error(
                        'Batch Render Error:',
                        error
                    );
                }
            });
        });
    }

    /* ========================================================
       PERFORMANCE CLEANUP
    ======================================================== */

    cleanup() {

        if (this.renderQueue.length > 1000) {

            console.warn(
                '⚠️ Render Queue Overflow'
            );

            this.renderQueue =
                this.renderQueue.slice(-200);
        }
    }

    /* ========================================================
       DESTROY
    ======================================================== */

    destroy() {

        if (this.frameId) {

            cancelAnimationFrame(
                this.frameId
            );
        }

        this.renderQueue = [];

        this.components.clear();

        this.cachedNodes.clear();
    }
}

/* ============================================================
   إنشاء المحرك العالمي
============================================================ */

window.SOVEREIGN_RENDER =
    new SovereignRenderEngine();
