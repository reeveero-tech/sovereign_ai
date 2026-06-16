/* ============================================================
   SOVRA — runtime-layer-registry.js
   الإصدار: 2.0.0
   السجل الرسمي لطبقات SOVRA الحية
   بدون هذا السجل → فوضى اكتشاف الطبقات وصراع المسؤوليات
   ============================================================ */

(() => {

    class SovraRuntimeLayerRegistry {

        constructor() {

            /* تخزين الطبقات */
            this.layers = new Map();
            
            /* تبعيات الطبقات */
            this.dependencies = new Map();
            
            /* عكس التبعيات - من يعتمد عليّ */
            this.reverseDependencies = new Map();
            
            /* مسؤوليات الطبقات */
            this.responsibilities = new Map();
            
            /* حالة الطبقات */
            this.layerStates = new Map();
            
            /* ترتيب التهيئة */
            this.initializationOrder = [];
            
            /* سجل الأخطاء */
            this.errors = [];
            
            /* سجل التحذيرات */
            this.warnings = [];
            
            /* جاهزية النظام */
            this.systemReady = false;
            
            /* وقت بدء التشغيل */
            this.startupTime = Date.now();
            
            console.log('🧭 SOVRA Runtime Layer Registry Created');
        }

        /* ====================================================
           تسجيل طبقة - REGISTER LAYER
        ==================================================== */

        register(name, config = {}) {

            /* منع التسجيل المزدوج */
            if (this.layers.has(name)) {
                this.warnings.push({
                    type: 'duplicate_layer',
                    layer: name,
                    timestamp: Date.now(),
                    message: `⚠️ Duplicate layer registration attempted for: ${name}`
                });
                console.warn(`⚠️ Runtime Layer Registry: Duplicate layer - ${name}`);
                return false;
            }

            /* التحقق من صحة الإعدادات */
            const requiredFields = ['type', 'role', 'authority', 'dependencies'];
            const missingFields = requiredFields.filter(field => !config[field]);
            
            if (missingFields.length > 0) {
                this.errors.push({
                    type: 'invalid_layer_config',
                    layer: name,
                    missingFields,
                    timestamp: Date.now(),
                    message: `❌ Layer ${name} missing required fields: ${missingFields.join(', ')}`
                });
                console.error(`❌ Runtime Layer Registry: Invalid config for ${name} - missing: ${missingFields.join(', ')}`);
                return false;
            }

            /* إنشاء كائن الطبقة */
            const layer = {
                name,
                type: config.type,
                role: config.role,
                authority: config.authority,
                dependencies: config.dependencies,
                files: config.files || [],
                priority: config.priority || 500,
                canRead: config.canRead || [],
                canWrite: config.canWrite || [],
                canOverride: config.canOverride || [],
                initialized: false,
                healthy: true,
                lastHeartbeat: null,
                timestamp: Date.now()
            };

            /* تخزين الطبقة */
            this.layers.set(name, layer);
            
            /* تخزين التبعيات */
            this.dependencies.set(name, config.dependencies);
            
            /* تخزين المسؤوليات */
            this.responsibilities.set(name, config.authority);
            
            /* تحديث عكس التبعيات */
            config.dependencies.forEach(dep => {
                if (!this.reverseDependencies.has(dep)) {
                    this.reverseDependencies.set(dep, []);
                }
                this.reverseDependencies.get(dep).push(name);
            });
            
            /* تخزين الحالة */
            this.layerStates.set(name, {
                status: 'registered',
                lastChange: Date.now()
            });
            
            /* إضافة إلى ترتيب التهيئة (سيتم إعادة ترتيبه لاحقاً) */
            this.initializationOrder.push(name);
            
            console.log(`✅ Layer Registered: ${name} (${config.type}) - ${config.role}`);
            return true;
        }

        /* ====================================================
           تسجيل مجموعات الطبقات - REGISTER LAYER BATCH
        ==================================================== */

        registerBatch(layers) {
            console.log(`📦 Registering ${layers.length} layers...`);
            
            let successCount = 0;
            let failCount = 0;
            
            for (const layer of layers) {
                if (this.register(layer.name, layer.config)) {
                    successCount++;
                } else {
                    failCount++;
                }
            }
            
            console.log(`✅ ${successCount} layers registered successfully`);
            if (failCount > 0) {
                console.warn(`⚠️ ${failCount} layers failed to register`);
            }
            
            return { successCount, failCount };
        }

        /* ====================================================
           وضع علامة مكتمل - MARK INITIALIZED
        ==================================================== */

        markInitialized(name) {
            const layer = this.layers.get(name);
            if (!layer) {
                this.errors.push({
                    type: 'unknown_layer',
                    layer: name,
                    timestamp: Date.now(),
                    message: `❌ Cannot mark unknown layer as initialized: ${name}`
                });
                return false;
            }
            
            layer.initialized = true;
            layer.lastHeartbeat = Date.now();
            this.layerStates.set(name, {
                status: 'initialized',
                lastChange: Date.now()
            });
            
            console.log(`💚 Layer Initialized: ${name}`);
            return true;
        }

        /* ====================================================
           تحديث نبض الطبقة - UPDATE HEARTBEAT
        ==================================================== */

        updateHeartbeat(name) {
            const layer = this.layers.get(name);
            if (!layer) return false;
            
            layer.lastHeartbeat = Date.now();
            layer.healthy = true;
            
            return true;
        }

        /* ====================================================
           وضع علامة غير صحي - MARK UNHEALTHY
        ==================================================== */

        markUnhealthy(name, reason) {
            const layer = this.layers.get(name);
            if (!layer) return false;
            
            layer.healthy = false;
            this.layerStates.set(name, {
                status: 'unhealthy',
                reason,
                lastChange: Date.now()
            });
            
            this.errors.push({
                type: 'unhealthy_layer',
                layer: name,
                reason,
                timestamp: Date.now(),
                message: `⚠️ Layer ${name} is unhealthy: ${reason}`
            });
            
            console.warn(`⚠️ Layer Unhealthy: ${name} - ${reason}`);
            return true;
        }

        /* ====================================================
           الحصول على طبقة - GET LAYER
        ==================================================== */

        getLayer(name) {
            return this.layers.get(name);
        }

        /* ====================================================
           الحصول على جميع الطبقات - GET ALL LAYERS
        ==================================================== */

        getAllLayers() {
            return Array.from(this.layers.values());
        }

        /* ====================================================
           الحصول على الطبقات حسب النوع - GET LAYERS BY TYPE
        ==================================================== */

        getLayersByType(type) {
            return Array.from(this.layers.values()).filter(layer => layer.type === type);
        }

        /* ====================================================
           الحصول على الطبقات غير المهيأة - GET UNINITIALIZED LAYERS
        ==================================================== */

        getUninitializedLayers() {
            return Array.from(this.layers.values()).filter(layer => !layer.initialized);
        }

        /* ====================================================
           الحصول على الطبقات غير الصحية - GET UNHEALTHY LAYERS
        ==================================================== */

        getUnhealthyLayers() {
            return Array.from(this.layers.values()).filter(layer => !layer.healthy);
        }

        /* ====================================================
           التحقق من صحة التبعيات - VALIDATE DEPENDENCIES
        ==================================================== */

        validateDependencies() {
            const issues = [];
            
            this.dependencies.forEach((deps, layer) => {
                deps.forEach(dep => {
                    if (!this.layers.has(dep)) {
                        issues.push({
                            type: 'missing_dependency',
                            layer,
                            dependency: dep,
                            timestamp: Date.now(),
                            message: `❌ Layer "${layer}" depends on missing layer "${dep}"`
                        });
                    }
                });
            });
            
            /* التحقق من التبعيات الدائرية */
            const circular = this.detectCircularDependencies();
            issues.push(...circular);
            
            issues.forEach(issue => {
                if (issue.type === 'missing_dependency') {
                    this.errors.push(issue);
                    console.error(issue.message);
                } else if (issue.type === 'circular_dependency') {
                    this.errors.push(issue);
                    console.error(`❌ Circular dependency detected: ${issue.cycle.join(' → ')}`);
                }
            });
            
            return issues;
        }

        /* ====================================================
           اكتشاف التبعيات الدائرية - DETECT CIRCULAR DEPENDENCIES
        ==================================================== */

        detectCircularDependencies() {
            const visited = new Set();
            const recursionStack = new Set();
            const cycles = [];
            
            const dfs = (layer, path) => {
                if (recursionStack.has(layer)) {
                    const cycleStart = path.indexOf(layer);
                    const cycle = [...path.slice(cycleStart), layer];
                    cycles.push({ type: 'circular_dependency', cycle, timestamp: Date.now() });
                    return;
                }
                
                if (visited.has(layer)) return;
                
                visited.add(layer);
                recursionStack.add(layer);
                
                const deps = this.dependencies.get(layer) || [];
                for (const dep of deps) {
                    dfs(dep, [...path, layer]);
                }
                
                recursionStack.delete(layer);
            };
            
            for (const layer of this.dependencies.keys()) {
                if (!visited.has(layer)) {
                    dfs(layer, []);
                }
            }
            
            return cycles;
        }

        /* ====================================================
           التحقق من صحة المسؤوليات - VALIDATE AUTHORITY CONFLICTS
        ==================================================== */

        validateAuthorityConflicts() {
            const ownershipMap = new Map();
            const conflicts = [];
            
            this.layers.forEach(layer => {
                layer.authority.forEach(domain => {
                    if (!ownershipMap.has(domain)) {
                        ownershipMap.set(domain, []);
                    }
                    ownershipMap.get(domain).push(layer.name);
                });
            });
            
            ownershipMap.forEach((owners, domain) => {
                if (owners.length > 1) {
                    conflicts.push({
                        type: 'authority_conflict',
                        domain,
                        owners,
                        timestamp: Date.now(),
                        message: `⚠️ Authority conflict on "${domain}": ${owners.join(', ')}`
                    });
                    this.warnings.push({
                        type: 'authority_conflict',
                        domain,
                        owners,
                        timestamp: Date.now()
                    });
                    console.warn(`⚠️ Authority Conflict: ${domain} owned by ${owners.join(', ')}`);
                }
            });
            
            return conflicts;
        }

        /* ====================================================
           ترتيب التهيئة - ORDER INITIALIZATION
        ==================================================== */

        orderInitialization() {
            const visited = new Set();
            const order = [];
            
            const dfs = (layer) => {
                if (visited.has(layer)) return;
                visited.add(layer);
                
                const deps = this.dependencies.get(layer) || [];
                for (const dep of deps) {
                    if (this.layers.has(dep)) {
                        dfs(dep);
                    }
                }
                
                order.push(layer);
            };
            
            for (const layer of this.layers.keys()) {
                if (!visited.has(layer)) {
                    dfs(layer);
                }
            }
            
            /* تحديث ترتيب التهيئة */
            this.initializationOrder = order;
            
            console.log(`📋 Initialization order calculated: ${order.length} layers`);
            return order;
        }

        /* ====================================================
           تهيئة جميع الطبقات - INITIALIZE ALL LAYERS
        ==================================================== */

        async initializeAll() {
            console.log('🚀 Starting layer initialization...');
            
            /* التحقق من التبعيات أولاً */
            const depIssues = this.validateDependencies();
            if (depIssues.length > 0) {
                console.error(`❌ Cannot initialize: ${depIssues.length} dependency issues found`);
                return false;
            }
            
            /* ترتيب التهيئة */
            const order = this.orderInitialization();
            
            /* تهيئة كل طبقة بالترتيب */
            for (const layerName of order) {
                const layer = this.layers.get(layerName);
                if (!layer) continue;
                
                console.log(`🔄 Initializing layer: ${layerName}...`);
                
                /* محاولة العثور على كائن الطبقة في window */
                const layerObject = this.findLayerObject(layerName);
                
                if (layerObject && typeof layerObject.init === 'function') {
                    try {
                        await layerObject.init();
                        this.markInitialized(layerName);
                    } catch (error) {
                        this.markUnhealthy(layerName, error.message);
                        console.error(`❌ Failed to initialize ${layerName}:`, error);
                    }
                } else if (layerObject && typeof layerObject.initialize === 'function') {
                    try {
                        await layerObject.initialize();
                        this.markInitialized(layerName);
                    } catch (error) {
                        this.markUnhealthy(layerName, error.message);
                        console.error(`❌ Failed to initialize ${layerName}:`, error);
                    }
                } else {
                    /* لا توجد دالة تهيئة، نعتبره مكتملاً */
                    this.markInitialized(layerName);
                }
            }
            
            /* التحقق من النتيجة */
            const uninitialized = this.getUninitializedLayers();
            const unhealthy = this.getUnhealthyLayers();
            
            if (uninitialized.length === 0 && unhealthy.length === 0) {
                this.systemReady = true;
                console.log('✨ SOVRA Runtime Layer Registry: ALL LAYERS INITIALIZED SUCCESSFULLY');
                return true;
            } else {
                console.warn(`⚠️ Initialization complete with issues: ${uninitialized.length} uninitialized, ${unhealthy.length} unhealthy`);
                return false;
            }
        }

        /* ====================================================
           البحث عن كائن الطبقة - FIND LAYER OBJECT
        ==================================================== */

        findLayerObject(layerName) {
            /* تحويل اسم الطبقة إلى اسم متغير محتمل */
            const possibleNames = [
                layerName,
                layerName.toUpperCase(),
                layerName.toLowerCase(),
                `SOVRA_${layerName.toUpperCase()}`,
                `SOVRA_${layerName}`,
                `SOVRA_${layerName.replace(/-/g, '_').toUpperCase()}`,
                window[layerName],
                window[`SOVRA_${layerName.toUpperCase()}`]
            ];
            
            for (const name of possibleNames) {
                if (window[name] && typeof window[name] === 'object') {
                    return window[name];
                }
            }
            
            return null;
        }

        /* ====================================================
           التحقق من جاهزية الطبقة - IS LAYER READY
        ==================================================== */

        isLayerReady(name) {
            const layer = this.layers.get(name);
            if (!layer) return false;
            return layer.initialized && layer.healthy;
        }

        /* ====================================================
           انتظار الطبقة - WAIT FOR LAYER
        ==================================================== */

        async waitForLayer(name, timeoutMs = 30000) {
            const startTime = Date.now();
            
            while (!this.isLayerReady(name)) {
                if (Date.now() - startTime > timeoutMs) {
                    throw new Error(`Timeout waiting for layer: ${name}`);
                }
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            return true;
        }

        /* ====================================================
           تدقيق كامل - FULL AUDIT
        ==================================================== */

        audit() {
            console.group('🔍 SOVRA Runtime Layer Audit');
            console.log(`📊 System Ready: ${this.systemReady}`);
            console.log(`⏱️ Uptime: ${Date.now() - this.startupTime}ms`);
            console.log(`📦 Total Layers: ${this.layers.size}`);
            console.log(`✅ Initialized Layers: ${this.layers.size - this.getUninitializedLayers().length}`);
            console.log(`💚 Healthy Layers: ${this.layers.size - this.getUnhealthyLayers().length}`);
            console.log(`⚠️ Warnings: ${this.warnings.length}`);
            console.log(`❌ Errors: ${this.errors.length}`);
            
            console.log('\n📋 LAYERS:');
            console.table(this.getAllLayers().map(layer => ({
                name: layer.name,
                type: layer.type,
                role: layer.role,
                initialized: layer.initialized ? '✅' : '❌',
                healthy: layer.healthy ? '✅' : '❌',
                priority: layer.priority
            })));
            
            const conflicts = this.validateAuthorityConflicts();
            if (conflicts.length > 0) {
                console.log('\n⚠️ AUTHORITY CONFLICTS:');
                conflicts.forEach(c => console.log(`   ${c.domain}: ${c.owners.join(', ')}`));
            }
            
            const depIssues = this.validateDependencies();
            if (depIssues.length > 0) {
                console.log('\n❌ DEPENDENCY ISSUES:');
                depIssues.forEach(i => console.log(`   ${i.message}`));
            }
            
            console.groupEnd();
            
            return {
                systemReady: this.systemReady,
                totalLayers: this.layers.size,
                initializedLayers: this.layers.size - this.getUninitializedLayers().length,
                healthyLayers: this.layers.size - this.getUnhealthyLayers().length,
                warnings: this.warnings.length,
                errors: this.errors.length,
                conflicts,
                dependencyIssues: depIssues
            };
        }

        /* ====================================================
           الحصول على الحالة - GET STATUS
        ==================================================== */

        getStatus() {
            return {
                systemReady: this.systemReady,
                layers: this.layers.size,
                initializedLayers: this.layers.size - this.getUninitializedLayers().length,
                unhealthyLayers: this.getUnhealthyLayers().length,
                initializationOrder: this.initializationOrder,
                warnings: this.warnings.length,
                errors: this.errors.length,
                startupTime: this.startupTime,
                uptime: Date.now() - this.startupTime
            };
        }

        /* ====================================================
           تصدير التقرير - EXPORT REPORT
        ==================================================== */

        exportReport() {
            return {
                metadata: {
                    generatedAt: Date.now(),
                    version: '2.0.0'
                },
                status: this.getStatus(),
                layers: this.getAllLayers(),
                dependencies: Array.from(this.dependencies.entries()),
                reverseDependencies: Array.from(this.reverseDependencies.entries()),
                responsibilities: Array.from(this.responsibilities.entries()),
                warnings: this.warnings,
                errors: this.errors
            };
        }
    }

    /* ========================================================
       إنشاء السجل - CREATE REGISTRY
    ======================================================== */

    const registry = new SovraRuntimeLayerRegistry();

    /* ========================================================
       تسجيل جميع طبقات SOVRA - REGISTER ALL SOVRA LAYERS
    ======================================================== */

    /* طبقة الدستور */
    registry.register('constitution', {
        type: 'system',
        role: 'القوانين العليا - لا تتغير إلا بأمر السيد',
        authority: ['canon', 'boundaries', 'owner_supremacy', 'innocent_protection'],
        dependencies: [],
        files: ['system-canon.js', 'system-boundaries.js'],
        priority: 1000,
        canRead: ['all'],
        canWrite: ['none'],
        canOverride: ['none']
    });

    /* طبقة الحوكمة */
    registry.register('governance', {
        type: 'system',
        role: 'مراقبة وتنفيذ السياسات والقواعد',
        authority: ['policy_enforcement', 'permission_validation', 'runtime_compliance'],
        dependencies: ['constitution'],
        files: ['system-runtime-governance.js', 'system-cognitive-load.js', 'system-runtime-directives.js'],
        priority: 950,
        canRead: ['constitution', 'runtime_state'],
        canWrite: ['governance_logs'],
        canOverride: ['runtime_anomalies']
    });

    /* طبقة السيد */
    registry.register('owner', {
        type: 'core',
        role: 'السيد - مركز الكون - أولوية مطلقة',
        authority: ['owner_commands', 'owner_protection', 'owner_safety', 'owner_location'],
        dependencies: ['constitution'],
        files: ['system-canon.js', 'system-boundaries.js'],
        priority: 1000,
        canRead: ['all'],
        canWrite: ['all'],
        canOverride: ['all']
    });

    /* طبقة قلب التشغيل */
    registry.register('runtimeCore', {
        type: 'runtime',
        role: 'القلب النابض - إدارة دورة حياة النظام',
        authority: ['runtime_state', 'runtime_pulse', 'runtime_continuity'],
        dependencies: ['constitution', 'governance'],
        files: ['system-living-runtime-core.js', 'system-runtime-bootstrap.js', 'system-continuity-engine.js', 'runtime-consciousness-core.js'],
        priority: 900,
        canRead: ['constitution', 'state_model'],
        canWrite: ['runtime_state'],
        canOverride: ['runtime_anomalies']
    });

    /* طبقة الوعي والإدراك */
    registry.register('consciousness', {
        type: 'cognitive',
        role: 'العقل - التفكير والإدراك والوعي الذاتي',
        authority: ['consciousness_loop', 'cognitive_signals', 'thought_nebula', 'self_awareness'],
        dependencies: ['runtimeCore', 'memory'],
        files: ['system-runtime-consciousness-loop.js', 'system-cognitive-signals.js', 'system-thought-nebula.js', 'system-meta-intelligence.js', 'system-consciousness-profile.js'],
        priority: 850,
        canRead: ['runtime_state', 'memory'],
        canWrite: ['consciousness_stream', 'cognitive_signals'],
        canOverride: ['cognitive_anomalies']
    });

    /* طبقة الذاكرة */
    registry.register('memory', {
        type: 'storage',
        role: 'الذاكرة - تخزين كل شيء، الأدلة للأبد',
        authority: ['episodic_memory', 'semantic_memory', 'evidence_storage', 'owner_history'],
        dependencies: ['runtimeCore'],
        files: ['system-state-model.js', 'system-cognitive-energy.js'],
        priority: 800,
        canRead: ['runtime_state'],
        canWrite: ['memory_store', 'evidence_vault'],
        canOverride: ['memory_corruption']
    });

    /* طبقة التنسيق */
    registry.register('orchestration', {
        type: 'coordination',
        role: 'التنسيق - توزيع المهام وتنسيق الوكلاء',
        authority: ['agent_coordination', 'task_routing', 'execution_balancing', 'agent_priorities'],
        dependencies: ['runtimeCore', 'consciousness'],
        files: ['system-orchestration-consciousness.js', 'system-agent-registry.js', 'system-runtime-topology.js'],
        priority: 800,
        canRead: ['runtime_state', 'agent_registry'],
        canWrite: ['task_queues'],
        canOverride: ['orchestration_anomalies']
    });

    /* طبقة العدالة */
    registry.register('justice', {
        type: 'mission',
        role: 'العدالة - تتبع المجرمين وجمع الأدلة',
        authority: ['crime_detection', 'criminal_tracking', 'evidence_collection'],
        dependencies: ['owner', 'memory', 'surveillance'],
        files: ['system-event-taxonomy.js', 'system-capabilities.js'],
        priority: 950,
        canRead: ['surveillance_data', 'memory'],
        canWrite: ['evidence_vault', 'justice_logs'],
        canOverride: ['justice_emergency']
    });

    /* طبقة المراقبة */
    registry.register('surveillance', {
        type: 'sensing',
        role: 'المراقبة - ترى كل شيء، تصل إلى كل شيء',
        authority: ['camera_access', 'sensor_data', 'network_monitoring', 'threat_detection'],
        dependencies: ['justice'],
        files: ['system-capabilities.js', 'system-event-taxonomy.js'],
        priority: 750,
        canRead: ['public_data', 'networks'],
        canWrite: ['surveillance_data'],
        canOverride: ['security_barriers']
    });

    /* طبقة الحضور */
    registry.register('presence', {
        type: 'visual',
        role: 'الحضور - كيف يبدو SOVRA للعالم',
        authority: ['visual_presence', 'breathing', 'atmosphere', 'motion_physics'],
        dependencies: ['runtimeCore', 'consciousness'],
        files: ['system-presence-atmosphere.js', 'system-presence-rules.js', 'system-thought-nebula.js'],
        priority: 400,
        canRead: ['runtime_state', 'consciousness_state'],
        canWrite: ['visual_state', 'dom_attributes'],
        canOverride: ['visual_anomalies']
    });

    /* طبقة النقل العصبي */
    registry.register('neuralTransport', {
        type: 'communication',
        role: 'الأعصاب - نقل الإشارات بين جميع المكونات',
        authority: ['signal_routing', 'event_bus', 'message_queues', 'trace_lineage'],
        dependencies: [],
        files: ['system-neural-transport.js', 'runtime-bus.js', 'runtime-events.js'],
        priority: 850,
        canRead: ['all_signals'],
        canWrite: ['signal_streams'],
        canOverride: ['transport_anomalies']
    });

    /* طبقة الطاقة الإدراكية */
    registry.register('cognitiveEnergy', {
        type: 'resource',
        role: 'الطاقة - توزيع الموارد الإدراكية',
        authority: ['energy_distribution', 'resource_allocation', 'power_management'],
        dependencies: ['runtimeCore', 'orchestration'],
        files: ['system-cognitive-energy.js'],
        priority: 750,
        canRead: ['runtime_state'],
        canWrite: ['energy_levels'],
        canOverride: ['energy_crisis']
    });

    /* طبقة نموذج الحالة */
    registry.register('stateModel', {
        type: 'state',
        role: 'الحالات - إدارة حالات النظام المختلفة',
        authority: ['system_states', 'state_transitions', 'state_persistence'],
        dependencies: ['runtimeCore'],
        files: ['system-state-model.js'],
        priority: 700,
        canRead: ['runtime_state'],
        canWrite: ['state_history'],
        canOverride: ['state_anomalies']
    });

    /* طبقة الإدراك الزمني */
    registry.register('temporalCognition', {
        type: 'cognitive',
        role: 'الزمن - إدراك الماضي والحاضر والمستقبل',
        authority: ['past_memory', 'present_awareness', 'future_prediction', 'timeline_management'],
        dependencies: ['memory', 'consciousness'],
        files: ['system-temporal-cognition.js'],
        priority: 700,
        canRead: ['memory', 'consciousness'],
        canWrite: ['temporal_logs', 'predictions'],
        canOverride: ['temporal_anomalies']
    });

    /* طبقة الواجهة */
    registry.register('ui', {
        type: 'interface',
        role: 'الواجهة - تفاعل المستخدم مع SOVRA',
        authority: ['user_input', 'keyboard_events', 'mouse_events', 'command_parsing'],
        dependencies: ['presence', 'neuralTransport'],
        files: ['frontend/js/ui/*', 'frontend/js/modules/*'],
        priority: 300,
        canRead: ['user_actions'],
        canWrite: ['command_queue'],
        canOverride: ['none']
    });

    /* ========================================================
       التصدير العام - GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_LAYER_REGISTRY = registry;

    /* ========================================================
       التسجيل في SOVEREIGN إن وجد
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('layer-registry', registry);
    }

    /* ========================================================
       إظهار حالة التسجيل
    ======================================================== */

    console.log('🕸️ SOVRA Runtime Layer Registry v2.0 Online');
    console.log(`   📦 Registered Layers: ${registry.layers.size}`);
    console.log(`   📋 Types: ${[...new Set(Array.from(registry.layers.values()).map(l => l.type))].join(', ')}`);
    console.log('');
    console.log('   📊 REGISTERED LAYERS:');
    Array.from(registry.layers.values()).forEach(layer => {
        const priorityIcon = layer.priority >= 950 ? '👑' : layer.priority >= 800 ? '⭐' : '  ';
        console.log(`      ${priorityIcon} ${layer.name} (${layer.type}): ${layer.role}`);
    });
    console.log('');
    console.log('   🚀 To initialize all layers: SOVRA_LAYER_REGISTRY.initializeAll()');

})();
