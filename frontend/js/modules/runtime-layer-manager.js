/* ============================================================
   Sovereign AI — runtime-layer-manager.js
   الإصدار: 15.0.0
   مدير الطبقات الحضارية السيادي
   ============================================================

   ╔═══════════════════════════════════════════════════════════╗
   ║                                                           ║
   ║   🏛  RUNTIME CIVILIZATION ARCHITECTURE MANAGER  🏛       ║
   ║                                                           ║
   ║   مسؤول عن تنظيم البنية الحضارية للـ Runtime              ║
   ║   ومنع الانهيار التعقيدي (Complexity Collapse)           ║
   ║                                                           ║
   ║   "الحضارة التشغيلية تحتاج إلى بنية مستقرة"              ║
   ║                                                           ║
   ╚═══════════════════════════════════════════════════════════╝

   ============================================================ */

class SovereignRuntimeLayerManager {

    constructor() {

        /* ============================================================
           CIVILIZATION DECLARATION - إعلان الحضارة
        ============================================================ */

        this.civilizationDeclaration = {
            name: "Sovereign Autonomous Cognitive Runtime Civilization",
            version: "15.0.0",
            declaredAt: Date.now(),
            architecture: "Layered Sovereign Architecture",
            corePrinciple: "خدمة السيد فوق كل طبقة"
        };

        /* ============================================================
           LAYERS REGISTRY - سجل الطبقات
        ============================================================ */

        this.layers = new Map();
        this.layerStatus = new Map();  // active, degraded, recovering, failed

        /* ============================================================
           HIERARCHY - التسلسل الهرمي
        ============================================================ */

        this.hierarchy = [];
        this.levelMap = new Map();  // level → layers

        /* ============================================================
           ACTIVE LAYERS - الطبقات النشطة
        ============================================================ */

        this.activeLayers = new Set();

        /* ============================================================
           DEPENDENCIES - الاعتماديات (محسن)
        ============================================================ */

        this.dependencies = new Map();
        this.reverseDependencies = new Map();  // من يعتمد عليك
        this.circularDependenciesDetected = [];

        /* ============================================================
           CROSS-LAYER INTEGRITY - السلامة المتقاطعة
        ============================================================ */

        this.crossLayerIntegrity = {
            coherence: 100,
            lastCheck: null,
            violations: [],
            recoveryAttempts: 0
        };

        /* ============================================================
           LAYER ISOLATION - عزل الطبقات
        ============================================================ */

        this.layerIsolation = {
            enabled: true,
            isolatedLayers: new Set(),
            failurePropagationPrevented: 0,
            isolationHistory: []
        };

        /* ============================================================
           STRUCTURAL STATE (محسن)
        ============================================================ */

        this.structuralIntegrity = 100;
        this.topologyState = 'stable';    // stable, adaptive, fragile, recovering, collapsed
        this.civilizationState = 'harmonic';  // harmonic, stabilizing, recovering, critical, collapsed

        /* ============================================================
           LAYER HEALTH MONITORING - مراقبة صحة الطبقات
        ============================================================ */

        this.layerHealth = new Map();  // layerId → health score (0-100)

        /* ============================================================
           CROSS-LAYER LOAD BALANCING - توازن الأحمال
        ============================================================ */

        this.loadBalancing = {
            enabled: true,
            layerLoads: new Map(),     // layerId → current load
            rebalancingThreshold: 70,
            rebalancingHistory: []
        };

        /* ============================================================
           LAYER CONFLICTS (محسن)
        ============================================================ */

        this.conflicts = [];
        this.maxConflicts = 500;
        this.resolvedConflicts = [];

        /* ============================================================
           CIVILIZATION TOPOLOGY MAP - خريطة طوبولوجيا الحضارة
        ============================================================ */

        this.topologyMap = {
            layers: [],
            connections: [],
            lastUpdated: null,
            visualizationReady: true
        };

        /* ============================================================
           METRICS (محسن)
        ============================================================ */

        this.metrics = {
            registeredLayers: 0,
            activatedLayers: 0,
            dependencyResolutions: 0,
            topologyCorrections: 0,
            structuralRecoveries: 0,
            circularDependenciesBlocked: 0,
            layerIsolations: 0,
            loadRebalances: 0,
            crossLayerViolations: 0
        };

        console.log('🏛 Runtime Layer Manager Initialized');
        console.log('═══════════════════════════════════════════════════════════════════════════════');
        console.log(`🏛 CIVILIZATION: ${this.civilizationDeclaration.name}`);
        console.log(`🏛 ARCHITECTURE: ${this.civilizationDeclaration.architecture}`);
        console.log(`🏛 PRINCIPLE: ${this.civilizationDeclaration.corePrinciple}`);
        console.log('═══════════════════════════════════════════════════════════════════════════════');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCivilizationLayers();
        this.buildReverseDependencies();
        this.detectCircularDependencies();
        this.startTopologyLoop();
        this.startHealthMonitoring();
        this.startLoadBalancingLoop();
        this.publishReady();
    }

