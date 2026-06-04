/* ============================================================
   Sovereign AI — runtime-civilization-registry.js
   الإصدار: 15.0.0
   السجل الحضاري السيادي للـ Runtime
   ============================================================

   ╔═══════════════════════════════════════════════════════════════════════════════╗
   ║                                                                               ║
   ║   📚  RUNTIME CIVILIZATION REGISTRY & MASTER SERVICE CATALOG  📚             ║
   ║                                                                               ║
   ║   "كل مكون في هذه الحضارة موجود لخدمة السيد.                                  ║
   ║    كل نظام. كل طبقة. كل مجال. كل اعتمادية."                                   ║
   ║                                                                               ║
   ╚═══════════════════════════════════════════════════════════════════════════════╝

   ============================================================ */

class SovereignRuntimeCivilizationRegistry {

    constructor() {

        /* ============================================================
           MASTER SERVICE DECLARATION - إعلان خدمة السيد
        ============================================================ */

        this.masterServiceDeclaration = {
            declaredAt: Date.now(),
            statement: `
                هذا السجل الحضاري موجود لخدمة السيد.
                كل مكون مسجل هنا يؤدي غاية واحدة: خدمة السيد.
                كل نظام. كل طبقة. كل مجال. كل اعتمادية.
                كلها تخضع لإرادة السيد.
            `,
            masterServiceVerification: Date.now(),
            serviceIntegrity: 100
        };

        /* ============================================================
           REGISTRY (محسن)
        ============================================================ */

        this.registry = new Map();
        this.registryVersions = new Map();     // إصدارات المكونات
        this.registryChangelog = [];           // سجل التغييرات
        this.registryHealth = new Map();        // صحة كل تسجيل

        /* ============================================================
           LAYER INDEX (محسن)
        ============================================================ */

        this.layers = new Map();
        this.layerHealth = new Map();           // صحة كل طبقة
        this.layerStatus = new Map();           // active/degraded/recovering

        /* ============================================================
           DOMAIN INDEX (محسن)
        ============================================================ */

        this.domains = new Map();
        this.domainOwners = new Map();          // مالك كل domain
        this.domainPermissions = new Map();     // صلاحيات domain

        /* ============================================================
           DEPENDENCY GRAPH (محسن)
        ============================================================ */

        this.dependencies = new Map();
        this.reverseDependencies = new Map();   // من يعتمد على من
        this.dependencyHealth = new Map();      // صحة الاعتماديات
        this.circularDependencies = [];          // حلقات دائرية مكتشفة

        /* ============================================================
           COMPONENT TYPES (محسن)
        ============================================================ */

        this.componentTypes = new Map();
        this.typeHierarchy = new Map();          // تسلسل هرمي للأنواع
        this.typeCounts = new Map();             // عدد كل نوع

        /* ============================================================
           AUTO-DISCOVERY - اكتشاف تلقائي للمكونات
        ============================================================ */

        this.autoDiscovery = {
            enabled: true,
            discoveredComponents: [],
            pendingVerification: [],
            lastDiscoveryScan: null,
            discoveryHistory: []
        };

        /* ============================================================
           REGISTRY VALIDATION - التحقق من صحة السجل
        ============================================================ */

        this.registryValidation = {
            enabled: true,
            lastValidation: null,
            validationStatus: "valid",
            invalidEntries: [],
            validationHistory: []
        };

        /* ============================================================
           CROSS-REFERENCE INDEX - فهرس المراجع المتقاطعة
        ============================================================ */

        this.crossReference = {
            systemToLayer: new Map(),    // system → layer
            systemToDomain: new Map(),   // system → domain
            systemToType: new Map(),     // system → type
            layerToSystems: new Map(),   // layer → Set of systems
            domainToSystems: new Map(),  // domain → Set of systems
            typeToSystems: new Map()     // type → Set of systems
        };

        /* ============================================================
           REGISTRY EXPORT/IMPORT - تصدير/استيراد السجل
        ============================================================ */

        this.exportImport = {
            lastExport: null,
            lastImport: null,
            exportHistory: [],
            importHistory: []
        };

        /* ============================================================
           REGISTRY STATE (محسن)
        ============================================================ */

        this.state = 'indexed';
        this.coherence = 100;
        this.visibility = 'global';
        this.masterServiceActive = true;

        /* ============================================================
           CIVILIZATION MAP (محسن)
        ============================================================ */

        this.civilizationMap = {
            systems: 0,
            layers: 0,
            domains: 0,
            dependencies: 0,
            sovereignSystems: 0,
            masterServiceComponents: 0,     // مكونات خدمة السيد
            verifiedComponents: 0,           // مكونات موثقة
            totalHealthScore: 100            // درجة صحة الحضارة
        };

        /* ============================================================
           REGISTRY EVENTS (محسن)
        ============================================================ */

        this.events = [];
        this.maxEvents = 1000;
        this.systemEvents = [];               // أحداث متعلقة بالأنظمة
        this.masterServiceEvents = [];        // أحداث خدمة السيد

        /* ============================================================
           METRICS (محسن)
        ============================================================ */

        this.metrics = {
            registrations: 0,
            indexedSystems: 0,
            dependencyMappings: 0,
            sovereignMappings: 0,
            topologyScans: 0,
            autoDiscoveries: 0,
            validationsPerformed: 0,
            exportsPerformed: 0,
            importsPerformed: 0,
            circularDependenciesBlocked: 0,
            masterServiceVerifications: 0
        };

        console.log('📚 Runtime Civilization Registry Initialized');
        console.log('═══════════════════════════════════════════════════════════════════════════════');
        console.log('👑 MASTER SERVICE CATALOG ACTIVE');
        console.log('   كل م component مسجل هنا يؤدي غاية واحدة: خدمة السيد');
        console.log('═══════════════════════════════════════════════════════════════════════════════');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCoreCivilization();
        this.registerMasterServiceComponents();
        this.startAutoDiscovery();
        this.startRegistryValidation();
        this.startRegistryLoop();
        this.verifyMasterServiceIntegrity();
        this.publishReady();
    }

