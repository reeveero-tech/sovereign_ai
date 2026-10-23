/* ============================================================
   Sovereign AI — interface-runtime.js
   الإصدار: 6.0.0
   واجهة التشغيل السيادية
   ============================================================ */

class SovereignInterfaceRuntime {

    constructor() {

        this.activeTab = 'monitor';

        console.log(
            '🖥 Interface Runtime Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindTabs();

        this.bindToggles();

        this.bindQuickActions();

        this.bindCounters();
    }

    /* ========================================================
       TABS
    ======================================================== */

    bindTabs() {

        const tabs =
            document.querySelectorAll(
                '.tab'
            );

        tabs.forEach(tab => {

            tab.addEventListener(
                'click',
                () => {

                    const target =
                        tab.dataset.tab;

                    this.switchTab(
                        target
                    );
                }
            );
        });
    }

    /* ========================================================
       SWITCH TAB
    ======================================================== */

    switchTab(tabId) {

        this.activeTab = tabId;

        document
            .querySelectorAll('.tab')
            .forEach(tab => {

                tab.classList.toggle(
                    'active',
                    tab.dataset.tab === tabId
                );
            });

        document
            .querySelectorAll('.tab-content')
            .forEach(content => {

                const active =
                    content.id ===
                    `tab-${tabId}`;

                content.style.display =
                    active
                        ? 'block'
                        : 'none';
            });

        window.SOVEREIGN_EVENTS
            ?.emit(
                'ui:tab_changed',
                {
                    tab: tabId
                }
            );

        window.SOVEREIGN_CINEMA
            ?.pulse(1.05);
    }

    /* ========================================================
       TOGGLES
    ======================================================== */

    bindToggles() {

        const holographic =
            document.getElementById(
                'toggle-holographic'
            );

        if (
            holographic
        ) {

            holographic.addEventListener(
                'change',
                (e) => {

                    document.body.classList.toggle(
                        'reduced-holographic',
                        !e.target.checked
                    );

                    window.SOVEREIGN_NOTIFY
                        ?.info(
                            e.target.checked
                                ? 'Holographic Effects Enabled'
                                : 'Holographic Effects Reduced'
                        );
                }
            );
        }
    }

    /* ========================================================
       QUICK ACTIONS
    ======================================================== */

    bindQuickActions() {

        const cycle =
            document.getElementById(
                'btn-run-cycle'
            );

        if (
            cycle
        ) {

            cycle.addEventListener(
                'click',
                () => {

                    window.SOVEREIGN_CINEMA
                        ?.createMoment(
                            'epic'
                        );

                    window.SOVEREIGN_NOTIFY
                        ?.info(
                            'طُلبت دورة من الخادم — النتيجة الفعلية في تبويب القرارات'
                        );
                }
            );
        }

        const status =
            document.getElementById(
                'btn-get-status'
            );

        if (
            status
        ) {

            status.addEventListener(
                'click',
                () => {

                    const metrics =
                        window.SOVEREIGN_METRICS
                            ?.getMetrics();

                    console.log(
                        '📊 Runtime Status',
                        metrics
                    );

                    window.SOVEREIGN_NOTIFY
                        ?.info(
                            'Runtime Status Logged'
                        );
                }
            );
        }
    }

    /* ========================================================
       COUNTERS
    ======================================================== */

    bindCounters() {

        const commandInput =
            document.getElementById(
                'sir-command-input'
            );

        const commandCounter =
            document.getElementById(
                'sir-command-count'
            );

        if (
            commandInput &&
            commandCounter
        ) {

            commandInput.addEventListener(
                'input',
                () => {

                    commandCounter.textContent =
                        commandInput.value.length;
                }
            );
        }
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_INTERFACE =
    new SovereignInterfaceRuntime();
