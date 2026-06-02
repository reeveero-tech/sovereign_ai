/* ============================================================
   Sovereign AI — command-runtime.js
   الإصدار: 5.0.0
   نظام الأوامر السيادي
   ============================================================ */

class SovereignCommandRuntime {

    constructor() {

        this.history = [];

        this.maxHistory = 100;

        this.input = null;

        this.button = null;

        console.log(
            '👑 Command Runtime Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.input =
            document.getElementById(
                'sir-command-input'
            );

        this.button =
            document.getElementById(
                'btn-send-sir-command'
            );

        this.bindEvents();
    }

    /* ========================================================
       EVENTS
    ======================================================== */

    bindEvents() {

        if (
            this.button
        ) {

            this.button.addEventListener(
                'click',
                () => {

                    this.execute();
                }
            );
        }

        if (
            this.input
        ) {

            this.input.addEventListener(
                'keydown',
                (e) => {

                    if (
                        e.key === 'Enter' &&
                        !e.shiftKey
                    ) {

                        e.preventDefault();

                        this.execute();
                    }
                }
            );
        }
    }

    /* ========================================================
       EXECUTE
    ======================================================== */

    execute() {

        const command =
            this.input?.value?.trim();

        if (!command) return;

        this.saveHistory(command);

        this.renderCommand(
            command
        );

        this.processCommand(
            command
        );

        this.clearInput();

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .createMoment(
                    'epic'
                );
        }
    }

    /* ========================================================
       PROCESS
    ======================================================== */

    processCommand(command) {

        const lower =
            command.toLowerCase();

        /* =========================================
           RESET
        ========================================= */

        if (
            lower === 'reset'
        ) {

            location.reload();

            return;
        }

        /* =========================================
           STATUS
        ========================================= */

        if (
            lower === 'status'
        ) {

            const metrics =
                window.SOVEREIGN_METRICS
                    ?.getMetrics();

            console.log(
                '📊 STATUS:',
                metrics
            );

            return;
        }

        /* =========================================
           MEMORY CLEAR
        ========================================= */

        if (
            lower === 'clear memory'
        ) {

            window.SOVEREIGN_MEMORY
                ?.clearMemory();

            return;
        }

        /* =========================================
           AI COMMAND
        ========================================= */

        if (
            window.SOVEREIGN_SOCKET
        ) {

            window.SOVEREIGN_SOCKET
                .send(
                    'sovereign_command',
                    {
                        command
                    }
                );
        }
    }

    /* ========================================================
       RENDER
    ======================================================== */

    renderCommand(command) {

        const container =
            document.getElementById(
                'commands-list'
            );

        if (!container) return;

        const item =
            document.createElement('div');

        item.className =
            `
            command-item
            glass
            sovereign-live-message
            `;

        item.innerHTML = `
            <div class="command-header">
                <div class="command-name">
                    👑 ${command}
                </div>

                <div class="command-time">
                    ${
                        new Date()
                        .toLocaleTimeString('ar-SA')
                    }
                </div>
            </div>

            <div class="command-status success">
                جاري التنفيذ...
            </div>
        `;

        container.prepend(item);
    }

    /* ========================================================
       HISTORY
    ======================================================== */

    saveHistory(command) {

        this.history.unshift({

            command,

            timestamp:
                Date.now()
        });

        if (
            this.history.length >
            this.maxHistory
        ) {

            this.history.pop();
        }
    }

    /* ========================================================
       CLEAR
    ======================================================== */

    clearInput() {

        if (
            this.input
        ) {

            this.input.value = '';
        }
    }

    /* ========================================================
       GET HISTORY
    ======================================================== */

    getHistory() {

        return this.history;
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_COMMANDS =
    new SovereignCommandRuntime();
