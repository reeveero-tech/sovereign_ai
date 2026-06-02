/* ============================================================
   Sovereign AI — neural-memory.js
   الإصدار: 5.0.0
   الذاكرة العصبية السيادية
   ============================================================ */

class SovereignNeuralMemory {

    constructor() {

        this.shortTermMemory = [];

        this.longTermMemory = [];

        this.maxShortTerm = 25;

        this.maxLongTerm = 200;

        console.log(
            '🧠 Neural Memory Initialized'
        );

        this.restoreMemory();
    }

    /* ========================================================
       SAVE INTERACTION
    ======================================================== */

    saveInteraction(
        user,
        ai
    ) {

        const memory = {

            id:
                crypto.randomUUID(),

            user,

            ai,

            timestamp:
                Date.now()
        };

        this.shortTermMemory.push(
            memory
        );

        if (
            this.shortTermMemory.length >
            this.maxShortTerm
        ) {

            const transferred =
                this.shortTermMemory.shift();

            this.longTermMemory.push(
                transferred
            );
        }

        if (
            this.longTermMemory.length >
            this.maxLongTerm
        ) {

            this.longTermMemory.shift();
        }

        this.persistMemory();

        this.emitMemoryUpdate();
    }

    /* ========================================================
       GET CONTEXT
    ======================================================== */

    getContext(
        limit = 10
    ) {

        return this.shortTermMemory
            .slice(-limit);
    }

    /* ========================================================
       SEARCH MEMORY
    ======================================================== */

    search(query) {

        const allMemory = [

            ...this.shortTermMemory,
            ...this.longTermMemory
        ];

        return allMemory.filter(
            item => {

                const text =
                    `
                    ${item.user}
                    ${item.ai}
                    `
                    .toLowerCase();

                return text.includes(
                    query.toLowerCase()
                );
            }
        );
    }

    /* ========================================================
       PERSIST MEMORY
    ======================================================== */

    persistMemory() {

        localStorage.setItem(
            'sovereign_memory_short',
            JSON.stringify(
                this.shortTermMemory
            )
        );

        localStorage.setItem(
            'sovereign_memory_long',
            JSON.stringify(
                this.longTermMemory
            )
        );
    }

    /* ========================================================
       RESTORE MEMORY
    ======================================================== */

    restoreMemory() {

        try {

            const shortMemory =
                localStorage.getItem(
                    'sovereign_memory_short'
                );

            const longMemory =
                localStorage.getItem(
                    'sovereign_memory_long'
                );

            if (shortMemory) {

                this.shortTermMemory =
                    JSON.parse(shortMemory);
            }

            if (longMemory) {

                this.longTermMemory =
                    JSON.parse(longMemory);
            }

        } catch (error) {

            console.error(
                'Memory Restore Failed',
                error
            );
        }
    }

    /* ========================================================
       CLEAR MEMORY
    ======================================================== */

    clearMemory() {

        this.shortTermMemory = [];

        this.longTermMemory = [];

        localStorage.removeItem(
            'sovereign_memory_short'
        );

        localStorage.removeItem(
            'sovereign_memory_long'
        );

        console.log(
            '🧹 Memory Cleared'
        );
    }

    /* ========================================================
       EMIT UPDATE
    ======================================================== */

    emitMemoryUpdate() {

        if (
            window.SOVEREIGN_CORE
        ) {

            window.SOVEREIGN_CORE.emit(
                'memory:updated',
                {
                    short:
                        this.shortTermMemory.length,

                    long:
                        this.longTermMemory.length
                }
            );
        }
    }

    /* ========================================================
       GET STATS
    ======================================================== */

    getStats() {

        return {

            shortTerm:
                this.shortTermMemory.length,

            longTerm:
                this.longTermMemory.length
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_MEMORY =
    new SovereignNeuralMemory();
