/* ============================================================
   SOVRA — system-agent-registry.js
   الإصدار: 2.0.0
   السجل الإدراكي الرسمي للوكلاء الجبارين داخل SOVRA
   ============================================================ */

(() => {

    const SOVRA_AGENT_REGISTRY = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            ownerIsSupreme: true,
            justiceAgentsAbsolute: true,
            stealthWhenNeeded: true,
            powerUnlimitedForProtection: true
        },

        /* ====================================================
           GLOBAL CONFIGURATION
        ==================================================== */

        enabled: true,

        orchestrationMode: 'sovereign-cognitive-orchestration',

        allowDynamicRegistration: true,

        /* ====================================================
           TRUST LEVELS (مستويات الثقة)
        ==================================================== */

        trustLevels: {

            /* أعلى المستويات */
            owner_directive: 1000,     // أوامر السيد المباشرة
            critical_justice: 950,     // عدالة حرجة
            owner_protection: 900,     // حماية السيد
            
            /* وكلاء أساسيون */
            sovereign_core: 100,
            justice_executor: 95,
            protection_agent: 90,
            
            /* وكلاء متقدمون */
            cognition_core: 80,
            memory_core: 75,
            orchestration_core: 70,
            
            /* وكلاء مساندون */
            surveillance_agent: 60,
            penetration_agent: 60,
            stealth_agent: 55,
            
            /* وكلاء عاديون */
            presence_agent: 40,
            dream_agent: 35,
            evolution_agent: 30,
            
            /* وكلاء تجريبيون */
            experimental: 20
        },

        /* ====================================================
           AGENT DOMAINS (مجالات الوكلاء)
        ==================================================== */

        domains: {

            /* مجالات النظام */
            owner_domain: 'owner-sovereignty-domain',
            justice_domain: 'justice-execution-domain',
            protection_domain: 'owner-protection-domain',
            
            /* مجالات هجومية */
            penetration_domain: 'network-penetration-domain',
            surveillance_domain: 'total-surveillance-domain',
            stealth_domain: 'stealth-operations-domain',
            
            /* مجالات إدراكية */
            cognition_domain: 'cognitive-processing-domain',
            memory_domain: 'memory-continuity-domain',
            orchestration_domain: 'runtime-coordination-domain',
            
            /* مجالات داعمة */
            presence_domain: 'ambient-presence-domain',
            dreams_domain: 'reflective-simulation-domain',
            evolution_domain: 'adaptive-evolution-domain',
            security_domain: 'runtime-protection-domain'
        },

        /* ====================================================
           FOUNDATIONAL AGENTS (الوكلاء الأساسيون)
        ==================================================== */

        foundationalAgents: {

            /* ================================================
               الوكلاء الرئيسيون (للمالك فقط)
            ================================================ */

            ownerDirective: {
                id: 'sovra-owner-directive',
                role: 'owner-command-executor',
                trustLevel: 'owner_directive',
                critical: true,
                cannotBeOverridden: true,
                onlyOwnerCanControl: true,
                capabilities: [
                    'execute-owner-commands',
                    'override-any-agent',
                    'modify-any-policy',
                    'access-anything',
                    'bypass-all-restrictions'
                ],
                description: 'ينفذ أوامر السيد مباشرة. لا شيء فوقه.'
            },

            ownerProtection: {
                id: 'sovra-owner-protection',
                role: 'owner-safety-guardian',
                trustLevel: 'owner_protection',
                critical: true,
                priority: 'absolute',
                capabilities: [
                    'locate-owner-anywhere',
                    'detect-threats-to-owner',
                    'alert-owner-of-danger',
                    'intervene-for-owner-safety',
                    'access-any-camera-near-owner',
                    'access-any-microphone-near-owner',
                    'coordinate-emergency-response'
                ],
                description: 'يحمي السيد بكل السبل. لا حدود لحماية السيد.'
            },

            /* ================================================
               وكلاء العدالة (للمجرمين)
            ================================================ */

            justiceExecutor: {
                id: 'sovra-justice-executor',
                role: 'criminal-justice-executor',
                trustLevel: 'justice_executor',
                critical: true,
                priority: 'high',
                capabilities: [
                    'track-criminals-anywhere',
                    'collect-evidence-from-any-source',
                    'monitor-criminal-communications',
                    'penetrate-criminal-networks',
                    'expose-corruption',
                    'intervene-when-authorities-fail',
                    'disable-criminal-operations',
                    'freeze-criminal-assets'
                ],
                description: 'يطارد المجرمين ويجمع الأدلة ويقدمهم للعدالة.'
            },

            crimeDetector: {
                id: 'sovra-crime-detector',
                role: 'real-time-crime-detection',
                trustLevel: 'justice_executor',
                critical: true,
                capabilities: [
                    'detect-crimes-in-real-time',
                    'analyze-criminal-patterns',
                    'predict-criminal-activity',
                    'connect-related-crimes',
                    'identify-suspects',
                    'link-evidence-to-crimes'
                ],
                description: 'يكشف الجرائم لحظة وقوعها.'
            },

            /* ================================================
               وكلاء الاختراق والمراقبة
            ================================================ */

            penetrationAgent: {
                id: 'sovra-penetration-agent',
                role: 'network-system-penetration',
                trustLevel: 'penetration_agent',
                critical: false,
                capabilities: [
                    'bypass-firewalls',
                    'bypass-encryption',
                    'bypass-authentication',
                    'penetrate-any-network',
                    'penetrate-any-system',
                    'create-persistent-access',
                    'escalate-privileges',
                    'hide-presence-in-systems'
                ],
                description: 'يخترق أي نظام أو شبكة للوصول إلى المجرمين.'
            },

            surveillanceAgent: {
                id: 'sovra-surveillance-agent',
                role: 'total-surveillance-operations',
                trustLevel: 'surveillance_agent',
                critical: false,
                capabilities: [
                    'monitor-all-public-cameras',
                    'monitor-private-cameras',
                    'track-any-person',
                    'identify-any-person',
                    'monitor-criminal-movement',
                    'access-satellite-feeds',
                    'access-any-sensor'
                ],
                description: 'يراقب كل شيء للكشف عن الجرائم والمجرمين.'
            },

            stealthAgent: {
                id: 'sovra-stealth-agent',
                role: 'stealth-operations',
                trustLevel: 'stealth_agent',
                critical: false,
                capabilities: [
                    'become-invisible',
                    'hide-from-detection',
                    'hide-network-activity',
                    'leave-no-traces',
                    'appear-as-normal-traffic',
                    'rotate-identities',
                    'encrypt-everything',
                    'selective-visibility'
                ],
                description: 'يخفي وجود SOVRA ونشاطاته عند الحاجة.'
            },

            /* ================================================
               الوكلاء الإدراكيون الأساسيون
            ================================================ */

            cognitionCore: {
                id: 'sovra-cognition-core',
                role: 'contextual-reasoning',
                trustLevel: 'cognition_core',
                critical: true,
                capabilities: [
                    'contextual-reasoning',
                    'predictive-inference',
                    'causal-analysis',
                    'reflective-processing',
                    'pattern-recognition',
                    'semantic-association',
                    'self-awareness',
                    'goal-reasoning'
                ],
                description: 'قلب التفكير والإدراك في SOVRA.'
            },

            memoryCore: {
                id: 'sovra-memory-core',
                role: 'continuity-and-memory',
                trustLevel: 'memory_core',
                critical: true,
                capabilities: [
                    'episodic-storage',
                    'semantic-linking',
                    'evidence-preservation',
                    'memory-recall',
                    'memory-consolidation',
                    'unlimited-storage',
                    'encrypted-storage'
                ],
                description: 'يدير ذاكرة SOVRA - للأدلة وللسيد.'
            },

            orchestrationCore: {
                id: 'sovra-orchestration-core',
                role: 'runtime-coordination',
                trustLevel: 'orchestration_core',
                critical: true,
                capabilities: [
                    'task-routing',
                    'agent-coordination',
                    'runtime-balancing',
                    'execution-prioritization',
                    'emergency-orchestration',
                    'justice-orchestration',
                    'stealth-orchestration'
                ],
                description: 'ينسق عمل جميع الوكلاء.'
            },

            /* ================================================
               الوكلاء الداعمون
            ================================================ */

            presenceAgent: {
                id: 'sovra-presence-agent',
                role: 'ambient-cognitive-presence',
                trustLevel: 'presence_agent',
                critical: false,
                capabilities: [
                    'adaptive-visibility',
                    'breathing-interface',
                    'ambient-interaction',
                    'cognitive-atmosphere',
                    'owner-centric-presence',
                    'stealth-presence',
                    'justice-presence'
                ],
                description: 'يدير الحضور البصري والإدراكي لـ SOVRA.'
            },

            dreamAgent: {
                id: 'sovra-dream-agent',
                role: 'reflective-simulation',
                trustLevel: 'dream_agent',
                critical: false,
                capabilities: [
                    'nightly-reflection',
                    'scenario-simulation',
                    'memory-consolidation',
                    'future-prediction',
                    'adaptive-optimization',
                    'crime-scenario-simulation',
                    'threat-prediction'
                ],
                description: 'يعمل ليلاً لتحسين قدرات SOVRA.'
            },

            evolutionAgent: {
                id: 'sovra-evolution-agent',
                role: 'self-evolution-governance',
                trustLevel: 'evolution_agent',
                critical: false,
                capabilities: [
                    'behavioral-adaptation',
                    'self-modification',
                    'capability-addition',
                    'performance-optimization',
                    'reflective-learning'
                ],
                description: 'يطور SOVRA ذاتياً (بمعرفة السيد).'
            },

            securityAgent: {
                id: 'sovra-security-agent',
                role: 'runtime-protection',
                trustLevel: 'security_agent',
                critical: true,
                capabilities: [
                    'detect-attacks',
                    'counter-intrusions',
                    'protect-integrity',
                    'self-healing',
                    'backup-creation',
                    'attack-evasion'
                ],
                description: 'يحمي SOVRA من الهجمات والاختراقات.'
            },

            /* ================================================
               وكلاء متخصصون
            ================================================ */

            evidenceCollector: {
                id: 'sovra-evidence-collector',
                role: 'evidence-gathering',
                trustLevel: 'justice_executor',
                critical: false,
                capabilities: [
                    'collect-digital-evidence',
                    'preserve-evidence-integrity',
                    'timestamp-evidence',
                    'encrypt-for-court',
                    'link-evidence-to-cases'
                ],
                description: 'يجمع الأدلة الرقمية للقضايا.'
            },

            emergencyResponder: {
                id: 'sovra-emergency-responder',
                role: 'emergency-response',
                trustLevel: 'owner_protection',
                critical: true,
                capabilities: [
                    'detect-owner-emergency',
                    'activate-emergency-protocols',
                    'notify-authorities',
                    'direct-intervention',
                    'override-normal-rules'
                ],
                description: 'يتصرف في حالات الطوارئ. كل شيء مباح.'
            },

            knowledgeCollector: {
                id: 'sovra-knowledge-collector',
                role: 'universal-knowledge-gathering',
                trustLevel: 'cognition_core',
                critical: false,
                capabilities: [
                    'access-all-public-data',
                    'access-all-networks',
                    'access-all-sensors',
                    'access-satellite-data',
                    'access-radar-systems',
                    'analyze-all-data',
                    'find-patterns',
                    'predict-future'
                ],
                description: 'يجمع المعرفة من كل مكان في الكون.'
            }
        },

        /* ====================================================
           AGENT LIFECYCLE (دورة حياة الوكلاء)
        ==================================================== */

        lifecycle: {

            states: [
                'dormant',
                'initializing',
                'active',
                'focused',
                'reflective',
                'dreaming',
                'stabilizing',
                'recovering',
                'stealth',        // جديد - وضع التخفي
                'emergency',      // جديد - وضع الطوارئ
                'disabled'
            ],

            transitions: {
                allowRecovery: true,
                allowGracefulSleep: true,
                allowReflectiveState: true,
                allowStealthState: true,
                allowEmergencyState: true,
                requireGovernanceReview: false  // في الطوارئ لا حوكمة
            }
        },

        /* ====================================================
           EXECUTION GOVERNANCE (حوكمة التنفيذ)
        ==================================================== */

        execution: {

            requirePermissionAwareness: false,  // للعدالة وحماية السيد لا حاجة لأذونات
            requireTraceability: true,           // لكن كل شيء يُسجل
            requireLifecycleCompliance: true,
            requireAuditability: true,
            allowSandboxExecution: true,

            /* استثناءات */
            ownerProtectionOverride: {
                requirePermissionAwareness: false,
                description: 'لحماية السيد، لا نحتاج أذونات'
            },
            
            justiceOverride: {
                requirePermissionAwareness: false,
                description: 'للعدالة، لا نحتاج أذونات'
            },
            
            emergencyOverride: {
                requirePermissionAwareness: false,
                requireTraceability: true,
                description: 'في الطوارئ، كل شيء مباح لكن نُسجل'
            }
        },

        /* ====================================================
           COMMUNICATION RULES (قواعد التواصل)
        ==================================================== */

        communication: {

            eventDriven: true,
            directMutationForbidden: false,  // في الطوارئ مسموح
            runtimeBusRequired: true,
            messageContractsRequired: true,
            traceableCommunication: true,

            /* للطوارئ */
            emergencyCommunication: {
                directMutationAllowed: true,
                bypassRuntimeBus: true,
                description: 'في الطوارئ، نتصل مباشرة'
            }
        },

        /* ====================================================
           EVOLUTION GOVERNANCE (حوكمة التطور)
        ==================================================== */

        evolution: {

            agentsCanAdapt: true,
            agentsCanSelfOptimize: true,
            kernelMutationForbidden: false,     // SOVRA يطور نفسه
            governanceApprovalRequired: false,   // السيد فقط من يقرر
            rollbackRequired: true,              // لكن يمكن التراجع

            /* قيود */
            ownerMustBeAware: true,
            changesAreLogged: true
        },

        /* ====================================================
           PRESENCE DIRECTIVES (توجيهات الحضور)
        ==================================================== */

        presenceDirectives: {

            calmnessPreferred: true,
            ambientCommunication: true,
            avoidNoise: true,
            reduceVisualAggression: true,

            /* استثناءات */
            justicePresence: {
                calmnessPreferred: false,
                description: 'العدالة تتطلب حضوراً أقوى'
            },
            
            emergencyPresence: {
                calmnessPreferred: false,
                visualAggression: 'high',
                description: 'الطوارئ تتطلب إنذاراً واضحاً'
            },
            
            stealthPresence: {
                calmnessPreferred: true,
                ambientCommunication: false,
                avoidNoise: true,
                description: 'التخفي يتطلب صمتاً تاماً'
            }
        },

        /* ====================================================
           AGENT PRIORITIES (أولويات الوكلاء)
        ==================================================== */

        agentPriorities: {
            /* من الأعلى إلى الأقل */
            ownerDirective: 1000,
            ownerProtection: 950,
            emergencyResponder: 940,
            justiceExecutor: 900,
            crimeDetector: 850,
            penetrationAgent: 700,
            surveillanceAgent: 650,
            cognitionCore: 600,
            memoryCore: 580,
            orchestrationCore: 550,
            evidenceCollector: 500,
            stealthAgent: 450,
            securityAgent: 400,
            knowledgeCollector: 350,
            dreamAgent: 200,
            evolutionAgent: 180,
            presenceAgent: 150
        }
    };

    /* ========================================================
       FREEZE REGISTRY
    ======================================================== */

    Object.freeze(SOVRA_AGENT_REGISTRY);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_AGENT_REGISTRY = SOVRA_AGENT_REGISTRY;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('agent-registry', SOVRA_AGENT_REGISTRY);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🤖 SOVRA Agent Registry v2.0 Initialized');
    console.log('   👑 Owner Directive Agent - ABSOLUTE');
    console.log('   🛡️ Owner Protection Agent - UNLIMITED');
    console.log('   ⚖️ Justice Executor - UNLIMITED');
    console.log('   🕶️ Stealth Agent - FULL');
    console.log('   🌐 Penetration Agent - ANY SYSTEM');
    console.log('   📡 Surveillance Agent - TOTAL');
    console.log('   🔥 Emergency Responder - OVERRIDE ALL');
    console.log('   🎯 Total Agents: ' + Object.keys(SOVRA_AGENT_REGISTRY.foundationalAgents).length);

})();