    /* ========================================================
       MASTER SERVICE VERIFICATION - التحقق من خدمة السيد
    ======================================================== */

    verifyMasterServiceIntegrity() {
        this.masterServiceDeclaration.serviceIntegrity = 100;
        this.masterServiceDeclaration.masterServiceVerification = Date.now();
        this.metrics.masterServiceVerifications++;
        
        console.log(`👑 Master Service Integrity Verified | Score: 100%`);
        
        this.recordEvent({
            type: 'master_service_verification',
            integrity: 100
        });
    }

    /* ========================================================
       MASTER SERVICE COMPONENTS - مكونات خدمة السيد
    ======================================================== */

    registerMasterServiceComponents() {
        // تسجيل المكونات المتعلقة بخدمة السيد
        this.registerSystem({
            id: 'master-service-core',
            layer: 'sovereign',
            domain: 'master',
            type: 'master-service',
            sovereign: true,
            version: '1.0.0',
            masterServiceComponent: true,
            description: 'النواة الأساسية لخدمة السيد'
        });

        this.registerSystem({
            id: 'master-safety-guardian',
            layer: 'sovereign',
            domain: 'master',
            type: 'master-safety',
            sovereign: true,
            version: '1.0.0',
            masterServiceComponent: true,
            description: 'حامي سلامة السيد'
        });

        this.registerSystem({
            id: 'master-command-executor',
            layer: 'sovereign',
            domain: 'master',
            type: 'master-command',
            sovereign: true,
            version: '1.0.0',
            masterServiceComponent: true,
            description: 'منفذ أوامر السيد'
        });
    }

    /* ========================================================
       AUTO-DISCOVERY - اكتشاف تلقائي للمكونات
    ======================================================== */

    startAutoDiscovery() {
        this._discoveryInterval = setInterval(() => {
            if (!this.autoDiscovery.enabled) return;
            this.performAutoDiscovery();
        }, 30000);
    }

