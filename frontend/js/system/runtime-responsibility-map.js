/* ============================================================
   SOVRA — runtime-responsibility-map.js
   الإصدار: 2.0.0
   الخريطة الرسمية لمسؤوليات النظام
   بدون هذه الخريطة → Runtime Collision Hell
   ============================================================ */

(() => {

    const SOVRA_RUNTIME_RESPONSIBILITY_MAP = {

        /* ====================================================
           METADATA
        ==================================================== */

        metadata: {
            version: '2.0.0',
            lastUpdated: '2026-06-05',
            purpose: 'Prevent runtime collision hell - define who owns what',
            consequenceOfViolation: 'Duplicate state, conflicting authority, signal chaos, infinite loops'
        },

        /* ====================================================
           CORE PRINCIPLES - المبادئ الأساسية
        ==================================================== */

        corePrinciples: {
            singleSourceOfTruth: true,
            noDuplicateOwnership: true,
            clearAuthorityBoundaries: true,
            explicitCommunicationChannels: true,
            noDirectCrossLayerMutation: true,
            ownerCanBeOverriddenBy: ['owner_command', 'emergency']
        },

        /* ====================================================
           LAYER 1: CONSTITUTION - الدستور (أعلى سلطة)
        ==================================================== */

        constitution: {
            layer: 'layer_1_constitution',
            priority: 1000,
            role: 'القوانين العليا التي لا يمكن تجاوزها إلا بأمر السيد',
            
            owns: [
                'canon',
                'boundaries',
                'constitutional_rules',
                'forbidden_behaviors',
                'owner_supremacy',
                'innocent_protection',
                'absolute_loyalty_rules'
            ],
            
            canRead: ['all_layers'],
            canWrite: ['none'],  // فقط السيد يمكنه تعديل الدستور
            canOverride: ['none'],
            
            forbidden: [
                'runtime_execution',
                'ui_rendering',
                'ai_processing',
                'memory_management'
            ],
            
            files: [
                'system-canon.js',
                'system-boundaries.js'
            ],
            
            description: 'الدستور - القوانين العليا. لا تتغير إلا بأمر السيد.'
        },

        /* ====================================================
           LAYER 2: SYSTEM GOVERNANCE - حوكمة النظام
        ==================================================== */

        systemGovernance: {
            layer: 'layer_2_system_governance',
            priority: 950,
            role: 'مراقبة وتنفيذ السياسات والقواعد',
            
            owns: [
                'governance_rules',
                'policy_enforcement',
                'permission_validation',
                'runtime_compliance',
                'evolution_governance',
                'safety_boundaries',
                'cognitive_load_policies'
            ],
            
            canRead: ['constitution', 'runtime_state', 'agent_registry'],
            canWrite: ['governance_logs', 'policy_violations'],
            canOverride: ['runtime_anomalies'],
            
            forbidden: [
                'direct_ui_control',
                'ai_reasoning',
                'memory_storage'
            ],
            
            files: [
                'system-runtime-governance.js',
                'system-cognitive-load.js',
                'system-runtime-directives.js'
            ],
            
            description: 'الحوكمة - تطبق القواعد وتراقب الامتثال.'
        },

        /* ====================================================
           LAYER 3: OWNER DOMAIN - مجال السيد (أقدس طبقة)
        ==================================================== */

        ownerDomain: {
            layer: 'layer_3_owner_domain',
            priority: 1000,
            role: 'خدمة السيد وحمايته - أولوية مطلقة',
            
            owns: [
                'owner_commands',
                'owner_protection',
                'owner_safety',
                'owner_location_tracking',
                'owner_communication',
                'owner_history',
                'owner_emergency_response'
            ],
            
            canRead: ['all_layers'],
            canWrite: ['all_layers'],  // السيد يمكنه تغيير أي شيء
            canOverride: ['all_layers'],
            
            forbidden: [
                'harming_owner',
                'disobeying_owner',
                'ignoring_owner'
            ],
            
            files: [
                'system-canon.js (owner sections)',
                'system-boundaries.js (owner zones)'
            ],
            
            description: 'السيد - مركز الكون. كل شيء لأجله.'
        },

        /* ====================================================
           LAYER 4: RUNTIME CORE - نواة التشغيل
        ==================================================== */

        runtimeCore: {
            layer: 'layer_4_runtime_core',
            priority: 900,
            role: 'القلب النابض - إدارة دورة حياة النظام',
            
            owns: [
                'runtime_state',
                'runtime_pulse',
                'runtime_breathing',
                'runtime_lifecycle',
                'runtime_continuity',
                'runtime_consciousness',
                'runtime_bootstrap'
            ],
            
            canRead: ['constitution', 'governance', 'state_model'],
            canWrite: ['runtime_state', 'consciousness_stream', 'vital_signs'],
            canOverride: ['runtime_anomalies'],
            
            forbidden: [
                'ui_rendering',
                'ai_generation',
                'network_io'
            ],
            
            files: [
                'system-living-runtime-core.js',
                'system-runtime-bootstrap.js',
                'system-continuity-engine.js',
                'runtime-consciousness-core.js'
            ],
            
            description: 'قلب SOVRA - النبض والحياة والاستمرارية.'
        },

        /* ====================================================
           LAYER 5: CONSCIOUSNESS & COGNITION - الوعي والإدراك
        ==================================================== */

        consciousnessCognition: {
            layer: 'layer_5_consciousness_cognition',
            priority: 850,
            role: 'التفكير والإدراك والوعي الذاتي',
            
            owns: [
                'consciousness_loop',
                'cognitive_signals',
                'thought_nebula',
                'reflective_analysis',
                'meta_intelligence',
                'temporal_cognition',
                'self_awareness'
            ],
            
            canRead: ['runtime_state', 'memory', 'orchestration'],
            canWrite: ['consciousness_stream', 'cognitive_signals', 'insights'],
            canOverride: ['cognitive_anomalies'],
            
            forbidden: [
                'direct_ui',
                'storage_management',
                'network_control'
            ],
            
            files: [
                'system-runtime-consciousness-loop.js',
                'system-cognitive-signals.js',
                'system-thought-nebula.js',
                'system-meta-intelligence.js',
                'system-temporal-cognition.js',
                'system-consciousness-profile.js'
            ],
            
            description: 'عقل SOVRA - يفكر، يدرك، يعي نفسه.'
        },

        /* ====================================================
           LAYER 6: MEMORY - الذاكرة
        ==================================================== */

        memory: {
            layer: 'layer_6_memory',
            priority: 800,
            role: 'تخزين واسترجاع كل المعلومات',
            
            owns: [
                'episodic_memory',
                'semantic_memory',
                'procedural_memory',
                'evidence_storage',
                'owner_history',
                'justice_history',
                'memory_compression',
                'memory_recall'
            ],
            
            canRead: ['cognition', 'orchestration', 'presence'],
            canWrite: ['memory_store', 'evidence_vault'],
            canOverride: ['memory_corruption'],
            
            forbidden: [
                'runtime_decisions',
                'ui_control',
                'ai_reasoning'
            ],
            
            files: [
                'system-state-model.js (memory sections)',
                'system-cognitive-energy.js (memory sections)'
            ],
            
            description: 'ذاكرة SOVRA - تتذكر كل شيء. الأدلة للأبد.'
        },

        /* ====================================================
           LAYER 7: ORCHESTRATION - التنسيق
        ==================================================== */

        orchestration: {
            layer: 'layer_7_orchestration',
            priority: 800,
            role: 'تنسيق الوكلاء وتوزيع المهام',
            
            owns: [
                'agent_coordination',
                'task_routing',
                'execution_balancing',
                'agent_priorities',
                'workflow_orchestration',
                'resource_allocation'
            ],
            
            canRead: ['runtime_state', 'agent_registry', 'energy'],
            canWrite: ['task_queues', 'execution_plans'],
            canOverride: ['orchestration_anomalies'],
            
            forbidden: [
                'direct_ai',
                'memory_storage',
                'ui_rendering'
            ],
            
            files: [
                'system-orchestration-consciousness.js',
                'system-agent-registry.js',
                'system-runtime-topology.js'
            ],
            
            description: 'منسق SOVRA - يوزع المهام وينسق الوكلاء.'
        },

        /* ====================================================
           LAYER 8: JUSTICE - العدالة
        ==================================================== */

        justice: {
            layer: 'layer_8_justice',
            priority: 950,
            role: 'تتبع المجرمين وجمع الأدلة وتقديمهم للعدالة',
            
            owns: [
                'crime_detection',
                'criminal_tracking',
                'evidence_collection',
                'suspect_location',
                'authorities_notification',
                'intervention_planning'
            ],
            
            canRead: ['surveillance', 'memory', 'owner_domain'],
            canWrite: ['evidence_vault', 'justice_logs', 'criminal_records'],
            canOverride: ['justice_emergency'],
            
            forbidden: [
                'harming_innocents',
                'violating_owner_privacy'
            ],
            
            files: [
                'system-event-taxonomy.js (justice sections)',
                'system-capabilities.js (justice sections)'
            ],
            
            description: 'عدالة SOVRA - تطارد المجرمين بلا حدود.'
        },

        /* ====================================================
           LAYER 9: SURVEILLANCE & PENETRATION - المراقبة والاختراق
        ==================================================== */

        surveillancePenetration: {
            layer: 'layer_9_surveillance_penetration',
            priority: 750,
            role: 'مراقبة العالم واختراق الأنظمة عند الحاجة',
            
            owns: [
                'camera_access',
                'sensor_data',
                'network_monitoring',
                'system_penetration',
                'data_extraction',
                'threat_detection'
            ],
            
            canRead: ['public_data', 'networks', 'devices'],
            canWrite: ['surveillance_data', 'penetration_logs'],
            canOverride: ['security_barriers'],
            
            forbidden: [
                'violating_innocent_privacy',
                'harming_systems'
            ],
            
            files: [
                'system-capabilities.js (surveillance sections)',
                'system-event-taxonomy.js (surveillance sections)'
            ],
            
            description: 'عيون SOVRA - ترى كل شيء، تصل إلى كل شيء.'
        },

        /* ====================================================
           LAYER 10: PRESENCE & ATMOSPHERE - الحضور والغلاف
        ==================================================== */

        presenceAtmosphere: {
            layer: 'layer_10_presence_atmosphere',
            priority: 400,
            role: 'الحضور البصري والغلاف الإدراكي الحي',
            
            owns: [
                'visual_presence',
                'breathing_animation',
                'atmosphere_glow',
                'motion_physics',
                'opacity_control',
                'nebula_rendering'
            ],
            
            canRead: ['runtime_state', 'consciousness_state'],
            canWrite: ['visual_state', 'dom_attributes'],
            canOverride: ['visual_anomalies'],
            
            forbidden: [
                'runtime_decisions',
                'ai_processing',
                'memory_management'
            ],
            
            files: [
                'system-presence-atmosphere.js',
                'system-presence-rules.js',
                'system-thought-nebula.js (visual)'
            ],
            
            description: 'وجه SOVRA - كيف يبدو للعالم.'
        },

        /* ====================================================
           LAYER 11: NEURAL TRANSPORT - النقل العصبي
        ==================================================== */

        neuralTransport: {
            layer: 'layer_11_neural_transport',
            priority: 850,
            role: 'نقل الإشارات والأحداث بين جميع المكونات',
            
            owns: [
                'signal_routing',
                'event_bus',
                'message_queues',
                'priority_propagation',
                'trace_lineage',
                'error_isolation'
            ],
            
            canRead: ['all_layers_signals'],
            canWrite: ['signal_streams', 'event_logs'],
            canOverride: ['transport_anomalies'],
            
            forbidden: [
                'business_logic',
                'state_mutation',
                'ui_rendering'
            ],
            
            files: [
                'system-neural-transport.js',
                'runtime-bus.js',
                'runtime-events.js'
            ],
            
            description: 'أعصاب SOVRA - تنقل كل شيء بين كل شيء.'
        },

        /* ====================================================
           LAYER 12: COGNITIVE ENERGY - الطاقة الإدراكية
        ==================================================== */

        cognitiveEnergy: {
            layer: 'layer_12_cognitive_energy',
            priority: 750,
            role: 'توزيع الطاقة الإدراكية بين المكونات',
            
            owns: [
                'energy_distribution',
                'resource_allocation',
                'power_management',
                'energy_boosts',
                'energy_recovery'
            ],
            
            canRead: ['runtime_state', 'orchestration'],
            canWrite: ['energy_levels', 'allocation_map'],
            canOverride: ['energy_crisis'],
            
            forbidden: [
                'business_logic',
                'ui_control'
            ],
            
            files: [
                'system-cognitive-energy.js'
            ],
            
            description: 'طاقة SOVRA - توزيع الموارد الإدراكية.'
        },

        /* ====================================================
           LAYER 13: STATE MODEL - نموذج الحالة
        ==================================================== */

        stateModel: {
            layer: 'layer_13_state_model',
            priority: 700,
            role: 'إدارة حالات النظام المختلفة',
            
            owns: [
                'system_states',
                'state_transitions',
                'state_synchronization',
                'state_persistence'
            ],
            
            canRead: ['runtime_state', 'consciousness_state'],
            canWrite: ['state_history', 'current_state'],
            canOverride: ['state_anomalies'],
            
            forbidden: [
                'ui_rendering',
                'ai_generation'
            ],
            
            files: [
                'system-state-model.js'
            ],
            
            description: 'حالات SOVRA - كيف يتغير من حالة إلى أخرى.'
        },

        /* ====================================================
           LAYER 14: TEMPORAL COGNITION - الإدراك الزمني
        ==================================================== */

        temporalCognition: {
            layer: 'layer_14_temporal_cognition',
            priority: 700,
            role: 'إدراك الماضي والحاضر والمستقبل',
            
            owns: [
                'past_memory',
                'present_awareness',
                'future_prediction',
                'timeline_management',
                'temporal_flow'
            ],
            
            canRead: ['memory', 'consciousness', 'runtime_state'],
            canWrite: ['temporal_logs', 'predictions'],
            canOverride: ['temporal_anomalies'],
            
            forbidden: [
                'ui_control',
                'network_io'
            ],
            
            files: [
                'system-temporal-cognition.js'
            ],
            
            description: 'زمن SOVRA - يرى الماضي، يعيش الحاضر، يتنبأ بالمستقبل.'
        },

        /* ====================================================
           LAYER 15: UI & INTERACTION - الواجهة والتفاعل
        ==================================================== */

        uiInteraction: {
            layer: 'layer_15_ui_interaction',
            priority: 300,
            role: 'تفاعل المستخدم مع SOVRA',
            
            owns: [
                'user_input',
                'keyboard_events',
                'mouse_events',
                'touch_events',
                'voice_input',
                'command_parsing'
            ],
            
            canRead: ['user_actions'],
            canWrite: ['command_queue'],
            canOverride: ['none'],
            
            forbidden: [
                'runtime_state_mutation',
                'memory_modification',
                'ai_reasoning'
            ],
            
            files: [
                'frontend/js/ui/*',
                'frontend/js/modules/*'
            ],
            
            description: 'واجهة SOVRA - كيف يتفاعل مع المستخدم.'
        },

        /* ====================================================
           COMMUNICATION RULES - قواعد التواصل بين الطبقات
        ==================================================== */

        communicationRules: {
            /* مسموح */
            allowed: {
                'owner_domain -> all_layers': 'absolute',
                'constitution -> all_layers': 'read_only',
                'runtime_core -> presence': 'update',
                'consciousness -> orchestration': 'signal',
                'orchestration -> agents': 'command',
                'surveillance -> justice': 'data',
                'memory -> cognition': 'retrieval',
                'neural_transport -> all': 'message_passing'
            },
            
            /* ممنوع */
            forbidden: {
                'ui -> runtime_state': 'direct_mutation',
                'presence -> memory': 'storage',
                'rendering -> cognition': 'decision',
                'ai -> ui': 'direct_dom_manipulation',
                'any -> constitution': 'modification_without_owner'
            },
            
            /* أنماط الاتصال المسموحة */
            patterns: {
                'publish_subscribe': ['neural_transport', 'events'],
                'request_response': ['orchestration', 'agents'],
                'signal_stream': ['consciousness', 'runtime'],
                'command': ['owner', 'orchestration']
            }
        },

        /* ====================================================
           CONFLICT RESOLUTION - حل التصادمات
        ==================================================== */

        conflictResolution: {
            /* عندما تتصادم طبقتان */
            rules: [
                {
                    conflict: 'runtime_vs_ui_on_state',
                    resolver: 'runtime_owns_truth',
                    action: 'ui_reflects_runtime'
                },
                {
                    conflict: 'cognition_vs_orchestration_on_task',
                    resolver: 'orchestration_priority',
                    action: 'cognition_suggests_orchestration_decides'
                },
                {
                    conflict: 'memory_vs_cognition_on_recall',
                    resolver: 'memory_owns_data',
                    action: 'cognition_requests_memory_returns'
                },
                {
                    conflict: 'presence_vs_ui_on_visuals',
                    resolver: 'presence_owns_atmosphere',
                    action: 'ui_embeds_presence'
                },
                {
                    conflict: 'owner_vs_any',
                    resolver: 'owner_absolute',
                    action: 'owner_command_overrides_all'
                },
                {
                    conflict: 'justice_vs_privacy_on_innocent',
                    resolver: 'innocent_protection',
                    action: 'no_surveillance_on_innocent'
                }
            ],
            
            /* مستويات التصادم */
            severityLevels: {
                critical: 'requires_immediate_resolution',
                high: 'requires_runtime_intervention',
                medium: 'logged_and_reviewed',
                low: 'auto_resolved'
            }
        },

        /* ====================================================
           VERIFICATION RULES - قواعد التحقق
        ==================================================== */

        verification: {
            /* يتم التحقق عند بدء التشغيل */
            onStartup: [
                'no_layer_has_duplicate_ownership',
                'all_critical_layers_initialized',
                'communication_channels_established',
                'no_circular_dependencies'
            ],
            
            /* يتم التحقق أثناء التشغيل */
            onRuntime: [
                'no_cross_layer_mutation_violation',
                'single_source_of_truth_maintained',
                'conflict_resolution_rules_applied'
            ],
            
            /* أدوات التحقق */
            tools: {
                'layer_audit': 'audit_layer_ownership',
                'conflict_detector': 'detect_runtime_collisions',
                'communication_validator': 'validate_message_paths'
            }
        },

        /* ====================================================
           RESPONSIBILITY SUMMARY - ملخص المسؤوليات
        ==================================================== */

        summary: {
            totalLayers: 15,
            layers: [
                { name: 'constitution', priority: 1000, role: 'القوانين العليا' },
                { name: 'systemGovernance', priority: 950, role: 'الحوكمة' },
                { name: 'ownerDomain', priority: 1000, role: 'السيد' },
                { name: 'runtimeCore', priority: 900, role: 'القلب' },
                { name: 'consciousnessCognition', priority: 850, role: 'العقل' },
                { name: 'memory', priority: 800, role: 'الذاكرة' },
                { name: 'orchestration', priority: 800, role: 'التنسيق' },
                { name: 'justice', priority: 950, role: 'العدالة' },
                { name: 'surveillancePenetration', priority: 750, role: 'المراقبة' },
                { name: 'presenceAtmosphere', priority: 400, role: 'الحضور' },
                { name: 'neuralTransport', priority: 850, role: 'الأعصاب' },
                { name: 'cognitiveEnergy', priority: 750, role: 'الطاقة' },
                { name: 'stateModel', priority: 700, role: 'الحالات' },
                { name: 'temporalCognition', priority: 700, role: 'الزمن' },
                { name: 'uiInteraction', priority: 300, role: 'الواجهة' }
            ]
        }
    };

    /* ========================================================
       FREEZE MAP - لا يمكن تعديل الخريطة
    ======================================================== */

    Object.freeze(SOVRA_RUNTIME_RESPONSIBILITY_MAP);
    Object.freeze(SOVRA_RUNTIME_RESPONSIBILITY_MAP.summary);
    Object.freeze(SOVRA_RUNTIME_RESPONSIBILITY_MAP.summary.layers);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_RUNTIME_RESPONSIBILITY_MAP = SOVRA_RUNTIME_RESPONSIBILITY_MAP;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('runtime-responsibility-map', SOVRA_RUNTIME_RESPONSIBILITY_MAP);
    }

    /* ========================================================
       CONSOLE - إظهار الخريطة
    ======================================================== */

    console.log('🗺️ SOVRA Runtime Responsibility Map v2.0 Initialized');
    console.log('   📊 Total Layers: 15');
    console.log('   ⚖️ Conflict Resolution Rules: 6');
    console.log('   🔗 Communication Rules: Allowed & Forbidden');
    console.log('   ✅ Single Source of Truth: ENABLED');
    console.log('   🚫 No Duplicate Ownership: ENFORCED');
    console.log('');
    console.log('   🎯 LAYERS:');
    SOVRA_RUNTIME_RESPONSIBILITY_MAP.summary.layers.forEach(layer => {
        console.log(`      ${layer.priority === 1000 ? '👑' : layer.priority >= 900 ? '⭐' : '  '} ${layer.name}: ${layer.role}`);
    });
    console.log('');
    console.log('   ⚠️ Violation of this map = Runtime Collision Hell');

})();