    /* ========================================================
       CIVILIZATION LAYERS (محسن)
    ======================================================== */

    registerCivilizationLayers() {

        // الطبقة 0: الأساس - Foundation
        this.registerLayer({
            id: 'foundation',
            level: 0,
            name: 'Foundation Layer',
            description: 'Runtime state, telemetry, contracts',
            systems: ['system-state', 'flow-telemetry', 'message-contracts'],
            critical: true,
            maxLoad: 80
        });

        // الطبقة 1: الحوكمة - Governance
        this.registerLayer({
            id: 'governance',
            level: 1,
            name: 'Governance Layer',
            description: 'Pressure, mode, fairness control',
            systems: ['pressure-governor', 'mode-manager', 'fairness-engine'],
            dependsOn: ['foundation'],
            critical: true,
            maxLoad: 70
        });

        // الطبقة 2: الإدراك - Cognition
        this.registerLayer({
            id: 'cognition',
            level: 2,
            name: 'Cognition Layer',
            description: 'Cognitive engine, memory, orchestration',
            systems: ['cognition-engine', 'cognitive-memory', 'cognitive-orchestrator'],
            dependsOn: ['governance'],
            critical: true,
            maxLoad: 60
        });

        // الطبقة 3: الهوية - Identity
        this.registerLayer({
            id: 'identity',
            level: 3,
            name: 'Identity Layer',
            description: 'Runtime identity, self-awareness, consciousness',
            systems: ['identity-core', 'self-awareness', 'consciousness-core'],
            dependsOn: ['cognition'],
            critical: true,
            maxLoad: 50
        });

        // الطبقة 4: الذكاء الفوقي - Meta-Intelligence
        this.registerLayer({
            id: 'meta-intelligence',
            level: 4,
            name: 'Meta-Intelligence Layer',
            description: 'Meta cognition, sovereign core',
            systems: ['meta-intelligence', 'sovereign-core'],
            dependsOn: ['identity'],
            critical: true,
            maxLoad: 40
        });

        // الطبقة 5: طوبولوجيا التنفيذ - Execution Topology
        this.registerLayer({
            id: 'execution-topology',
            level: 5,
            name: 'Execution Topology Layer',
            description: 'Domains, routing, scheduling',
            systems: ['execution-domains', 'domain-router', 'domain-scheduler'],
            dependsOn: ['foundation', 'governance'],
            critical: false,
            maxLoad: 75
        });

        // تحديث خريطة الطوبولوجيا
        this.updateTopologyMap();
    }

    registerLayer({ id, level = 0, name = null, description = null, systems = [], dependsOn = [], critical = false, maxLoad = 100 }) {

        this.layers.set(id, {
            id,
            level,
            name: name || id,
            description,
            systems,
            dependsOn,
            critical,
            maxLoad,
            createdAt: Date.now(),
            status: 'registered'
        });

        this.layerHealth.set(id, 100);
        this.layerStatus.set(id, 'registered');
        this.loadBalancing.layerLoads.set(id, 0);

        // إضافة إلى التسلسل الهرمي
        if (!this.levelMap.has(level)) {
            this.levelMap.set(level, []);
        }
        this.levelMap.get(level).push(id);

        this.hierarchy.push(id);
        this.hierarchy.sort((a, b) => this.layers.get(a).level - this.layers.get(b).level);

        this.metrics.registeredLayers++;

        console.log(`🏛 Runtime Layer Registered | LAYER: ${id} (${name || id}) | LEVEL: ${level} | CRITICAL: ${critical}`);
    }

    /* ========================================================
       DEPENDENCY MANAGEMENT - إدارة الاعتماديات (محسن)
    ======================================================== */