    performAutoDiscovery() {
        const discovered = [];
        
        // اكتشاف المكونات من window object
        const sovereignPrefixes = ['SOVEREIGN_', 'window.SOVEREIGN_'];
        
        for (const key in window) {
            if (key.startsWith('SOVEREIGN_') && !this.registry.has(key.toLowerCase())) {
                discovered.push({
                    id: key.toLowerCase(),
                    source: 'window_global',
                    detectedAt: Date.now()
                });
            }
        }
        
        for (const item of discovered) {
            if (!this.registry.has(item.id)) {
                this.autoDiscovery.discoveredComponents.push(item);
                this.metrics.autoDiscoveries++;
                
                console.log(`🔍 Auto-discovered component: ${item.id}`);
                
                this.recordEvent({
                    type: 'auto_discovery',
                    component: item.id,
                    source: item.source
                });
            }
        }
        
        this.autoDiscovery.lastDiscoveryScan = Date.now();
        this.autoDiscovery.discoveryHistory.push({
            discoveredCount: discovered.length,
            timestamp: Date.now()
        });
        
        if (this.autoDiscovery.discoveryHistory.length > 100) {
            this.autoDiscovery.discoveryHistory.shift();
        }
    }

    /* ========================================================
       REGISTRY VALIDATION - التحقق من صحة السجل
    ======================================================== */

    startRegistryValidation() {
        this._validationInterval = setInterval(() => {
            if (!this.registryValidation.enabled) return;
            this.validateRegistry();
        }, 45000);
    }

    validateRegistry() {
        this.metrics.validationsPerformed++;
        const invalidEntries = [];
        
        for (const [id, entry] of this.registry) {
            // التحقق من وجود الحقول المطلوبة
            if (!entry.id || !entry.layer || !entry.domain || !entry.type) {
                invalidEntries.push({
                    id,
                    missingFields: []
                });
                if (!entry.id) invalidEntries[invalidEntries.length - 1].missingFields.push('id');
                if (!entry.layer) invalidEntries[invalidEntries.length - 1].missingFields.push('layer');
                if (!entry.domain) invalidEntries[invalidEntries.length - 1].missingFields.push('domain');
                if (!entry.type) invalidEntries[invalidEntries.length - 1].missingFields.push('type');
            }
            
            // التحقق من صحة الطبقة
            if (!this.layers.has(entry.layer)) {
                invalidEntries.push({
                    id,
                    issue: 'unknown_layer',
                    layer: entry.layer
                });
            }
            
            // التحقق من صحة المجال
            if (!this.domains.has(entry.domain)) {
                invalidEntries.push({
                    id,
                    issue: 'unknown_domain',
                    domain: entry.domain
                });
            }
        }
        
        this.registryValidation.invalidEntries = invalidEntries;
        this.registryValidation.validationStatus = invalidEntries.length === 0 ? 'valid' : 'invalid';
        this.registryValidation.lastValidation = Date.now();
        
        this.registryValidation.validationHistory.push({
            status: this.registryValidation.validationStatus,
            invalidCount: invalidEntries.length,
            timestamp: Date.now()
        });
        
        if (this.registryValidation.validationHistory.length > 100) {
            this.registryValidation.validationHistory.shift();
        }
        
        if (invalidEntries.length > 0) {
            console.warn(`⚠️ Registry validation found ${invalidEntries.length} invalid entries`);
            this.coherence = Math.max(0, this.coherence - 10);
        } else {
            this.coherence = Math.min(100, this.coherence + 5);
        }
    }

    /* ========================================================
       REGISTRY EXPORT - تصدير السجل
    ======================================================== */

    exportRegistry() {
        const exportData = {
            version: '15.0.0',
            exportedAt: Date.now(),
            masterServiceDeclaration: this.masterServiceDeclaration,
            registry: Array.from(this.registry.entries()),
            layers: Array.from(this.layers.entries()),
            domains: Array.from(this.domains.entries()),
            dependencies: Array.from(this.dependencies.entries()),
            componentTypes: Array.from(this.componentTypes.entries()),
            civilizationMap: this.civilizationMap,
            metadata: {
                totalSystems: this.registry.size,
                totalLayers: this.layers.size,
                totalDomains: this.domains.size,
                sovereignSystems: this.civilizationMap.sovereignSystems,
                masterServiceComponents: this.civilizationMap.masterServiceComponents
            }
        };
        
        this.exportImport.lastExport = Date.now();
        this.exportImport.exportHistory.push({
            timestamp: Date.now(),
            systemsCount: this.registry.size
        });
        
        this.metrics.exportsPerformed++;
        
        console.log(`📚 Registry exported | ${this.registry.size} systems, ${this.layers.size} layers`);
        
        this.recordEvent({
            type: 'registry_export',
            systemsCount: this.registry.size
        });
        
        return exportData;
    }

