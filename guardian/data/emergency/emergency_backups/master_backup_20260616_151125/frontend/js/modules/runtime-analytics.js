/* ============================================================
   Sovereign AI — runtime-analytics.js
   الإصدار: 7.2.0 (Runtime Telemetry Service)
   
   الوظيفة: 
     - جمع وتحليل بيانات Runtime بشكل دوري (Telemetry Collector)
     - تخزين السجلات التاريخية (Historical Storage)
     - معالجة وتحليل البيانات (Analytics Processor)
     - إنشاء التقارير (Report Engine)
     - بث البيانات عبر Bus (Telemetry Stream)
     - تصدير البيانات (Export Manager)
     
   المبادئ:
     - Analytics هو "قلب الـ Runtime Observability"
     - يعتمد على Access Layer للوصول إلى الأنظمة الأخرى
     - يبث البيانات عبر Bus لتغذية Intelligence, Diagnostics, Health Matrix
     
   مستقبلاً (المرحلة القادمة):
     ✅ Consolidation of telemetry standards
     ✅ Service Contracts between services
     ✅ Runtime Interfaces documentation
     ✅ Unified Message Schema
     ✅ Runtime Profiling
     
   التقسيم المستقبلي للملف:
     - TelemetryCollector (captureAnalytics)
     - AnalyticsProcessor (calculateStabilityScore)
     - ReportEngine (generateReport)
     - TelemetryStream (bus publishing)
     - ExportManager (exportAnalytics)
   ============================================================ */

class SovereignRuntimeAnalytics {