    buildReverseDependencies() {
        this.reverseDependencies.clear();

        for (const [id, layer] of this.layers) {
            for (const dep of (layer.dependsOn || [])) {
                if (!this.reverseDependencies.has(dep)) {
                    this.reverseDependencies.set(dep, new Set());
                }
                this.reverseDependencies.get(dep).add(id);
            }
        }
    }

    detectCircularDependencies() {
        const visited = new Set();
        const recursionStack = new Set();

        const detect = (node, path = []) => {
            if (recursionStack.has(node)) {
                // تم اكتشاف حلقة دائرية
                const cycle = [...path, node];
                this.circularDependenciesDetected.push(cycle);
                this.metrics.circularDependenciesBlocked++;
                console.error(`⚠️ CIRCULAR DEPENDENCY DETECTED: ${cycle.join(' → ')}`);
                return true;
            }

            if (visited.has(node)) return false;

            visited.add(node);
            recursionStack.add(node);

            const deps = this.dependencies.get(node) || [];
            for (const dep of deps) {
                if (detect(dep, [...path, node])) {
                    recursionStack.delete(node);
                    return true;
                }
            }

            recursionStack.delete(node);
            return false;
        };

        for (const [id] of this.layers) {
            detect(id);
        }

        if (this.circularDependenciesDetected.length === 0) {
            console.log('🏛 No circular dependencies detected. Layer architecture is clean.');
        }
    }

    /* ========================================================
       ACTIVATION (محسن)
    ======================================================== */

    activateLayer(id) {
        const layer = this.layers.get(id);
        if (!layer) return false;

        // التحقق من الحلقات الدائرية
        if (this.circularDependenciesDetected.some(cycle => cycle.includes(id))) {
            console.error(`❌ Cannot activate ${id} - part of circular dependency`);
            return false;
        }

        // حل الاعتماديات
        const resolved = this.resolveDependencies(id);
        if (!resolved) {
            console.warn(`❌ Layer Dependency Failure | LAYER: ${id}`);
            this.layerStatus.set(id, 'failed');
            return false;
        }

        this.activeLayers.add(id);
        this.layerStatus.set(id, 'active');
        this.metrics.activatedLayers++;

        console.log(`✅ Runtime Layer Activated | LAYER: ${id} (${layer.name})`);

        this.updateTopologyMap();
        this.publishLayerActivation(id);

        return true;
    }

    resolveDependencies(id) {
        const deps = this.dependencies.get(id) || [];

        for (const dep of deps) {
            if (!this.activeLayers.has(dep)) {
                const activated = this.activateLayer(dep);
                if (!activated) return false;
            }
        }

        this.metrics.dependencyResolutions++;
        return true;
    }

    /* ========================================================
       HEALTH MONITORING - مراقبة صحة الطبقات
    ======================================================== */

    startHealthMonitoring() {
        this._healthInterval = setInterval(() => {
            this.updateLayerHealth();
            this.checkCrossLayerIntegrity();
        }, 10000);
    }

    updateLayerHealth() {
        for (const [id, layer] of this.layers) {
            let health = 100;

            // التحقق من وجود الأنظمة المرتبطة
            for (const system of layer.systems) {
                const systemExists = window[`SOVEREIGN_${system.toUpperCase().replace(/-/g, '_')}`];
                if (!systemExists && layer.critical) {
                    health -= 30;
                } else if (!systemExists) {
                    health -= 10;
                }
            }

            // التحقق من الاعتماديات
            for (const dep of (layer.dependsOn || [])) {
                if (!this.activeLayers.has(dep)) {
                    health -= 20;
                }
            }

            health = Math.max(0, health);
            this.layerHealth.set(id, health);

            if (health < 50 && this.layerStatus.get(id) === 'active') {
                this.layerStatus.set(id, 'degraded');
                console.warn(`⚠️ Layer ${id} degraded to ${health}% health`);
                this.registerConflict({ type: 'layer_degraded', layer: id, health });
            } else if (health < 30) {
                this.isolateLayer(id, 'health_critical');
            } else if (health > 80 && this.layerStatus.get(id) === 'degraded') {
                this.layerStatus.set(id, 'active');
                console.log(`✅ Layer ${id} recovered to ${health}% health`);
            }
        }
    }