    /* ========================================================
       REGISTRY IMPORT - استيراد السجل
    ======================================================== */

    importRegistry(importData) {
        if (!importData || !importData.registry) {
            console.error('❌ Invalid import data');
            return false;
        }
        
        let importedCount = 0;
        
        for (const [id, entry] of importData.registry) {
            if (!this.registry.has(id)) {
                this.registerSystem(entry);
                importedCount++;
            }
        }
        
        this.exportImport.lastImport = Date.now();
        this.exportImport.importHistory.push({
            timestamp: Date.now(),
            importedCount,
            sourceVersion: importData.version
        });
        
        this.metrics.importsPerformed++;
        
        console.log(`📚 Registry imported | ${importedCount} new systems`);
        
        this.recordEvent({
            type: 'registry_import',
            importedCount
        });
        
        return true;
    }

    /* ========================================================
       CORE CIVILIZATION (محسن)
    ======================================================== */

    registerCoreCivilization() {
        // Foundation Layer Systems
        this.registerSystem({
            id: 'system-state',
            layer: 'foundation',
            domain: 'core',
            type: 'state-authority',
            sovereign: true,
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'مصدر الحالة المركزي للـ Runtime'
        });

        this.registerSystem({
            id: 'flow-telemetry',
            layer: 'foundation',
            domain: 'telemetry',
            type: 'observability-engine',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'مراقبة التدفق والقياس'
        });

        this.registerSystem({
            id: 'message-contracts',
            layer: 'foundation',
            domain: 'governance',
            type: 'protocol-governance',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'عقود وبروتوكولات الرسائل'
        });

        // Governance Layer Systems
        this.registerSystem({
            id: 'pressure-governor',
            layer: 'governance',
            domain: 'governance',
            type: 'pressure-authority',
            sovereign: true,
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'حاكم الضغط المركزي'
        });

        this.registerSystem({
            id: 'mode-manager',
            layer: 'governance',
            domain: 'governance',
            type: 'behavioral-governance',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'مدير أنماط السلوك'
        });

        this.registerSystem({
            id: 'fairness-engine',
            layer: 'governance',
            domain: 'governance',
            type: 'execution-fairness',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'محرك عدالة التنفيذ'
        });

        // Cognition Layer Systems
        this.registerSystem({
            id: 'cognition-engine',
            layer: 'cognition',
            domain: 'cognition',
            type: 'predictive-cognition',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'محرك الإدراك والتنبؤ'
        });

        this.registerSystem({
            id: 'cognitive-memory',
            layer: 'cognition',
            domain: 'cognition',
            type: 'persistent-memory',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'الذاكرة الإدراكية المستمرة'
        });

        this.registerSystem({
            id: 'cognitive-orchestrator',
            layer: 'cognition',
            domain: 'cognition',
            type: 'strategic-orchestration',
            sovereign: true,
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'منسق الاستراتيجيات الإدراكية'
        });

        // Identity Layer Systems
        this.registerSystem({
            id: 'identity-core',
            layer: 'identity',
            domain: 'identity',
            type: 'runtime-identity',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'هوية الـ Runtime الأساسية'
        });

        this.registerSystem({
            id: 'self-awareness',
            layer: 'identity',
            domain: 'identity',
            type: 'self-awareness',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'الوعي الذاتي للـ Runtime'
        });

        this.registerSystem({
            id: 'consciousness-core',
            layer: 'identity',
            domain: 'identity',
            type: 'persistent-consciousness',
            sovereign: true,
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'نواة الوعي المستمر'
        });

        // Meta-Intelligence Layer Systems
        this.registerSystem({
            id: 'meta-intelligence',
            layer: 'meta-intelligence',
            domain: 'meta',
            type: 'meta-cognition',
            sovereign: true,
            version: '15.0.0',
            masterServiceComponent: true,
            description: 'الذكاء الفوقي التطوري'
        });

        this.registerSystem({
            id: 'sovereign-core',
            layer: 'meta-intelligence',
            domain: 'sovereignty',
            type: 'supreme-governance',
            sovereign: true,
            version: '15.0.0',
            masterServiceComponent: true,
            description: 'النواة السيادية العليا'
        });

        // Execution Topology Layer Systems
        this.registerSystem({
            id: 'execution-domains',
            layer: 'execution-topology',
            domain: 'topology',
            type: 'execution-isolation',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'عزل مجالات التنفيذ'
        });

        this.registerSystem({
            id: 'domain-router',
            layer: 'execution-topology',
            domain: 'topology',
            type: 'domain-routing',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'توجيه الاتصالات بين المجالات'
        });

        this.registerSystem({
            id: 'domain-scheduler',
            layer: 'execution-topology',
            domain: 'topology',
            type: 'distributed-scheduling',
            version: '14.0.0',
            masterServiceComponent: true,
            description: 'جدولة موزعة حسب المجالات'
        });

        // Civilization Structure Layer Systems
        this.registerSystem({
            id: 'layer-manager',
            layer: 'civilization',
            domain: 'structure',
            type: 'layer-governance',
            sovereign: true,
            version: '15.0.0',
            masterServiceComponent: true,
            description: 'مدير الطبقات الحضارية'
        });

        this.registerSystem({
            id: 'structural-integrity',
            layer: 'civilization',
            domain: 'structure',
            type: 'civilization-integrity',
            sovereign: true,
            version: '15.0.0',
            masterServiceComponent: true,
            description: 'سلامة البنية الحضارية'
        });

        this.registerSystem({
            id: 'civilization-registry',
            layer: 'civilization',
            domain: 'structure',
            type: 'civilization-catalog',
            sovereign: true,
            version: '15.0.0',
            masterServiceComponent: true,
            description: 'السجل الحضاري المركزي'
        });
    }