    constructor() {

        this.records = [];

        this.maxRecords = 500;

        // Cache for access layer
        this._access = null;

        console.log(
            '📈 Runtime Analytics Initialized (Telemetry Service Ready)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER (Runtime Access Layer)
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Analytics connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.startAnalytics();
        this.bindSignals();
        this.emitReady();
    }

    /* ========================================================
       EMIT READY (للـ Runtime Observability)
    ======================================================== */
    emitReady() {
        const access = this.access;
        const bus = access?.bus?.();
        
        if (bus) {
            bus.publish('analytics:ready', {
                timestamp: Date.now(),
                maxRecords: this.maxRecords,
                source: 'runtime-analytics',
                version: '7.2.0'
            });
        }
        
        window.SOVEREIGN_EVENTS?.emit('analytics:ready', {
            timestamp: Date.now()
        });
    }

    /* ========================================================
       START ANALYTICS (Telemetry Scheduler)
    ======================================================== */
    startAnalytics() {
        const access = this.access;
        let scheduler = access?.scheduler?.();
        
        if (!scheduler) {
            scheduler = access?.legacy?.('scheduler');
        }

        if (!scheduler?.registerTask) {
            console.warn('⚠️ Scheduler not available. Analytics using fallback interval.');
            setInterval(() => this.captureAnalytics(), 6000);
            return;
        }

        scheduler.registerTask(
            'runtime-analytics',
            () => this.captureAnalytics(),
            6000
        );
    }

    /* ========================================================
       CAPTURE ANALYTICS (Telemetry Collector)
    ======================================================== */
    captureAnalytics() {
        const access = this.access;
        const startTime = performance.now();
        
        // Collect data via Access Layer
        const metrics = access?.legacy?.('metrics')?.getMetrics?.();
        const kernel = access?.kernel?.()?.getStatus?.();
        const intelligence = access?.intelligence?.()?.getStatus?.();
        const power = access?.legacy?.('power')?.getStatus?.();
        const healthMatrix = access?.health?.()?.getStatus?.();

        // ✅ FIX 1: Correct overallHealth property
        const overallHealth = healthMatrix?.globalHealth ?? kernel?.health ?? 0;

        const snapshot = {
            timestamp: Date.now(),
            fps: metrics?.fps || 0,
            cycles: metrics?.cycles || 0,
            health: kernel?.health || 0,
            runtimeState: kernel?.state || 'unknown',
            intelligenceState: intelligence?.state || 'unknown',
            powerMode: power?.mode || 'balanced',
            overallHealth: overallHealth,
            captureDurationMs: parseFloat((performance.now() - startTime).toFixed(2))
        };

        // Storage
        this.records.push(snapshot);

        if (this.records.length > this.maxRecords) {
            const removed = this.records.shift();
            console.log(`📊 Analytics: Oldest record removed (${removed.timestamp})`);
        }

        // ✅ Cache with proper fallback
        const cache = access?.cache?.();
        if (cache?.set) {
            cache.set(`analytics-${snapshot.timestamp}`, snapshot, 300000);
        } else {
            // Fallback to legacy cache
            window.SOVEREIGN_CACHE?.set(`analytics-${snapshot.timestamp}`, snapshot, 300000);
        }

        // ✅ Bus Telemetry Stream
        const bus = access?.bus?.();
        if (bus) {
            bus.publish('analytics:capture', {
                snapshot,
                recordsCount: this.records.length,
                timestamp: Date.now(),
                source: 'runtime-analytics'
            });
        }
        
        // Critical alerts
        if (snapshot.health < 50 || snapshot.fps < 30) {
            bus?.publish('analytics:critical', {
                snapshot,
                reason: snapshot.health < 50 ? 'low_health' : 'low_fps',
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       SIGNALS (Event Binding)
    ======================================================== */
    bindSignals() {
        const access = this.access;
        const events = access?.events?.();
        
        if (events) {
            events.on('runtime:intelligence_changed', ({ current }) => {
                console.log(`📊 Intelligence Shift: ${current}`);
                const bus = access?.bus?.();
                bus?.publish('analytics:intelligence_shift', {
                    state: current,
                    timestamp: Date.now()
                });
            });

            events.on('kernel:degraded', () => {
                this.captureAnalytics();
            });
            
            events.on('analytics:export', () => {
                this.exportAnalytics();
            });
        } else {
            // Fallback to legacy events
            window.SOVEREIGN_EVENTS?.on('runtime:intelligence_changed', ({ current }) => {
                console.log(`📊 Intelligence Shift: ${current}`);
            });
            window.SOVEREIGN_EVENTS?.on('kernel:degraded', () => {
                this.captureAnalytics();
            });
        }
        
        // ✅ Bus-first subscription (FIX 2: Correct meta handling)
        const bus = access?.bus?.();
        if (bus) {
            bus.subscribe('analytics:capture:now', () => {
                console.log('📡 Manual analytics capture requested via Bus');
                this.captureAnalytics();
            });
            
            // ✅ FIX 2: Use message.id instead of meta?.messageId
            bus.subscribe('analytics:get:report', (message) => {
                const report = this.generateReport();
                bus.publish('analytics:report:response', {
                    report,
                    requestId: message?.id,
                    timestamp: Date.now()
                });
            });
        }
    }

    /* ========================================================
       GENERATE REPORT (Report Engine)
    ======================================================== */
    generateReport() {
        if (!this.records.length) {
            return null;
        }

        const latest = this.records[this.records.length - 1];
        
        const averageFPS = parseFloat(
            (this.records.reduce((sum, item) => sum + item.fps, 0) / this.records.length).toFixed(2)
        );
        
        const averageHealth = parseFloat(
            (this.records.reduce((sum, item) => sum + item.health, 0) / this.records.length).toFixed(2)
        );
        
        const stabilityScore = this.calculateStabilityScore();
        
        let minFPS = Infinity, maxFPS = -Infinity;
        let minHealth = Infinity, maxHealth = -Infinity;
        
        for (const record of this.records) {
            if (record.fps < minFPS) minFPS = record.fps;
            if (record.fps > maxFPS) maxFPS = record.fps;
            if (record.health < minHealth) minHealth = record.health;
            if (record.health > maxHealth) maxHealth = record.health;
        }

        return {
            recordsCount: this.records.length,
            maxRecords: this.maxRecords,
            averageFPS,
            averageHealth,
            stabilityScore,
            minFPS: minFPS === Infinity ? 0 : minFPS,
            maxFPS: maxFPS === -Infinity ? 0 : maxFPS,
            minHealth: minHealth === Infinity ? 0 : minHealth,
            maxHealth: maxHealth === -Infinity ? 0 : maxHealth,
            latest,
            timeRange: {
                from: this.records[0]?.timestamp,
                to: latest?.timestamp
            },
            generatedAt: Date.now()
        };
    }
    
    /* ========================================================
       CALCULATE STABILITY SCORE (Analytics Processor)
    ======================================================== */
    calculateStabilityScore() {
        if (this.records.length < 2) return 100;
        
        let fpsVariance = 0;
        let healthVariance = 0;
        const avgFPS = this.records.reduce((s, r) => s + r.fps, 0) / this.records.length;
        const avgHealth = this.records.reduce((s, r) => s + r.health, 0) / this.records.length;
        
        for (const record of this.records) {
            fpsVariance += Math.pow(record.fps - avgFPS, 2);
            healthVariance += Math.pow(record.health - avgHealth, 2);
        }
        
        fpsVariance = Math.sqrt(fpsVariance / this.records.length);
        healthVariance = Math.sqrt(healthVariance / this.records.length);
        
        const fpsStability = Math.max(0, 100 - (fpsVariance * 2));
        const healthStability = Math.max(0, 100 - (healthVariance * 1.5));
        
        return parseFloat(((fpsStability + healthStability) / 2).toFixed(2));
    }

    /* ========================================================
       EXPORT ANALYTICS (Export Manager)
    ======================================================== */
    exportAnalytics() {
        const report = this.generateReport();
        
        const exportData = {
            exportedAt: Date.now(),
            version: '7.2.0',
            report,
            fullRecords: this.records,
            systemInfo: {
                userAgent: navigator.userAgent,
                platform: navigator.platform
            }
        };
        
        const blob = new Blob(
            [JSON.stringify(exportData, null, 2)],
            { type: 'application/json' }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `sovereign-analytics-${Date.now()}.json`;
        link.click();
        URL.revokeObjectURL(url);

        const notify = this.access?.notify?.();
        notify?.success?.('Analytics Exported Successfully');
        
        const bus = this.access?.bus?.();
        bus?.publish('analytics:exported', {
            recordsCount: this.records.length,
            timestamp: Date.now()
        });
    }
    
    /* ========================================================
       OPERATIONAL APIS
    ======================================================== */
    clearAnalytics() {
        this.records = [];
        console.log('🧹 Analytics records cleared');
        
        const bus = this.access?.bus?.();
        bus?.publish('analytics:cleared', {
            timestamp: Date.now(),
            source: 'runtime-analytics'
        });
    }
    
    getTimeRange(fromTimestamp, toTimestamp) {
        return this.records.filter(r => 
            r.timestamp >= fromTimestamp && 
            r.timestamp <= toTimestamp
        );
    }

    /* ========================================================
       STATUS (Telemetry Health)
    ======================================================== */
    getStatus() {
        const lastRecord = this.records[this.records.length - 1];
        
        return {
            records: this.records.length,
            maxRecords: this.maxRecords,
            lastRecordTimestamp: lastRecord?.timestamp || null,
            lastRecordHealth: lastRecord?.health || null,
            lastRecordFPS: lastRecord?.fps || null,
            accessLayerConnected: !!this._access,
            percentFull: (this.records.length / this.maxRecords) * 100,
            timestamp: Date.now()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
   - Legacy Global: للتوافق مع الأنظمة القديمة
   - Unified Registry: للتسجيل في النواة الموحدة
============================================================ */

const sovereignAnalytics = new SovereignRuntimeAnalytics();

window.SOVEREIGN_ANALYTICS = sovereignAnalytics;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('analytics', sovereignAnalytics);
    console.log('✅ Runtime Analytics registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Analytics registered as legacy global only.');
}

window.SOVEREIGN_EVENTS?.emit('analytics:ready', {
    timestamp: Date.now(),
    status: sovereignAnalytics.getStatus()
});
