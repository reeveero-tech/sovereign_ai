/* ============================================================
   Sovereign AI — neural-ui-controller.js
   الإصدار: 5.0.0
   المتحكم العصبي بالواجهة
   ============================================================ */

class SovereignNeuralUIController {

    constructor() {

        this.activeTab = 'monitor';

        this.transitioning = false;

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        console.log(
            '🧠 Neural UI Controller Initialized'
        );

        this.bindTabs();

        this.bindButtons();

        this.bindSuggestions();

        this.bindKeyboardShortcuts();
    }

    /* ========================================================
       TABS
    ======================================================== */

    bindTabs() {

        const tabs =
            document.querySelectorAll('.tab');

        tabs.forEach(tab => {

            tab.addEventListener(
                'click',
                () => {

                    const target =
                        tab.dataset.tab;

                    this.switchTab(target);
                }
            );
        });
    }

    /* ========================================================
       SWITCH TAB
    ======================================================== */

    switchTab(tabId) {

        if (
            this.transitioning ||
            this.activeTab === tabId
        ) return;

        this.transitioning = true;

        const tabs =
            document.querySelectorAll('.tab');

        const contents =
            document.querySelectorAll(
                '.tab-content'
            );

        tabs.forEach(tab => {

            tab.classList.toggle(
                'active',
                tab.dataset.tab === tabId
            );
        });

        contents.forEach(content => {

            if (
                content.id === `tab-${tabId}`
            ) {

                content.style.display =
                    'block';

                requestAnimationFrame(() => {

                    content.classList.add(
                        'fade-in'
                    );
                });

            } else {

                content.style.display =
                    'none';

                content.classList.remove(
                    'fade-in'
                );
            }
        });

        this.activeTab = tabId;

        if (
            window.SOVEREIGN_STATE
        ) {

            window.SOVEREIGN_STATE.mergeState(
                'ui',
                {
                    activeTab: tabId
                }
            );
        }

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .createMoment(
                    'success'
                );
        }

        setTimeout(() => {

            this.transitioning = false;

        }, 500);
    }

    /* ========================================================
       BUTTONS
    ======================================================== */

    bindButtons() {

        const buttons =
            document.querySelectorAll(
                '.btn, .quick-btn'
            );

        buttons.forEach(button => {

            button.addEventListener(
                'mouseenter',
                () => {

                    this.activateButton(
                        button
                    );
                }
            );

            button.addEventListener(
                'mouseleave',
                () => {

                    this.deactivateButton(
                        button
                    );
                }
            );
        });
    }

    /* ========================================================
       BUTTON FX
    ======================================================== */

    activateButton(button) {

        button.style.transform =
            'translateY(-2px) scale(1.02)';

        button.style.boxShadow =
            `
            0 0 20px
            rgba(79,209,197,0.35)
            `;
    }

    deactivateButton(button) {

        button.style.transform = '';

        button.style.boxShadow = '';
    }

    /* ========================================================
       SUGGESTIONS
    ======================================================== */

    bindSuggestions() {

        const suggestions =
            document.querySelectorAll(
                '.suggestion-tag'
            );

        suggestions.forEach(tag => {

            tag.addEventListener(
                'click',
                () => {

                    const cmd =
                        tag.dataset.cmd;

                    const input =
                        document.getElementById(
                            'sir-command-input'
                        );

                    if (
                        input &&
                        cmd
                    ) {

                        input.value = cmd;

                        input.focus();

                        if (
                            window.SOVEREIGN_CINEMA
                        ) {

                            window.SOVEREIGN_CINEMA
                                .pulse(1.2);
                        }
                    }
                }
            );
        });
    }

    /* ========================================================
       KEYBOARD SHORTCUTS
    ======================================================== */

    bindKeyboardShortcuts() {

        window.addEventListener(
            'keydown',
            (e) => {

                if (
                    e.ctrlKey &&
                    e.key === '1'
                ) {

                    this.switchTab(
                        'monitor'
                    );
                }

                if (
                    e.ctrlKey &&
                    e.key === '2'
                ) {

                    this.switchTab(
                        'dialogue'
                    );
                }

                if (
                    e.ctrlKey &&
                    e.key === '3'
                ) {

                    this.switchTab(
                        'decisions'
                    );
                }

                if (
                    e.ctrlKey &&
                    e.key === '4'
                ) {

                    this.switchTab(
                        'proposals'
                    );
                }
            }
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_UI =
    new SovereignNeuralUIController();