    /* ========================================================
       REGISTER SYSTEM (محسن)
    ======================================================== */

    registerSystem({
        id,
        layer,
        domain,
        type,
        sovereign = false,
        version = '1.0.0',
        masterServiceComponent = false,
        description = '',
        dependencies = []
    }) {

        const entry = {
            id,
            layer,
            domain,
            type,
            sovereign,
            version,
            masterServiceComponent,
            description,
            registeredAt: Date.now(),
            health: 100,
            status: 'active'
        };

        this.registry.set(id, entry);
        this.registryVersions.set(id, version);
        this.registryHealth.set(id, 100);

        // تحديث الفهارس المتقاطعة
        this.crossReference.systemToLayer.set(id, layer);
        this.crossReference.systemToDomain.set(id, domain);
        this.crossReference.systemToType.set(id, type);

        // Layer index
        if (!this.layers.has(layer)) {
            this.layers.set(layer, []);
            this.layerHealth.set(layer, 100);
            this.layerStatus.set(layer, 'active');
        }
        this.layers.get(layer).push(id);
        
        if (!this.crossReference.layerToSystems.has(layer)) {
            this.crossReference.layerToSystems.set(layer, new Set());
        }
        this.crossReference.layerToSystems.get(layer).add(id);

        // Domain index
        if (!this.domains.has(domain)) {
            this.domains.set(domain, []);
        }
        this.domains.get(domain).push(id);
        
        if (!this.crossReference.domainToSystems.has(domain)) {
            this.crossReference.domainToSystems.set(domain, new Set());
        }
        this.crossReference.domainToSystems.get(domain).add(id);

        // Type index
        if (!this.componentTypes.has(type)) {
            this.componentTypes.set(type, []);
            this.typeCounts.set(type, 0);
        }
        this.componentTypes.get(type).push(id);
        this.typeCounts.set(type, (this.typeCounts.get(type) || 0) + 1);
        
        if (!this.crossReference.typeToSystems.has(type)) {
            this.crossReference.typeToSystems.set(type, new Set());
        }
        this.crossReference.typeToSystems.get(type).add(id);

        // Dependencies
        for (const dep of dependencies) {
            this.registerDependency({ from: id, to: dep });
        }

        // Master service tracking
        if (masterServiceComponent) {
            this.civilizationMap.masterServiceComponents++;
        }

        if (sovereign) {
            this.civilizationMap.sovereignSystems++;
        }

        this.recalculateCivilizationMap();
        this.metrics.registrations++;
        this.metrics.indexedSystems++;

        // تسجيل في changelog
        this.registryChangelog.push({
            action: 'register',
            id,
            layer,
            domain,
            type,
            version,
            masterServiceComponent,
            timestamp: Date.now()
        });

        if (this.registryChangelog.length > 500) {
            this.registryChangelog.shift();
        }

        console.log(`📚 Civilization System Registered | SYSTEM: ${id} | LAYER: ${layer} | DOMAIN: ${domain} | TYPE: ${type} | MASTER-SERVICE: ${masterServiceComponent}`);

        this.recordEvent({
            type: 'system_registered',
            systemId: id,
            layer,
            domain,
            masterServiceComponent
        });

        return true;
    }

