/* ============================================================
   Sovereign AI — runtime-devtools.js
   الإصدار: 6.0.0
   أدوات التطوير السيادية
   ============================================================ */

class SovereignRuntimeDevtools {

    constructor() {

        this.enabled = true;

        console.log(
            '🛠 Runtime Devtools Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.createGlobalConsole();

        this.bindShortcuts();

        this.monitorRuntime();
    }

    /* ========================================================
       GLOBAL CONSOLE
    ======================================================== */

    createGlobalConsole() {

        window.SOVEREIGN_DEVTOOLS = {

            runtime: () => {

                console.table({

                    core:
                        !!window.SOVEREIGN_CORE,

                    state:
                        !!window.SOVEREIGN_STATE,

                    render:
                        !!window.SOVEREIGN_RENDER,

                    cinema:
                        !!window.SOVEREIGN_CINEMA,

                    ai:
                        !!window.SOVEREIGN_AI,

                    socket:
                        !!window.SOVEREIGN_SOCKET,

                    memory:
                        !!window.SOVEREIGN_MEMORY
                });
            },

            metrics: () => {

                console.log(
                    window.SOVEREIGN_METRICS
                        ?.getMetrics()
                );
            },

            memory: () => {

                console.log(
                    window.SOVEREIGN_MEMORY
                        ?.getStats()
                );
            },

            events: () => {

                window.SOVEREIGN_EVENTS
                    ?.debug();
            },

            conversation: () => {

                console.log(
                    window.SOVEREIGN_CHAT
                        ?.getConversation()
                );
            },

            clear: () => {

                console.clear();
            }
        };
    }

    /* ========================================================
       SHORTCUTS
    ======================================================== */

    bindShortcuts() {

        window.addEventListener(
            'keydown',
            (e) => {

                /* =====================================
                   CTRL + SHIFT + D
                ===================================== */

                if (
                    e.ctrlKey &&
                    e.shiftKey &&
                    e.key.toLowerCase() === 'd'
                ) {

                    console.log(
                        `
👑 Sovereign Devtools

Available Commands:

SOVEREIGN_DEVTOOLS.runtime()
SOVEREIGN_DEVTOOLS.metrics()
SOVEREIGN_DEVTOOLS.memory()
SOVEREIGN_DEVTOOLS.events()
SOVEREIGN_DEVTOOLS.conversation()
SOVEREIGN_DEVTOOLS.clear()
                        `
                    );

                    window.SOVEREIGN_NOTIFY
                        ?.info(
                            'Sovereign Devtools Ready'
                        );
                }
            }
        );
    }

    /* ========================================================
       RUNTIME MONITOR
    ======================================================== */

    monitorRuntime() {

        setInterval(() => {

            const fps =
                window.SOVEREIGN_ANIMATION_ENGINE
                    ?.fps || 60;

            if (fps < 20) {

                console.warn(
                    '⚠️ Runtime FPS Critical:',
                    fps
                );
            }

        }, 3000);
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_RUNTIME_DEVTOOLS =
    new SovereignRuntimeDevtools();
