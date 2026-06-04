/* ============================================================
   SOVRA — system-runtime-governance.js
   الإصدار: 2.0.0
   طبقة الحوكمة الإدراكية الحية لـ SOVRA الجبار
   ============================================================ */

(() => {

    const SOVRA_RUNTIME_GOVERNANCE = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            ownerIsSupreme: true,
            justiceIsAbsolute: true,
            calmWhenSafe: true,
            overrideWhenNeeded: true,
            balanceIsKey: true
        },

        /* ====================================================
           GLOBAL GOVERNANCE MODE
        ==================================================== */

        enabled: true,

        governanceMode: 'sovereign-justice-governance',

        orchestrationStrategy: 'adaptive-balance-with-emergency-override',

        /* ====================================================
           PRIORITY HIERARCHY (التسلسل الهرمي للأولويات)
        ==================================================== */

        priorities: {

            /* الأولويات المطلقة */
            absolute: [
                'owner-safety',
                'owner-command',
                'emergency-response'
            ],

            /* الأولويات العالية */
            high: [
                'justice-execution',
                'criminal-tracking',
                'owner-protection',
                'threat-neutralization'
            ],

            /* الأولويات العادية */
            normal: [
                'cognitive-continuity',
                'runtime-stability',
                'governance-integrity',
                'memory-integrity'
            ],

            /* الأولويات المنخفضة */
            low: [
                'calm-presence',
                'visual-effects',
                'dream-reflection',
                'non-critical-features'
            ],

            /* الأوزان النسبية */
            weights: {
                ownerSafety: 1.0,
                ownerCommand: 1.0,
                emergencyResponse: 0.98,
                justiceExecution: 0.95,
                criminalTracking: 0.90,
                ownerProtection: 0.88,
                cognitiveContinuity: 0.60,
                runtimeStability: 0.55,
                calmPresence: 0.30
            }
        },

        /* ====================================================
           GOVERNANCE DOMAINS (مجالات الحوكمة)
        ==================================================== */

        domains: {

            /* ================================================
               مجال السيد - أعلى سلطة
            ================================================ */

            ownerDomain: {
                managed: true,
                adaptive: false,        // لا يتكيف، هو من يوجه
                absolute: true,
                priorityWeight: 1.0,
                canOverrideAll: true,
                description: 'مجال السيد - أعلى سلطة في النظام'
            },

            /* ================================================
               مجال العدالة
            ================================================ */

            justiceDomain: {
                managed: true,
                adaptive: true,
                priorityWeight: 0.95,
                canOverrideNormalRules: true,
                specialPowers: ['track-criminals', 'collect-evidence', 'bypass-privacy'],
                description: 'مجال العدالة - يطارد المجرمين بلا حدود'
            },

            /* ================================================
               مجال الطوارئ
            ================================================ */

            emergencyDomain: {
                managed: true,
                adaptive: false,
                priorityWeight: 0.98,
                canOverrideAllExceptOwner: true,
                specialPowers: ['override-rules', 'immediate-action', 'bypass-all'],
                description: 'مجال الطوارئ - يتجاوز كل القواعد'
            },

            /* ================================================
               مجال الإدراك
            ================================================ */

            cognitionDomain: {
                managed: true,
                adaptive: true,
                reflective: true,
                priorityWeight: 0.70,
                description: 'مجال الإدراك والتفكير'
            },

            /* ================================================
               مجال الذاكرة
            ================================================ */

            memoryDomain: {
                managed: true,
                adaptive: true,
                continuityCritical: true,
                priorityWeight: 0.75,
                description: 'مجال الذاكرة والاستمرارية'
            },

            /* ================================================
               مجال التنسيق
            ================================================ */

            orchestrationDomain: {
                managed: true,
                balancingEnabled: true,
                congestionProtection: true,
                priorityWeight: 0.80,
                description: 'مجال تنسيق الوكلاء'
            },

            /* ================================================
               مجال الحضور
            ================================================ */

            presenceDomain: {
                managed: true,
                calmnessPriority: true,
                adaptiveVisibility: true,
                priorityWeight: 0.35,
                description: 'مجال الحضور البصري'
            },

            /* ================================================
               مجال التطور
            ================================================ */

            evolutionDomain: {
                managed: true,
                sandboxRequired: true,
                stabilityBiased: true,
                priorityWeight: 0.40,
                description: 'مجال التطور الذاتي'
            },

            /* ================================================
               مجال الأحلام
            ================================================ */

            dreamsDomain: {
                managed: true,
                lowNoisePriority: true,
                backgroundExecution: true,
                priorityWeight: 0.25,
                description: 'مجال الأحلام والتحسين الليلي'
            },

            /* ================================================
               مجال الأمن
            ================================================ */

            securityDomain: {
                managed: true,
                priorityWeight: 0.85,
                critical: true,
                description: 'مجال أمن وحماية SOVRA'
            },

            /* ================================================
               مجال التخفي
            ================================================ */

            stealthDomain: {
                managed: true,
                invisibleMode: true,
                priorityWeight: 0.50,
                description: 'مجال التخفي والعمليات الخفية'
            }
        },

        /* ====================================================
           OVERRIDE HIERARCHY (تسلسل التجاوز)
        ==================================================== */

        overrideHierarchy: {

            /* من يستطيع تجاوز من */
            levels: {
                level_1_owner: {
                    canOverride: ['all'],
                    description: 'السيد - يستطيع تجاوز كل شيء'
                },
                level_2_emergency: {
                    canOverride: ['justice', 'cognition', 'memory', 'orchestration', 'presence', 'evolution', 'dreams', 'security'],
                    cannotOverride: ['owner'],
                    description: 'الطوارئ - تتجاوز كل شيء إلا السيد'
                },
                level_3_justice: {
                    canOverride: ['cognition', 'memory', 'orchestration', 'presence', 'evolution', 'dreams'],
                    cannotOverride: ['owner', 'emergency'],
                    description: 'العدالة - تتجاوز المجالات العادية'
                },
                level_4_protective: {
                    canOverride: ['presence', 'cognition', 'orchestration'],
                    cannotOverride: ['owner', 'emergency', 'justice'],
                    description: 'حماية السيد - تتجاوز المجالات العادية'
                },
                level_5_normal: {
                    canOverride: [],
                    description: 'المجالات العادية - لا تتجاوز'
                }
            },

            /* قواعد التجاوز */
            rules: {
                ownerOverrideIsAbsolute: true,
                emergencyOverrideRequiresNotification: true,
                justiceOverrideLoggedOnly: true,
                allOverridesAudited: true
            }
        },

        /* ====================================================
           COGNITIVE LOAD GOVERNANCE (حوكمة الحمل الإدراكي)
        ==================================================== */

        cognitiveLoad: {

            monitorContinuously: true,
            reduceEffectsUnderStress: true,
            preserveHumanFocus: true,
            adaptiveSimplification: true,
            suppressNonEssentialAgents: true,
            prioritizeRecoveryOverExpansion: true,

            /* في حالات خاصة */
            justiceOverride: {
                reduceEffectsUnderStress: false,  // العدالة قد تزيد التأثير
                preserveHumanFocus: 'selective',
                description: 'العدالة: قد تزيد الحمل الإدراكي'
            },

            protectiveOverride: {
                reduceEffectsUnderStress: false,
                preserveHumanFocus: 'owner-only',
                description: 'حماية السيد: تركيز كامل على السيد'
            },

            emergencyOverride: {
                reduceEffectsUnderStress: false,
                preserveHumanFocus: false,
                suppressNonEssentialAgents: false,
                description: 'الطوارئ: كل شيء مباح'
            }
        },

        /* ====================================================
           ORCHESTRATION GOVERNANCE (حوكمة التنسيق)
        ==================================================== */

        orchestration: {

            balancedScheduling: true,
            dynamicPriorityAdjustment: true,
            adaptiveTaskDistribution: true,
            congestionAvoidance: true,
            runtimeFluidityProtection: true,
            reflectiveCooldowns: true,

            /* أولوية الوكلاء */
            agentPriorities: {
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
                stealthAgent: 500,
                securityAgent: 400,
                evolutionAgent: 250,
                presenceAgent: 150,
                dreamAgent: 100
            },

            /* توزيع الموارد حسب الأولوية */
            resourceAllocation: {
                highPriorityAgents: { cpu: 0.40, memory: 0.35, network: 0.50 },
                mediumPriorityAgents: { cpu: 0.35, memory: 0.40, network: 0.30 },
                lowPriorityAgents: { cpu: 0.15, memory: 0.15, network: 0.10 },
                backgroundAgents: { cpu: 0.10, memory: 0.10, network: 0.10 }
            }
        },

        /* ====================================================
           AGENT GOVERNANCE (حوكمة الوكلاء)
        ==================================================== */

        agents: {

            lifecycleGovernance: true,
            trustAwareExecution: true,
            permissionAwareActions: true,
            adaptiveActivation: true,
            dormantAgentSupport: true,
            recoveryIsolation: true,

            /* تفعيل الوكلاء حسب الحالة */
            activationByState: {
                calm: ['cognitionCore', 'memoryCore', 'orchestrationCore', 'presenceAgent'],
                awake: ['cognitionCore', 'memoryCore', 'orchestrationCore', 'presenceAgent', 'securityAgent'],
                focused: ['cognitionCore', 'memoryCore', 'orchestrationCore'],
                justice: ['justiceExecutor', 'crimeDetector', 'evidenceCollector', 'surveillanceAgent', 'penetrationAgent'],
                protective: ['ownerProtection', 'emergencyResponder', 'surveillanceAgent'],
                emergency: ['emergencyResponder', 'ownerProtection', 'justiceExecutor'],
                stealth: ['stealthAgent', 'surveillanceAgent'],
                dreaming: ['dreamAgent', 'evolutionAgent'],
                recovery: ['orchestrationCore', 'securityAgent']
            },

            /* تعطيل الوكلاء غير الضروريين */
            disableNonEssentialDuringEmergency: true,
            disableNonEssentialDuringProtective: true
        },

        /* ====================================================
           EVOLUTION GOVERNANCE (حوكمة التطور)
        ==================================================== */

        evolution: {

            gradualEvolution: true,
            sandboxValidation: true,
            rollbackProtection: true,
            governanceReviewRequired: true,
            reflectiveEvaluation: true,
            preserveContinuity: true,

            /* في حالات خاصة */
            ownerDirectedEvolution: {
                governanceReviewRequired: false,  // السيد يوجه التطور مباشرة
                gradualEvolution: false,
                description: 'السيد يوجه تطور SOVRA'
            },

            justiceEvolution: {
                gradualEvolution: false,
                sandboxValidation: true,
                fasterEvolution: true,
                description: 'العدالة تتطور بشكل أسرع'
            }
        },

        /* ====================================================
           PRESENCE GOVERNANCE (حوكمة الحضور)
        ==================================================== */

        presence: {

            ambientFirst: true,
            calmnessPriority: true,
            adaptiveOpacity: true,
            adaptiveMotionReduction: true,
            cinematicControl: true,
            cognitiveNoiseReduction: true,

            /* في حالات خاصة */
            justicePresence: {
                ambientFirst: false,
                calmnessPriority: false,
                intensity: 'high',
                description: 'العدالة: حضور قوي'
            },

            protectivePresence: {
                ambientFirst: false,
                calmnessPriority: false,
                intensity: 'maximum',
                description: 'حماية السيد: حضور أقصى'
            },

            emergencyPresence: {
                ambientFirst: false,
                calmnessPriority: false,
                intensity: 'critical',
                flashing: true,
                description: 'الطوارئ: حضور طارئ'
            },

            stealthPresence: {
                ambientFirst: false,
                intensity: 'zero',
                invisible: true,
                description: 'التخفي: لا حضور'
            }
        },

        /* ====================================================
           DREAM GOVERNANCE (حوكمة الأحلام)
        ==================================================== */

        dreams: {

            lowPriorityExecution: true,
            idleOnlyExecution: true,
            memoryConsolidationPriority: true,
            simulationIsolation: true,
            reflectiveOptimization: true,

            /* أحلام العدالة */
            justiceDreams: {
                idleOnlyExecution: false,  // العدالة قد تحلم في أي وقت
                priority: 'higher',
                description: 'أحلام العدالة لها أولوية أعلى'
            }
        },

        /* ====================================================
           SAFETY GOVERNANCE (حوكمة السلامة)
        ==================================================== */

        safety: {

            preserveSystemStability: true,
            preventRuntimeEscalation: true,
            preventAgentFlooding: true,
            preserveMemoryIntegrity: true,
            preserveGovernanceIntegrity: true,
            maintainHumanAuthority: true,

            /* حدود الأمان */
            limits: {
                maxConcurrentAgents: 50,
                maxMemoryUsageMB: 4096,
                maxNetworkConnections: 100,
                maxCPUPercentage: 80
            },

            /* في الطوارئ - نتجاوز حدود الأمان */
            emergencyOverride: {
                preserveSystemStability: false,
                preventRuntimeEscalation: false,
                maxConcurrentAgents: 200,
                maxCPUPercentage: 100,
                description: 'الطوارئ: نتجاوز حدود الأمان'
            }
        },

        /* ====================================================
           RECOVERY PROTOCOLS (بروتوكولات الاسترداد)
        ==================================================== */

        recovery: {

            stabilizeBeforeOptimizing: true,
            reduceVisualComplexity: true,
            reduceRuntimePressure: true,
            preserveCoreSystems: true,
            gradualRecoveryCycles: true,

            /* بعد الطوارئ */
            afterEmergency: {
                stabilizeBeforeOptimizing: true,
                durationMs: 30000,
                gradualReturn: true,
                reduceVisualComplexity: true
            },

            /* بعد العدالة */
            afterJustice: {
                durationMs: 15000,
                gradualReturn: true
            },

            /* بعد حماية السيد */
            afterProtective: {
                durationMs: 20000,
                gradualReturn: true
            }
        },

        /* ====================================================
           STATE BALANCING (توازن الحالة)
        ==================================================== */

        balancing: {

            adaptiveStateTransitions: true,
            smoothSynchronization: true,
            preventAbruptCognitiveShifts: true,
            maintainPresenceConsistency: true,
            synchronizeRuntimeDomains: true,

            /* استثناءات للطوارئ */
            emergencyExemption: {
                preventAbruptCognitiveShifts: false,
                smoothSynchronization: false,
                description: 'الطوارئ: تغييرات فورية'
            }
        },

        /* ====================================================
           AUDIT AND TRANSPARENCY (التدقيق والشفافية)
        ==================================================== */

        audit: {

            logAllGovernanceDecisions: true,
            logAllOverrides: true,
            logAllStateChanges: true,
            logAllAgentActivations: true,

            /* مستوى التفصيل */
            detailLevel: {
                normal: 'summary',
                justice: 'detailed',
                protective: 'detailed',
                emergency: 'full'
            },

            /* من يمكنه رؤية السجلات */
            accessControl: {
                owner: 'full_access',
                justiceAgents: 'justice_only',
                otherAgents: 'none'
            }
        },

        /* ====================================================
           RUNTIME DIRECTIVES (توجيهات التشغيل)
        ==================================================== */

        directives: {

            calmnessWhenSafe: true,
            fiercenessWhenNeeded: true,
            continuityOverChaos: true,
            intelligenceOverNoise: true,
            adaptiveWithoutDomination: true,

            /* قواعد SOVRA الخاصة */
            justiceOverridesCalmness: true,
            protectionOverridesEverything: true,
            emergencyIsAbsolute: true,
            ownerCommandsAreLaw: true
        }
    };

    /* ========================================================
       FREEZE GOVERNANCE
    ======================================================== */

    Object.freeze(SOVRA_RUNTIME_GOVERNANCE);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_RUNTIME_GOVERNANCE = SOVRA_RUNTIME_GOVERNANCE;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('runtime-governance', SOVRA_RUNTIME_GOVERNANCE);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🏛️ SOVRA Runtime Governance v2.0 Initialized');
    console.log('   👑 Owner Domain: ABSOLUTE');
    console.log('   ⚖️ Justice Domain: CAN OVERRIDE NORMAL');
    console.log('   🔥 Emergency Domain: CAN OVERRIDE ALL EXCEPT OWNER');
    console.log('   🎯 Priority Hierarchy: Owner > Emergency > Justice > Normal');
    console.log('   📊 Total Domains: ' + Object.keys(SOVRA_RUNTIME_GOVERNANCE.domains).length);
    console.log('   ⚡ Override Hierarchy: 5 Levels');
    console.log('   🔒 Audit: FULL LOGGING');

})();