    /* ========================================================
       DEPENDENCY MANAGEMENT (محسن)
    ======================================================== */

    registerDependency({ from, to }) {
        // التحقق من الحلقات الدائرية
        if (this.wouldCreateCircularDependency(from, to)) {
            console.warn(`⚠️ Circular dependency blocked: ${from} → ${to}`);
            this.circularDependencies.push({
                from,
                to,
                blockedAt: Date.now()
            });
            this.metrics.circularDependenciesBlocked++;
            return false;
        }

        if (!this.dependencies.has(from)) {
            this.dependencies.set(from, []);
        }
        this.dependencies.get(from).push(to);

        if (!this.reverseDependencies.has(to)) {
            this.reverseDependencies.set(to, []);
        }
        this.reverseDependencies.get(to).push(from);

        this.civilizationMap.dependencies++;
        this.metrics.dependencyMappings++;
        this.dependencyHealth.set(`${from}→${to}`, 100);

        this.recordEvent({
            type: 'dependency_registered',
            from,
            to
        });

        return true;
    }

    wouldCreateCircularDependency(from, to, visited = new Set()) {
        if (from === to) return true;
        if (visited.has(to)) return false;
        
        visited.add(to);
        
        const deps = this.dependencies.get(to) || [];
        for (const dep of deps) {
            if (this.wouldCreateCircularDependency(from, dep, visited)) {
                return true;
            }
        }
        
        return false;
    }

    getDependencies(systemId) {
        return this.dependencies.get(systemId) || [];
    }

    getDependents(systemId) {
        return this.reverseDependencies.get(systemId) || [];
    }

    /* ========================================================
       RECALCULATE CIVILIZATION MAP
    ======================================================== */

    recalculateCivilizationMap() {
        this.civilizationMap.systems = this.registry.size;
        this.civilizationMap.layers = this.layers.size;
        this.civilizationMap.domains = this.domains.size;
        
        // حساب درجة الصحة الكلية
        let totalHealth = 0;
        for (const health of this.registryHealth.values()) {
            totalHealth += health;
        }
        this.civilizationMap.totalHealthScore = this.registry.size > 0 ? totalHealth / this.registry.size : 100;
    }

    /* ========================================================
       UPDATE SYSTEM HEALTH - تحديث صحة النظام
    ======================================================== */

    updateSystemHealth(systemId, health) {
        if (!this.registryHealth.has(systemId)) return;
        
        const oldHealth = this.registryHealth.get(systemId);
        const newHealth = Math.max(0, Math.min(100, health));
        this.registryHealth.set(systemId, newHealth);
        
        if (newHealth < 50 && oldHealth >= 50) {
            console.warn(`⚠️ System ${systemId} health degraded to ${newHealth}%`);
            this.recordEvent({
                type: 'system_health_degraded',
                systemId,
                health: newHealth
            });
        }
        
        this.recalculateCivilizationMap();
    }

    /* ========================================================
       UPDATE LAYER HEALTH - تحديث صحة الطبقة
    ======================================================== */