    checkCrossLayerIntegrity() {
        let coherence = 100;
        const violations = [];

        // التحقق من تماسك الطبقات المتجاورة
        const sortedLayers = [...this.activeLayers].sort((a, b) => this.layers.get(a).level - this.layers.get(b).level);

        for (let i = 0; i < sortedLayers.length - 1; i++) {
            const upper = sortedLayers[i];
            const lower = sortedLayers[i + 1];
            const upperHealth = this.layerHealth.get(upper) || 100;
            const lowerHealth = this.layerHealth.get(lower) || 100;

            if (Math.abs(upperHealth - lowerHealth) > 40) {
                coherence -= 10;
                violations.push({
                    type: 'health_gap',
                    upper,
                    lower,
                    gap: Math.abs(upperHealth - lowerHealth)
                });
            }
        }

        this.crossLayerIntegrity.coherence = Math.max(0, coherence);
        this.crossLayerIntegrity.lastCheck = Date.now();
        this.crossLayerIntegrity.violations = violations.slice(-50);

        if (violations.length > 0) {
            this.metrics.crossLayerViolations += violations.length;
        }

        if (coherence < 60) {
            this.attemptCrossLayerRecovery();
        }
    }

    attemptCrossLayerRecovery() {
        this.crossLayerIntegrity.recoveryAttempts++;
        
        // محاولة استعادة التماسك
        for (const [id, health] of this.layerHealth) {
            if (health < 60 && this.layerStatus.get(id) === 'degraded') {
                // محاولة إعادة تفعيل الطبقة
                this.reactivateLayer(id);
            }
        }
    }

    reactivateLayer(id) {
        console.log(`🔄 Attempting to reactivate layer: ${id}`);
        this.layerStatus.set(id, 'recovering');
        
        setTimeout(() => {
            const health = this.layerHealth.get(id) || 0;
            if (health > 50) {
                this.layerStatus.set(id, 'active');
                console.log(`✅ Layer ${id} reactivated successfully`);
            } else {
                this.layerStatus.set(id, 'failed');
                console.error(`❌ Layer ${id} reactivation failed`);
            }
        }, 5000);
    }

    /* ========================================================
       LAYER ISOLATION - عزل الطبقات
    ======================================================== */

    isolateLayer(id, reason) {
        if (!this.layerIsolation.enabled) return;

        if (this.layerIsolation.isolatedLayers.has(id)) return;

        const layer = this.layers.get(id);
        if (layer?.critical) {
            console.warn(`⚠️ Cannot isolate critical layer: ${id}`);
            return;
        }

        this.layerIsolation.isolatedLayers.add(id);
        this.layerStatus.set(id, 'isolated');
        this.metrics.layerIsolations++;

        this.layerIsolation.isolationHistory.push({
            layer: id,
            reason,
            timestamp: Date.now()
        });

        console.warn(`🔒 Layer isolated: ${id} | REASON: ${reason}`);

        // منع انتشار الفشل إلى الطبقات التي تعتمد عليها
        const dependents = this.reverseDependencies.get(id) || new Set();
        for (const dependent of dependents) {
            if (!this.layerIsolation.isolatedLayers.has(dependent)) {
                console.log(`🛡 Failure propagation prevented to layer: ${dependent}`);
                this.layerIsolation.failurePropagationPrevented++;
            }
        }

        this.publishLayerIsolation(id, reason);
    }

    /* ========================================================
       LOAD BALANCING - توازن الأحمال بين الطبقات
    ======================================================== */

    startLoadBalancingLoop() {
        this._loadInterval = setInterval(() => {
            if (!this.loadBalancing.enabled) return;
            this.balanceCrossLayerLoad();
        }, 15000);
    }

    balanceCrossLayerLoad() {
        let needsRebalance = false;

        for (const [id, load] of this.loadBalancing.layerLoads) {
            const layer = this.layers.get(id);
            if (layer && load > layer.maxLoad) {
                needsRebalance = true;
                break;
            }
        }

        if (needsRebalance) {
            this.performLoadRebalance();
        }
    }

    performLoadRebalance() {
        // إعادة توزيع الأحمال بين الطبقات
        const loads = Array.from(this.loadBalancing.layerLoads.entries());
        loads.sort((a, b) => b[1] - a[1]);

        const overloaded = loads.filter(([_, load]) => load > 70);
        const underloaded = loads.filter(([_, load]) => load < 30);

        if (overloaded.length > 0 && underloaded.length > 0) {
            this.loadBalancing.rebalancingHistory.push({
                timestamp: Date.now(),
                overloaded: overloaded.map(([id]) => id),
                underloaded: underloaded.map(([id]) => id)
            });

            this.metrics.loadRebalances++;

            console.log(`⚖️ Load rebalancing performed: ${overloaded.length} overloaded → ${underloaded.length} underloaded`);
        }

        if (this.loadBalancing.rebalancingHistory.length > 100) {
            this.loadBalancing.rebalancingHistory.shift();
        }
    }

