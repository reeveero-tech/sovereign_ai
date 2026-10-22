/* ============================================================
   Sovereign AI — notification-runtime.js
   الإصدار: 5.0.0
   نظام الإشعارات السيادي
   ============================================================ */

class SovereignNotificationRuntime {

    constructor() {

        this.notifications = [];

        this.container = null;

        console.log(
            '🔔 Notification Runtime Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.createContainer();
    }

    /* ========================================================
       CONTAINER
    ======================================================== */

    createContainer() {

        this.container =
            document.createElement('div');

        this.container.id =
            'sovereign-notifications';

        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            gap: 12px;
            pointer-events: none;
        `;

        document.body.appendChild(
            this.container
        );
    }

    /* ========================================================
       SHOW
    ======================================================== */

    show(
        message,
        type = 'info',
        duration = 4000
    ) {

        /* R-715: منع تكدّس الإشعارات فوق الأزرار —
           (١) لا تكرار لنفس الرسالة وهي ظاهرة،
           (٢) حد أقصى للظاهر في نفس الوقت،
           (٣) النقر يغلق الإشعار فورًا. */

        const key = `${type}::${message}`;

        const existing = [...this.container.children]
            .find(el => el.dataset && el.dataset.key === key);

        if (existing) return;

        while (this.container.children.length >= 3) {
            this.container.firstElementChild.remove();
        }

        const notification =
            document.createElement('div');

        notification.dataset.key = key;

        notification.title = 'انقر للإغلاق';

        notification.addEventListener(
            'click',
            () => this.hide(notification)
        );

        notification.className =
            `
            sovereign-notification
            ${type}
            glass
            holo-glow
            `;

        notification.style.cssText = `
            min-width: 280px;
            max-width: 380px;
            padding: 14px 18px;
            border-radius: 16px;
            backdrop-filter: blur(20px);
            color: white;
            font-size: 14px;
            line-height: 1.6;
            pointer-events: auto;
            cursor: pointer;
            opacity: 0;
            transform:
                translateY(-20px)
                scale(0.95);
            transition:
                all 0.45s ease;
            border:
                1px solid
                rgba(255,255,255,0.08);
            background:
                rgba(8,12,24,0.75);
            box-shadow:
                0 0 30px
                rgba(79,209,197,0.15);
        `;

        notification.innerHTML = `
            <div style="
                display:flex;
                align-items:center;
                gap:12px;
            ">
                <div style="
                    font-size:18px;
                ">
                    ${this.getIcon(type)}
                </div>

                <div class="sovereign-notification-text" style="
                    flex:1;
                "></div>
            </div>
        `;

        /* R-715: نص الرسالة كنص لا HTML (قد يحمل نصًا من الخادم) */
        notification
            .querySelector('.sovereign-notification-text')
            .textContent = String(message);

        this.container.appendChild(
            notification
        );

        requestAnimationFrame(() => {

            notification.style.opacity = '1';

            notification.style.transform =
                `
                translateY(0)
                scale(1)
                `;
        });

        setTimeout(() => {

            this.hide(notification);

        }, duration);

        this.notifications.push({
            message,
            type,
            timestamp:
                Date.now()
        });

        this.cinematicReaction(type);
    }

    /* ========================================================
       HIDE
    ======================================================== */

    hide(notification) {

        if (notification.dataset.hiding) return;

        notification.dataset.hiding = '1';

        /* R-715: لا يُحسب الإشعار المختفي في منع التكرار */
        delete notification.dataset.key;

        notification.style.opacity = '0';

        notification.style.transform =
            `
            translateY(-10px)
            scale(0.96)
            `;

        setTimeout(() => {

            notification.remove();

        }, 400);
    }

    /* ========================================================
       ICONS
    ======================================================== */

    getIcon(type) {

        switch (type) {

            case 'success':
                return '✅';

            case 'warning':
                return '⚠️';

            case 'error':
                return '❌';

            case 'ai':
                return '🧠';

            default:
                return 'ℹ️';
        }
    }

    /* ========================================================
       CINEMATIC
    ======================================================== */

    cinematicReaction(type) {

        if (
            !window.SOVEREIGN_CINEMA
        ) return;

        switch (type) {

            case 'success':

                window.SOVEREIGN_CINEMA
                    .createMoment(
                        'success'
                    );

                break;

            case 'warning':

                window.SOVEREIGN_CINEMA
                    .enterScene(
                        'thinking'
                    );

                break;

            case 'error':

                window.SOVEREIGN_CINEMA
                    .enterScene(
                        'critical'
                    );

                break;

            case 'ai':

                window.SOVEREIGN_CINEMA
                    .pulse(1.2);

                break;
        }
    }

    /* ========================================================
       QUICK HELPERS
    ======================================================== */

    success(message) {

        this.show(
            message,
            'success'
        );
    }

    warning(message) {

        this.show(
            message,
            'warning'
        );
    }

    error(message) {

        this.show(
            message,
            'error'
        );
    }

    ai(message) {

        this.show(
            message,
            'ai'
        );
    }

    info(message) {

        this.show(
            message,
            'info'
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_NOTIFY =
    new SovereignNotificationRuntime();