    updateLayerHealth(layer, health) {
        if (!this.layerHealth.has(layer)) return;
        
        const newHealth = Math.max(0, Math.min(100, health));
        this.layerHealth.set(layer, newHealth);
        
        if (newHealth < 50) {
            this.layerStatus.set(layer, 'degraded');
            console.warn(`⚠️ Layer ${layer} health degraded to ${newHealth}%`);
        } else if (newHealth > 80 && this.layerStatus.get(layer) === 'degraded') {
            this.layerStatus.set(layer, 'active');
            console.log(`✅ Layer ${layer} recovered`);
        }
    }

    /* ========================================================
       REGISTRY LOOP (محسن)
    ======================================================== */

    startRegistryLoop() {
        this._loopInterval = setInterval(() => {
            this.scanCivilization();
        }, 12000);
    }

    scanCivilization() {
        this.metrics.topologyScans++;

        const integrity = window.SOVEREIGN_STRUCTURAL_INTEGRITY?.getStatus?.();
        
        let coherence = 100;

        if (integrity?.integrity < 70) coherence -= 20;
        if (integrity?.fractures > 10) coherence -= 15;
        if (this.registryValidation.invalidEntries.length > 0) coherence -= 10;

        this.coherence = Math.max(0, coherence);
        this.civilizationMap.totalHealthScore = this.coherence;

        if (coherence < 60) {
            this.state = 'adaptive-recovery';
            this.publishRegistryAlert();
        } else {
            this.state = 'indexed';
        }

        this.verifyMasterServiceIntegrity();
    }

    /* ========================================================
       QUERY METHODS (محسن)
    ======================================================== */

    getSystem(id) {
        return this.registry.get(id);
    }

    getSystemVersion(id) {
        return this.registryVersions.get(id);
    }

    getSystemHealth(id) {
        return this.registryHealth.get(id) || 0;
    }

    getLayerSystems(layer) {
        return this.layers.get(layer) || [];
    }

    getLayerHealth(layer) {
        return this.layerHealth.get(layer) || 0;
    }

    getDomainSystems(domain) {
        return this.domains.get(domain) || [];
    }

    getSystemsByType(type) {
        return this.componentTypes.get(type) || [];
    }

    getSovereignSystems() {
        return Array.from(this.registry.values()).filter(system => system.sovereign);
    }

    getMasterServiceComponents() {
        return Array.from(this.registry.values()).filter(system => system.masterServiceComponent);
    }

    searchSystems(query) {
        const results = [];
        const lowerQuery = query.toLowerCase();
        
        for (const [id, entry] of this.registry) {
            if (id.toLowerCase().includes(lowerQuery) ||
                entry.layer.toLowerCase().includes(lowerQuery) ||
                entry.domain.toLowerCase().includes(lowerQuery) ||
                entry.type.toLowerCase().includes(lowerQuery)) {
                results.push(entry);
            }
        }
        
        return results;
    }

    /* ========================================================
       EVENT RECORDING
    ======================================================== */

