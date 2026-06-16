/* ============================================================
   Sovereign AI — runtime-cognitive-memory.js
   الإصدار: 10.0.0
   الذاكرة الإدراكية السيادية للـ Runtime
   ============================================================ */

class SovereignRuntimeCognitiveMemory {

    constructor() {

        /* =========================================
           MEMORY LAYERS (محسن)
        ========================================= */

        this.shortTerm = [];
        this.longTerm = [];
        this.anomalyMemory = [];
        this.behavioralPatterns = [];
        this.episodicMemory = [];      // ذاكرة الأحداث الهامة (من 2200)
        this.semanticMemory = new Map(); // ذاكرة المعاني والعلاقات (من 2200)

        /* =========================================
           LIMITS
        ========================================= */

        this.shortTermLimit = 200;      // زيادة
        this.longTermLimit = 5000;      // زيادة كبيرة
        this.patternLimit = 1000;       // زيادة
        this.episodicLimit = 500;

        /* =========================================
           MEMORY COMPRESSION (ضغط ذكي - من 2200)
        ========================================= */

        this.compression = {
            enabled: true,
            threshold: 0.7,           // ضغط عندما تتجاوز 70% من السعة
            algorithms: {
                'pattern_merging': 0,
                'semantic_clustering': 0,
                'temporal_bucketing': 0
            },
            savedBytes: 0
        };

        /* =========================================
           DEEP PATTERN LEARNING (تعلم عميق - من 2200)
        ========================================= */

        this.patternLearning = {
            enabled: true,
            neuralWeights: new Map(),     // أوزان عصبية للأنماط
            patternConfidence: new Map(), // ثقة كل نمط
            learningRate: 0.1,
            epochs: 0
        };

        /* =========================================
           MEMORY-BASED PREDICTION (تنبؤ من الذاكرة - من 2200)
        ========================================= */

        this.memoryPrediction = {
            enabled: true,
            accuracy: 0,
            predictions: [],              // تنبؤات مبنية على الذاكرة
            lastPredictionTime: null
        };

        /* =========================================
           BEHAVIORAL REPLAY (إعادة تشغيل سلوكي - من 2200)
        ========================================= */

        this.behavioralReplay = {
            enabled: true,
            replayQueue: [],
            replaySpeed: 100,            // مللي ثانية لكل حدث
            learningFromReplay: true,
            replaysExecuted: 0
        };

        /* =========================================
           CROSS-DOMAIN MEMORY (ذاكرة مشتركة - من 2200)
        ========================================= */

        this.crossDomainMemory = new Map();  // domain → shared memories
        this.memoryQueries = new Map();      // تتبع استعلامات الذاكرة

        /* =========================================
           INDEXES (محسن)
        ========================================= */

        this.indexes = {
            anomalies: new Map(),
            predictions: new Map(),
            transitions: new Map(),
            domains: new Map(),
            patterns: new Map(),           // فهرس الأنماط
            temporal: new Map()            // فهرس زمني (من 2200)
        };

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {
            memories: 0,
            anomalies: 0,
            patterns: 0,
            recalls: 0,
            consolidations: 0,
            compressed: 0,
            predictionsFromMemory: 0,
            accuratePredictions: 0,
            replaysProcessed: 0,
            crossDomainHits: 0,
            semanticQueries: 0
        };

        console.log('🧠 Runtime Cognitive Memory Initialized (2200 Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindCognition();
        this.bindDomainEvents();
        this.startConsolidationLoop();
        this.startCompressionLoop();
        this.startBehavioralReplay();
        this.startMemoryPredictionLoop();
        this.publishReady();
    }

    /* ========================================================
       DOMAIN EVENTS (لذاكرة مشتركة)
    ======================================================== */

    bindDomainEvents() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:domain:isolated', ({ domain, reason }) => {
            this.storeDomainMemory(domain, 'isolation', { reason });
        });

        bus.subscribe('runtime:domain:recovered', ({ domain }) => {
            this.storeDomainMemory(domain, 'recovery', { timestamp: Date.now() });
        });
    }

    /* ========================================================
       COGNITION (محسن)
    ======================================================== */

    bindCognition() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:cognition:prediction', payload => {
            this.storePrediction(payload);
            this.learnFromPrediction(payload);
        });

        bus.subscribe('runtime:cognition:anomaly', payload => {
            this.storeAnomaly(payload);
            this.detectPatternFromAnomaly(payload);
        });

        bus.subscribe('runtime:mode:transition', payload => {
            this.storeTransition(payload);
            this.storeEpisodicMemory('mode_transition', payload);
        });

        bus.subscribe('telemetry:event', payload => {
            this.storeTelemetry(payload);
        });

        bus.subscribe('runtime:cognition:action', payload => {
            this.storeEpisodicMemory('cognitive_action', payload);
        });
    }

    /* ========================================================
       EPISODIC MEMORY (ذاكرة الأحداث الهامة - من 2200)
    ======================================================== */

    storeEpisodicMemory(eventType, data, importance = 1) {

        const entry = {
            id: crypto.randomUUID(),
            type: eventType,
            data,
            importance,
            timestamp: Date.now()
        };

        this.episodicMemory.push(entry);

        if (this.episodicMemory.length > this.episodicLimit) {
            // حذف أقل الأحداث أهمية
            this.episodicMemory.sort((a, b) => a.importance - b.importance);
            this.episodicMemory.shift();
        }

        // فهرسة زمنية
        const timeKey = new Date(entry.timestamp).toISOString().slice(0, 10); // يوم
        if (!this.indexes.temporal.has(timeKey)) {
            this.indexes.temporal.set(timeKey, []);
        }
        this.indexes.temporal.get(timeKey).push(entry.id);
    }

    /* ========================================================
       SEMANTIC MEMORY (ذاكرة المعاني - من 2200)
    ======================================================== */

    storeSemanticMemory(key, value, confidence = 100) {

        this.semanticMemory.set(key, {
            value,
            confidence,
            updatedAt: Date.now(),
            accessCount: 0
        });

        this.metrics.semanticQueries++;
    }

    querySemanticMemory(key) {

        const memory = this.semanticMemory.get(key);
        if (memory) {
            memory.accessCount++;
            return memory.value;
        }
        return null;
    }

    /* ========================================================
       DEEP PATTERN LEARNING (تعلم عميق - من 2200)
    ======================================================== */

    learnPattern(pattern, features) {

        if (!this.patternLearning.enabled) return;

        const patternKey = JSON.stringify(pattern);
        
        if (!this.patternLearning.neuralWeights.has(patternKey)) {
            this.patternLearning.neuralWeights.set(patternKey, {
                weights: features.map(() => Math.random() * 2 - 1),
                bias: Math.random(),
                confidence: 0
            });
        }

        const weights = this.patternLearning.neuralWeights.get(patternKey);
        
        // تحديث الأوزان (تعلم بسيط)
        for (let i = 0; i < weights.weights.length; i++) {
            weights.weights[i] += this.patternLearning.learningRate * (features[i] - weights.weights[i]);
        }
        
        weights.confidence = Math.min(100, weights.confidence + 5);
        this.patternLearning.patternConfidence.set(patternKey, weights.confidence);
    }

    predictPattern(currentFeatures) {

        let bestMatch = null;
        let bestScore = 0;

        for (const [patternKey, weights] of this.patternLearning.neuralWeights) {
            let score = weights.bias;
            for (let i = 0; i < Math.min(weights.weights.length, currentFeatures.length); i++) {
                score += weights.weights[i] * currentFeatures[i];
            }
            score = 1 / (1 + Math.exp(-score)); // sigmoid
            
            if (score > bestScore) {
                bestScore = score;
                bestMatch = patternKey;
            }
        }

        return bestMatch ? JSON.parse(bestMatch) : null;
    }

    /* ========================================================
       MEMORY-BASED PREDICTION (تنبؤ من الذاكرة - من 2200)
    ======================================================== */

    startMemoryPredictionLoop() {

        this._predictionInterval = setInterval(() => {
            if (!this.memoryPrediction.enabled) return;
            this.generateMemoryBasedPredictions();
        }, 15000);
    }

    generateMemoryBasedPredictions() {

        // البحث عن أنماط متكررة في الذاكرة طويلة المدى
        const recentMemories = this.longTerm.slice(-50);
        const patternFrequency = new Map();

        for (const memory of recentMemories) {
            if (memory.type === 'transition') {
                const key = `${memory.payload.previous}→${memory.payload.current}`;
                patternFrequency.set(key, (patternFrequency.get(key) || 0) + 1);
            }
        }

        // التنبؤ بالتحول التالي بناءً على الأنماط المتكررة
        for (const [pattern, frequency] of patternFrequency) {
            if (frequency >= 3) {
                const [from, to] = pattern.split('→');
                const prediction = {
                    type: 'memory_based_transition',
                    from,
                    predictedTo: to,
                    confidence: Math.min(100, frequency * 20),
                    basedOnMemory: true
                };
                
                this.memoryPrediction.predictions.push({
                    ...prediction,
                    timestamp: Date.now()
                });
                
                this.metrics.predictionsFromMemory++;
                
                // نشر التنبؤ
                const bus = window.SOVEREIGN_ACCESS?.bus?.();
                if (bus && typeof bus.publishWithoutMiddleware === 'function') {
                    bus.publishWithoutMiddleware('runtime:cognitive:memory-prediction', prediction);
                }
            }
        }

        this.memoryPrediction.lastPredictionTime = Date.now();
        
        // تنظيف التنبؤات القديمة
        if (this.memoryPrediction.predictions.length > 100) {
            this.memoryPrediction.predictions = this.memoryPrediction.predictions.slice(-50);
        }
    }

    /* ========================================================
       BEHAVIORAL REPLAY (إعادة تشغيل سلوكي - من 2200)
    ======================================================== */

    startBehavioralReplay() {

        this._replayInterval = setInterval(() => {
            if (!this.behavioralReplay.enabled) return;
            this.processBehavioralReplay();
        }, 5000);
    }

    processBehavioralReplay() {

        if (this.behavioralReplay.replayQueue.length === 0) {
            // إضافة أحداث هامة إلى قائمة إعادة التشغيل
            const importantEvents = this.episodicMemory
                .filter(e => e.importance > 5)
                .slice(-10);
            
            this.behavioralReplay.replayQueue.push(...importantEvents);
        }

        if (this.behavioralReplay.replayQueue.length > 0) {
            const event = this.behavioralReplay.replayQueue.shift();
            this.replayEvent(event);
            this.metrics.replaysProcessed++;
        }
    }

    replayEvent(event) {

        console.log(`🧠 Replaying cognitive event: ${event.type} (importance: ${event.importance})`);

        if (this.behavioralReplay.learningFromReplay) {
            // تعلم من إعادة التشغيل
            this.learnFromEvent(event);
        }

        // نشر حدث إعادة التشغيل
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognitive:replay', {
                event: event.type,
                data: event.data,
                timestamp: Date.now()
            });
        }
    }

    learnFromEvent(event) {

        // تعلم من الأحداث المعاد تشغيلها
        if (event.type === 'mode_transition') {
            const key = `${event.data.previous}→${event.data.current}`;
            const freq = this.indexes.transitions.get(key)?.length || 0;
            if (freq > 2) {
                this.storeSemanticMemory(`transition_pattern_${key}`, { confidence: 80 }, 80);
            }
        }
    }

    /* ========================================================
       MEMORY COMPRESSION (ضغط ذكي - من 2200)
    ======================================================== */

    startCompressionLoop() {

        this._compressionInterval = setInterval(() => {
            if (!this.compression.enabled) return;
            this.compressMemory();
        }, 60000);
    }

    compressMemory() {

        const shortTermUsage = this.shortTerm.length / this.shortTermLimit;
        const longTermUsage = this.longTerm.length / this.longTermLimit;

        if (shortTermUsage > this.compression.threshold) {
            this.compressShortTermMemory();
        }

        if (longTermUsage > this.compression.threshold) {
            this.compressLongTermMemory();
        }
    }

    compressShortTermMemory() {

        // دمج الأنماط المتشابهة
        const patterns = new Map();

        for (const memory of this.shortTerm) {
            if (memory.type === 'telemetry') {
                const key = `${memory.payload.type}_${Math.floor(memory.timestamp / 10000)}`; // نافذة 10 ثوانٍ
                if (!patterns.has(key)) {
                    patterns.set(key, []);
                }
                patterns.get(key).push(memory);
            }
        }

        // استبدال المجموعات بملخص
        for (const [key, group] of patterns) {
            if (group.length > 5) {
                const summary = {
                    type: 'compressed_telemetry',
                    count: group.length,
                    startTime: group[0].timestamp,
                    endTime: group[group.length - 1].timestamp,
                    compressedAt: Date.now()
                };
                
                this.shortTerm.push({
                    id: crypto.randomUUID(),
                    type: 'compressed',
                    payload: summary,
                    timestamp: Date.now()
                });
                
                // حذف المجموعة الأصلية
                for (const mem of group) {
                    const index = this.shortTerm.indexOf(mem);
                    if (index !== -1) this.shortTerm.splice(index, 1);
                }
                
                this.compression.algorithms.pattern_merging++;
                this.metrics.compressed++;
            }
        }
    }

    compressLongTermMemory() {

        // ضغط الذاكرة طويلة المدى عن طريق التجميع الزمني
        const timeBuckets = new Map();

        for (const memory of this.longTerm) {
            const bucketKey = Math.floor(memory.timestamp / 3600000); // ساعة واحدة
            if (!timeBuckets.has(bucketKey)) {
                timeBuckets.set(bucketKey, []);
            }
            timeBuckets.get(bucketKey).push(memory);
        }

        // لا نضغط الذاكرة القديمة جداً، نحذفها فقط
        const oneWeekAgo = Date.now() - 7 * 24 * 3600000;
        this.longTerm = this.longTerm.filter(m => m.timestamp > oneWeekAgo);
    }

    /* ========================================================
       CROSS-DOMAIN MEMORY (ذاكرة مشتركة - من 2200)
    ======================================================== */

    storeDomainMemory(domain, eventType, data) {

        if (!this.crossDomainMemory.has(domain)) {
            this.crossDomainMemory.set(domain, []);
        }

        const memory = {
            eventType,
            data,
            timestamp: Date.now()
        };

        this.crossDomainMemory.get(domain).push(memory);

        // الاحتفاظ بآخر 100 حدث لكل domain
        if (this.crossDomainMemory.get(domain).length > 100) {
            this.crossDomainMemory.get(domain).shift();
        }
    }

    queryDomainMemory(domain, eventType = null, limit = 20) {

        const memories = this.crossDomainMemory.get(domain) || [];
        
        let filtered = memories;
        if (eventType) {
            filtered = memories.filter(m => m.eventType === eventType);
        }
        
        this.metrics.crossDomainHits++;
        
        return filtered.slice(-limit);
    }

    /* ========================================================
       PATTERN DETECTION (محسن)
    ======================================================== */

    detectBehavioralPattern(entry = {}) {

        // تحليل أكثر عمقاً
        const pattern = {
            type: entry.type,
            timestamp: Date.now(),
            context: entry.payload?.context || 'unknown'
        };

        this.behavioralPatterns.push(pattern);
        this.metrics.patterns++;

        // كشف الأنماط المتكررة
        const recentPatterns = this.behavioralPatterns.slice(-20);
        const patternFrequency = new Map();

        for (const p of recentPatterns) {
            const key = `${p.type}_${p.context}`;
            patternFrequency.set(key, (patternFrequency.get(key) || 0) + 1);
        }

        for (const [key, freq] of patternFrequency) {
            if (freq >= 5 && !this.indexes.patterns.has(key)) {
                this.indexes.patterns.set(key, {
                    frequency: freq,
                    firstSeen: recentPatterns[0]?.timestamp,
                    lastSeen: Date.now(),
                    confidence: Math.min(100, freq * 10)
                });
                
                // تعلم النمط
                const [type, context] = key.split('_');
                this.learnPattern({ type, context }, [freq / 10, 0.5]);
            }
        }

        if (this.behavioralPatterns.length > this.patternLimit) {
            this.behavioralPatterns = this.behavioralPatterns.slice(-this.patternLimit);
        }
    }

    detectPatternFromAnomaly(anomalyPayload) {

        const anomaly = anomalyPayload.anomaly;
        if (!anomaly) return;

        // ربط الشذوذ بالأنماط السلوكية السابقة
        const recentPatterns = this.behavioralPatterns.slice(-50);
        const anomalyContext = anomaly.type;

        for (const pattern of recentPatterns) {
            if (pattern.type === anomalyContext) {
                this.storeSemanticMemory(`anomaly_${anomaly.type}_context`, pattern.context, 70);
            }
        }
    }

    learnFromPrediction(predictionPayload) {

        const prediction = predictionPayload.prediction;
        if (!prediction) return;

        // تتبع دقة التنبؤات المستقبلية سيتم في cognition engine
        this.storeSemanticMemory(`prediction_${prediction.type}`, {
            severity: prediction.severity,
            timestamp: Date.now()
        }, 50);
    }

    /* ========================================================
       MEMORY STORAGE (محسن)
    ======================================================== */

    storeMemory(memory = {}) {

        const entry = {
            id: crypto.randomUUID(),
            ...memory,
            timestamp: Date.now()
        };

        this.shortTerm.push(entry);
        this.metrics.memories++;

        if (this.shortTerm.length > this.shortTermLimit) {
            const toConsolidate = this.shortTerm.splice(0, this.shortTermLimit / 2);
            this.longTerm.push(...toConsolidate);
        }
    }

    storePrediction(payload = {}) {
        const prediction = payload.prediction;
        if (!prediction) return;

        this.storeMemory({ type: 'prediction', payload: prediction });
        this.indexMemory('predictions', prediction.type, prediction);
    }

    storeAnomaly(payload = {}) {
        const anomaly = payload.anomaly;
        if (!anomaly) return;

        this.metrics.anomalies++;
        this.anomalyMemory.push({ ...anomaly, rememberedAt: Date.now() });
        this.storeMemory({ type: 'anomaly', payload: anomaly });
        this.indexMemory('anomalies', anomaly.type, anomaly);
        
        // تخزين episodic للشذوذات الهامة
        if (anomaly.severity === 'critical') {
            this.storeEpisodicMemory('critical_anomaly', anomaly, 10);
        }
    }

    storeTransition(payload = {}) {
        this.storeMemory({ type: 'transition', payload });
        this.indexMemory('transitions', payload.current, payload);
        this.storeEpisodicMemory('mode_transition', payload, 7);
    }

    storeTelemetry(payload = {}) {
        const entry = payload.entry;
        if (!entry) return;

        this.storeMemory({ type: 'telemetry', payload: entry });
        this.detectBehavioralPattern(entry);
    }

    /* ========================================================
       INDEXING (محسن)
    ======================================================== */

    indexMemory(indexName, key, value) {
        const index = this.indexes[indexName];
        if (!index) return;

        if (!index.has(key)) {
            index.set(key, []);
        }
        index.get(key).push({ value, timestamp: Date.now() });
    }

    /* ========================================================
       CONSOLIDATION (محسن)
    ======================================================== */

    startConsolidationLoop() {
        this._consolidationInterval = setInterval(() => {
            this.consolidateMemory();
        }, 8000);
    }

    consolidateMemory() {
        if (this.shortTerm.length === 0) return;

        const memories = this.shortTerm.splice(0, Math.min(30, this.shortTerm.length));
        this.longTerm.push(...memories);
        this.metrics.consolidations++;

        if (this.longTerm.length > this.longTermLimit) {
            this.longTerm = this.longTerm.slice(-this.longTermLimit);
        }

        this.publishConsolidation(memories.length);
    }

    /* ========================================================
       RECALL (محسن)
    ======================================================== */

    recall({ type = null, limit = 20, temporalRange = null } = {}) {
        this.metrics.recalls++;

        let memories = [...this.longTerm];

        if (type) {
            memories = memories.filter(memory => memory.type === type);
        }

        if (temporalRange) {
            const { start, end } = temporalRange;
            memories = memories.filter(m => m.timestamp >= start && m.timestamp <= end);
        }

        return memories.slice(-limit);
    }

    quickRecall(type, limit = 5) {
        // استدعاء سريع من shortTerm أولاً
        let results = this.shortTerm.filter(m => m.type === type).slice(-limit);
        if (results.length < limit) {
            results.push(...this.longTerm.filter(m => m.type === type).slice(-(limit - results.length)));
        }
        return results;
    }

    /* ========================================================
       UTILITIES
    ======================================================== */

    getAnomalyHistory(type = null) {
        return type ? this.anomalyMemory.filter(a => a.type === type) : this.anomalyMemory;
    }

    getPredictionHistory(type = null) {
        const index = this.indexes.predictions;
        return type ? (index.get(type) || []) : Object.fromEntries(index);
    }

    getEpisodicMemory(importanceThreshold = 0) {
        return this.episodicMemory.filter(e => e.importance >= importanceThreshold).slice(-100);
    }

    getSemanticMemory() {
        return Object.fromEntries(this.semanticMemory);
    }

    summarizePatterns() {
        const summary = {};
        this.behavioralPatterns.forEach(pattern => {
            summary[pattern.type] = (summary[pattern.type] || 0) + 1;
        });
        return summary;
    }

    getPatternConfidence(patternType) {
        const patternKey = `{"type":"${patternType}","context":"unknown"}`;
        return this.patternLearning.patternConfidence.get(patternKey) || 0;
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishConsolidation(count) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognitive:memory', {
                consolidated: count,
                shortTermSize: this.shortTerm.length,
                longTermSize: this.longTerm.length,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-cognitive-memory:ready', {
                shortTermLimit: this.shortTermLimit,
                longTermLimit: this.longTermLimit,
                compressionEnabled: this.compression.enabled,
                patternLearningEnabled: this.patternLearning.enabled,
                behavioralReplayEnabled: this.behavioralReplay.enabled,
                memoryPredictionEnabled: this.memoryPrediction.enabled,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {
        return {
            shortTerm: this.shortTerm.length,
            longTerm: this.longTerm.length,
            anomalies: this.anomalyMemory.length,
            patterns: this.behavioralPatterns.length,
            episodic: this.episodicMemory.length,
            semantic: this.semanticMemory.size,
            crossDomain: this.crossDomainMemory.size,
            patternConfidence: Array.from(this.patternLearning.patternConfidence.entries()),
            compression: {
                enabled: this.compression.enabled,
                saved: this.compression.savedBytes,
                algorithms: this.compression.algorithms
            },
            memoryPrediction: {
                enabled: this.memoryPrediction.enabled,
                accuracy: this.memoryPrediction.accuracy,
                predictionsCount: this.memoryPrediction.predictions.length
            },
            behavioralReplay: {
                enabled: this.behavioralReplay.enabled,
                replayCount: this.metrics.replaysProcessed,
                queueSize: this.behavioralReplay.replayQueue.length
            },
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._consolidationInterval) {
            clearInterval(this._consolidationInterval);
            this._consolidationInterval = null;
        }

        if (this._compressionInterval) {
            clearInterval(this._compressionInterval);
            this._compressionInterval = null;
        }

        if (this._replayInterval) {
            clearInterval(this._replayInterval);
            this._replayInterval = null;
        }

        if (this._predictionInterval) {
            clearInterval(this._predictionInterval);
            this._predictionInterval = null;
        }

        this.shortTerm = [];
        this.longTerm = [];
        this.anomalyMemory = [];
        this.behavioralPatterns = [];
        this.episodicMemory = [];
        this.semanticMemory.clear();
        this.crossDomainMemory.clear();
        this.indexes.anomalies.clear();
        this.indexes.predictions.clear();
        this.indexes.transitions.clear();
        this.indexes.domains.clear();
        this.indexes.patterns.clear();
        this.indexes.temporal.clear();

        console.log('🧠 Runtime Cognitive Memory Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeCognitiveMemory =
    new SovereignRuntimeCognitiveMemory();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_COGNITIVE_MEMORY =
    sovereignRuntimeCognitiveMemory;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
    window.SOVEREIGN.register('cognitive-memory', sovereignRuntimeCognitiveMemory);
}