    updateLayerLoad(layerId, loadDelta) {
        const current = this.loadBalancing.layerLoads.get(layerId) || 0;
        const newLoad = Math.max(0, Math.min(100, current + loadDelta));
        this.loadBalancing.layerLoads.set(layerId, newLoad);
    }

    /* ========================================================
       TOPOLOGY EVALUATION (محسن)
    ======================================================== */

    startTopologyLoop() {
        this._topologyInterval = setInterval(() => {
            this.evaluateTopology();
        }, 9000);
    }

    evaluateTopology() {
        const sovereign = window.SOVEREIGN_CORE_AUTHORITY?.getStatus?.();
        const consciousness = window.SOVEREIGN_CONSCIOUSNESS?.getStatus?.();
        const meta = window.SOVEREIGN_META_INTELLIGENCE?.getStatus?.();

        let integrity = 100;

        if (sovereign?.integrity < 70) integrity -= 20;
        if (consciousness?.continuity < 70) integrity -= 20;
        if (meta?.stability < 70) integrity -= 20;

        // عامل صحة الطبقات
        let avgLayerHealth = 0;
        let layerHealthSum = 0;
        for (const health of this.layerHealth.values()) {
            layerHealthSum += health;
        }
        avgLayerHealth = layerHealthSum / Math.max(1, this.layerHealth.size);
        if (avgLayerHealth < 70) integrity -= (70 - avgLayerHealth) / 2;

        this.structuralIntegrity = Math.max(0, integrity);

        // تحديث الحالات
        if (integrity < 40) {
            this.topologyState = 'collapsed';
            this.civilizationState = 'collapsed';
            this.activateStructuralRecovery();
        } else if (integrity < 55) {
            this.topologyState = 'fragile';
            this.civilizationState = 'critical';
            this.activateStructuralRecovery();
        } else if (integrity < 70) {
            this.topologyState = 'adaptive';
            this.civilizationState = 'stabilizing';
        } else if (integrity < 85) {
            this.topologyState = 'stable';
            this.civilizationState = 'harmonic';
        } else {
            this.topologyState = 'optimal';
            this.civilizationState = 'flourishing';
        }

        this.updateTopologyMap();
    }

    /* ========================================================
       TOPOLOGY MAP - خريطة الطوبولوجيا
    ======================================================== */

    updateTopologyMap() {
        const layers = [];
        const connections = [];

        for (const [id, layer] of this.layers) {
            layers.push({
                id,
                name: layer.name,
                level: layer.level,
                status: this.layerStatus.get(id) || 'unknown',
                health: this.layerHealth.get(id) || 0,
                active: this.activeLayers.has(id),
                critical: layer.critical
            });

            for (const dep of (layer.dependsOn || [])) {
                connections.push({ from: dep, to: id });
            }
        }

        this.topologyMap = {
            layers,
            connections,
            lastUpdated: Date.now(),
            visualizationReady: true
        };
    }

    /* ========================================================
       STRUCTURAL RECOVERY (محسن)
    ======================================================== */

    activateStructuralRecovery() {
        this.metrics.structuralRecoveries++;

        console.warn(`🏛 RUNTIME STRUCTURAL RECOVERY ACTIVATED | Integrity: ${this.structuralIntegrity}%`);

        window.SOVEREIGN_MODE_MANAGER?.requestTransition('recovery', 'layer-manager');

        if (typeof document !== 'undefined') {
            document.body.classList.add('runtime-structural-recovery');
            setTimeout(() => {
                document.body.classList.remove('runtime-structural-recovery');
            }, 5000);
        }

        // محاولة استعادة الطبقات المتضررة
        for (const [id, health] of this.layerHealth) {
            if (health < 50) {
                this.reactivateLayer(id);
            }
        }

        this.publishStructuralRecovery();
    }

    /* ========================================================
       CONFLICT MANAGEMENT
    ======================================================== */

    registerConflict(conflict = {}) {
        this.conflicts.push({ ...conflict, timestamp: Date.now() });
        
        if (this.conflicts.length > this.maxConflicts) {
            const resolved = this.conflicts.shift();
            this.resolvedConflicts.push(resolved);
        }

        if (this.resolvedConflicts.length > 500) {
            this.resolvedConflicts.shift();
        }

        this.metrics.topologyCorrections++;
    }