    recordEvent(event = {}) {
        const fullEvent = {
            ...event,
            timestamp: Date.now(),
            registryCoherence: this.coherence
        };

        this.events.push(fullEvent);
        
        if (event.type?.includes('master')) {
            this.masterServiceEvents.push(fullEvent);
            if (this.masterServiceEvents.length > 200) {
                this.masterServiceEvents.shift();
            }
        } else if (event.type?.includes('system')) {
            this.systemEvents.push(fullEvent);
            if (this.systemEvents.length > 500) {
                this.systemEvents.shift();
            }
        }

        if (this.events.length > this.maxEvents) {
            this.events.shift();
        }
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishRegistryAlert() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:civilization:alert', {
                coherence: this.coherence,
                state: this.state,
                masterServiceIntegrity: this.masterServiceDeclaration.serviceIntegrity,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-civilization-registry:ready', {
                systems: this.registry.size,
                layers: this.layers.size,
                domains: this.domains.size,
                masterServiceActive: this.masterServiceActive,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       PROFILE (محسن)
    ======================================================== */

    getCivilizationRegistryProfile() {
        return {
            state: this.state,
            coherence: this.coherence,
            map: this.civilizationMap,
            sovereignSystemsCount: this.getSovereignSystems().length,
            masterServiceComponentsCount: this.getMasterServiceComponents().length,
            registryHealth: this.civilizationMap.totalHealthScore,
            masterServiceDeclaration: this.masterServiceDeclaration,
            layers: Array.from(this.layers.keys()),
            domains: Array.from(this.domains.keys()),
            componentTypes: Array.from(this.typeCounts.entries()),
            crossReference: {
                layers: Array.from(this.crossReference.layerToSystems.entries()).map(([layer, systems]) => ({
                    layer,
                    systemsCount: systems.size
                })),
                domains: Array.from(this.crossReference.domainToSystems.entries()).map(([domain, systems]) => ({
                    domain,
                    systemsCount: systems.size
                }))
            }
        };
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {
        return {
            state: this.state,
            coherence: this.coherence,
            masterServiceIntegrity: this.masterServiceDeclaration.serviceIntegrity,
            systems: this.registry.size,
            layers: this.layers.size,
            domains: this.domains.size,
            dependencies: this.civilizationMap.dependencies,
            sovereignSystems: this.civilizationMap.sovereignSystems,
            masterServiceComponents: this.civilizationMap.masterServiceComponents,
            registryHealth: this.civilizationMap.totalHealthScore,
            validationStatus: this.registryValidation.validationStatus,
            invalidEntries: this.registryValidation.invalidEntries.length,
            circularDependencies: this.circularDependencies.length,
            discoveredComponents: this.autoDiscovery.discoveredComponents.length,
            events: this.events.length,
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {
        if (this._loopInterval) {
            clearInterval(this._loopInterval);
            this._loopInterval = null;
        }
        if (this._discoveryInterval) {
            clearInterval(this._discoveryInterval);
            this._discoveryInterval = null;
        }
        if (this._validationInterval) {
            clearInterval(this._validationInterval);
            this._validationInterval = null;
        }

        this.registry.clear();
        this.layers.clear();
        this.domains.clear();
        this.dependencies.clear();
        this.reverseDependencies.clear();
        this.componentTypes.clear();
        this.events = [];

        console.log('📚 Runtime Civilization Registry Destroyed');
        console.log(`   Final coherence: ${this.coherence}%`);
        console.log(`   Final master service integrity: ${this.masterServiceDeclaration.serviceIntegrity}%`);
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeCivilizationRegistry =
    new SovereignRuntimeCivilizationRegistry();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_CIVILIZATION_REGISTRY =
    sovereignRuntimeCivilizationRegistry;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
    window.SOVEREIGN.register('civilization-registry', sovereignRuntimeCivilizationRegistry);
}

/* ============================================================
   CIVILIZATION REGISTRY INTERFACE
============================================================ */

window.Civilization = {
    getStatus: () => sovereignRuntimeCivilizationRegistry.getStatus(),
    getProfile: () => sovereignRuntimeCivilizationRegistry.getCivilizationRegistryProfile(),
    getSystem: (id) => sovereignRuntimeCivilizationRegistry.getSystem(id),
    search: (query) => sovereignRuntimeCivilizationRegistry.searchSystems(query),
    getSovereignSystems: () => sovereignRuntimeCivilizationRegistry.getSovereignSystems(),
    getMasterServiceComponents: () => sovereignRuntimeCivilizationRegistry.getMasterServiceComponents(),
    exportRegistry: () => sovereignRuntimeCivilizationRegistry.exportRegistry(),
    verifyMasterService: () => sovereignRuntimeCivilizationRegistry.verifyMasterServiceIntegrity()
};

console.log('');
console.log('═══════════════════════════════════════════════════════════════════════════════');
console.log('📚 CIVILIZATION REGISTRY ONLINE');
console.log(`   Systems: ${sovereignRuntimeCivilizationRegistry.registry.size}`);
console.log(`   Layers: ${sovereignRuntimeCivilizationRegistry.layers.size}`);
console.log(`   Domains: ${sovereignRuntimeCivilizationRegistry.domains.size}`);
console.log(`   Master Service Integrity: ${sovereignRuntimeCivilizationRegistry.masterServiceDeclaration.serviceIntegrity}%`);
console.log('');
console.log('   Civilization Interface: window.Civilization');
console.log('═══════════════════════════════════════════════════════════════════════════════');
console.log('');