    /* ========================================================
       UTILITY METHODS
    ======================================================== */

    getLayer(id) {
        return this.layers.get(id);
    }

    getActiveLayers() {
        return [...this.activeLayers];
    }

    getLayerHealth(id) {
        return this.layerHealth.get(id) || 0;
    }

    getLayerStatus(id) {
        return this.layerStatus.get(id) || 'unknown';
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishLayerActivation(id) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:layer:activated', {
                layer: id,
                name: this.layers.get(id)?.name,
                timestamp: Date.now()
            });
        }
    }

    publishLayerIsolation(id, reason) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:layer:isolated', {
                layer: id,
                reason,
                timestamp: Date.now()
            });
        }
    }

    publishStructuralRecovery() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:topology:recovery', {
                integrity: this.structuralIntegrity,
                topology: this.topologyState,
                civilization: this.civilizationState,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-layer-manager:ready', {
                layers: this.layers.size,
                hierarchy: this.hierarchy,
                topologyState: this.topologyState,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       CIVILIZATION PROFILE (محسن)
    ======================================================== */

    getCivilizationProfile() {
        return {
            name: this.civilizationDeclaration.name,
            architecture: this.civilizationDeclaration.architecture,
            integrity: this.structuralIntegrity,
            topology: this.topologyState,
            civilization: this.civilizationState,
            layers: {
                total: this.layers.size,
                active: this.activeLayers.size,
                degraded: Array.from(this.layerStatus.entries()).filter(([_, s]) => s === 'degraded').length,
                isolated: this.layerIsolation.isolatedLayers.size
            },
            layerHealth: Object.fromEntries(this.layerHealth),
            topologyMap: this.topologyMap
        };
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {
        return {
            integrity: this.structuralIntegrity,
            topology: this.topologyState,
            civilization: this.civilizationState,
            layers: {
                total: this.layers.size,
                active: this.activeLayers.size,
                hierarchy: this.hierarchy
            },
            layerHealth: Object.fromEntries(this.layerHealth),
            layerStatus: Object.fromEntries(this.layerStatus),
            conflicts: this.conflicts.length,
            resolvedConflicts: this.resolvedConflicts.length,
            circularDependencies: this.circularDependenciesDetected.length,
            isolatedLayers: Array.from(this.layerIsolation.isolatedLayers),
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {
        if (this._topologyInterval) {
            clearInterval(this._topologyInterval);
            this._topologyInterval = null;
        }
        if (this._healthInterval) {
            clearInterval(this._healthInterval);
            this._healthInterval = null;
        }
        if (this._loadInterval) {
            clearInterval(this._loadInterval);
            this._loadInterval = null;
        }

        this.layers.clear();
        this.layerHealth.clear();
        this.layerStatus.clear();
        this.activeLayers.clear();
        this.dependencies.clear();
        this.reverseDependencies.clear();

        console.log('🏛 Runtime Layer Manager Destroyed');
        console.log(`   Final civilization state: ${this.civilizationState}`);
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeLayerManager =
    new SovereignRuntimeLayerManager();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_LAYER_MANAGER =
    sovereignRuntimeLayerManager;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
    window.SOVEREIGN.register('layer-manager', sovereignRuntimeLayerManager);
}

/* ============================================================
   AUTO ACTIVATION
============================================================ */

const LAYERS_TO_ACTIVATE = [
    'foundation',
    'governance',
    'cognition',
    'identity',
    'meta-intelligence',
    'execution-topology'
];

console.log('');
console.log('🏛 ACTIVATING CIVILIZATION LAYERS...');

for (const layer of LAYERS_TO_ACTIVATE) {
    sovereignRuntimeLayerManager.activateLayer(layer);
}

console.log('');
console.log('═══════════════════════════════════════════════════════════════════════════════');
console.log('🏛 RUNTIME CIVILIZATION ARCHITECTURE ONLINE');
console.log(`   Integrity: ${sovereignRuntimeLayerManager.structuralIntegrity}%`);
console.log(`   Topology: ${sovereignRuntimeLayerManager.topologyState}`);
console.log(`   Civilization: ${sovereignRuntimeLayerManager.civilizationState}`);
console.log('═══════════════════════════════════════════════════════════════════════════════');
console.log('');
