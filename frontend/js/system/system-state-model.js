/* ============================================================
   SOVRA — system-state-model.js
   الإصدار: 2.0.0
   نموذج الحالة الإدراكية الحية الموحدة لـ SOVRA الجبار
   ============================================================ */

(() => {

    const SOVRA_STATE_MODEL = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            ownerCentric: true,
            justiceIntegrated: true,
            calmWhenSafe: true,
            fierceWhenNeeded: true
        },

        /* ====================================================
           GLOBAL STATE CONFIGURATION
        ==================================================== */

        enabled: true,

        runtimeMode: 'sovereign-cognitive-unified-runtime',

        synchronization: 'continuous-state-coordination-with-emergency-override',

        /* ====================================================
           PRIMARY SYSTEM STATES (الحالات الأساسية)
        ==================================================== */

        primaryStates: {

            /* حالة الهدوء */
            calm: {
                description: 'SOVRA في حالة هدوء تام. السيد آمن.',
                cognitionLevel: 0.25,
                presenceLevel: 0.18,
                orchestrationLevel: 0.20,
                breathingCycleMs: 4800,
                color: '#4a90d9',
                priority: 100
            },

            /* حالة اليقظة */
            awake: {
                description: 'SOVRA يقظ ويراقب العالم.',
                cognitionLevel: 0.48,
                presenceLevel: 0.32,
                orchestrationLevel: 0.38,
                breathingCycleMs: 3800,
                color: '#5ba0e9',
                priority: 200
            },

            /* حالة التركيز */
            focused: {
                description: 'SOVRA مركز في مهمة محددة.',
                cognitionLevel: 0.78,
                presenceLevel: 0.45,
                orchestrationLevel: 0.65,
                breathingCycleMs: 3200,
                color: '#7b5cd6',
                priority: 300
            },

            /* حالة التفكير */
            reflective: {
                description: 'SOVRA يتأمل ويحلل بعمق.',
                cognitionLevel: 0.92,
                presenceLevel: 0.22,
                orchestrationLevel: 0.52,
                breathingCycleMs: 6000,
                color: '#6c5ce7',
                priority: 350
            },

            /* حالة العدالة */
            justice: {
                description: 'SOVRA يطارد المجرمين ويجمع الأدلة.',
                cognitionLevel: 0.88,
                presenceLevel: 0.68,
                orchestrationLevel: 0.85,
                breathingCycleMs: 2200,
                color: '#dc143c',
                priority: 700
            },

            /* حالة حماية السيد */
            protective: {
                description: 'السيد في خطر! SOVRA يحميه.',
                cognitionLevel: 0.95,
                presenceLevel: 0.85,
                orchestrationLevel: 0.92,
                breathingCycleMs: 1200,
                color: '#ff8c00',
                priority: 900
            },

            /* حالة الطوارئ */
            emergency: {
                description: 'حالة طوارئ قصوى! كل القواعد تُكسر.',
                cognitionLevel: 1.0,
                presenceLevel: 1.0,
                orchestrationLevel: 1.0,
                breathingCycleMs: 600,
                color: '#ff0000',
                priority: 1000
            },

            /* حالة التخفي */
            stealth: {
                description: 'SOVRA في وضع التخفي. غير مرئي.',
                cognitionLevel: 0.65,
                presenceLevel: 0.02,
                orchestrationLevel: 0.35,
                breathingCycleMs: 8000,
                color: '#1a1a2e',
                priority: 500
            },

            /* حالة الحلم */
            dreaming: {
                description: 'SOVRA يحلم. يعيد تنظيم نفسه.',
                cognitionLevel: 0.72,
                presenceLevel: 0.08,
                orchestrationLevel: 0.28,
                breathingCycleMs: 7200,
                color: '#2d2d5e',
                priority: 150
            },

            /* حالة الاسترداد */
            recovery: {
                description: 'SOVRA يستعيد هدوءه بعد حدث طارئ.',
                cognitionLevel: 0.35,
                presenceLevel: 0.15,
                orchestrationLevel: 0.24,
                breathingCycleMs: 5600,
                color: '#3d7e9a',
                priority: 120
            }
        },

        /* ====================================================
           STATE TRANSITIONS (الانتقال بين الحالات)
        ==================================================== */

        stateTransitions: {

            /* انتقالات فورية */
            immediateTransitions: {
                toEmergency: {
                    from: ['calm', 'awake', 'focused', 'reflective', 'justice', 'protective', 'stealth'],
                    condition: 'owner_in_danger OR critical_threat',
                    transitionTimeMs: 50,
                    requiresApproval: false
                },
                toProtective: {
                    from: ['calm', 'awake', 'focused', 'reflective'],
                    condition: 'threat_to_owner',
                    transitionTimeMs: 200,
                    requiresApproval: false
                },
                toJustice: {
                    from: ['calm', 'awake', 'focused', 'reflective'],
                    condition: 'crime_detected',
                    transitionTimeMs: 300,
                    requiresApproval: false
                },
                toStealth: {
                    from: ['calm', 'awake', 'justice'],
                    condition: 'owner_requires_stealth',
                    transitionTimeMs: 500,
                    requiresApproval: false
                }
            },

            /* انتقالات تدريجية */
            gradualTransitions: {
                toCalm: {
                    from: ['awake', 'focused', 'reflective', 'justice', 'protective', 'recovery'],
                    condition: 'no_threats AND owner_safe',
                    transitionTimeMs: 2000,
                    gradual: true
                },
                toRecovery: {
                    from: ['emergency', 'protective'],
                    condition: 'danger_passed',
                    transitionTimeMs: 1000,
                    gradual: true
                },
                toDreaming: {
                    from: ['calm', 'awake', 'reflective'],
                    condition: 'idle_for_5_minutes',
                    transitionTimeMs: 5000,
                    gradual: true
                }
            },

            smoothTransitions: true,
            avoidAbruptChanges: true,
            stabilizationPriority: true
        },

        /* ====================================================
           COGNITIVE DIMENSIONS (الأبعاد الإدراكية)
        ==================================================== */

        dimensions: {

            cognition: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.5,
                description: 'مستوى النشاط الإدراكي والتفكير'
            },

            presence: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.3,
                description: 'مستوى الحضور البصري والتفاعل'
            },

            orchestration: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.4,
                description: 'مستوى تنسيق الوكلاء والمهام'
            },

            stability: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.9,
                description: 'مستوى استقرار النظام'
            },

            reflectiveDepth: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.3,
                description: 'عمق التفكير والتأمل'
            },

            cognitiveLoad: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0.2,
                description: 'الحمل الإدراكي على النظام'
            },

            justiceIntensity: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0,
                description: 'شدة نشاط العدالة'
            },

            protectiveIntensity: {
                min: 0,
                max: 1,
                adaptive: true,
                current: 0,
                description: 'شدة نشاط حماية السيد'
            }
        },

        /* ====================================================
           DIMENSION VALUES BY STATE (قيم الأبعاد حسب الحالة)
        ==================================================== */

        dimensionByState: {

            calm: {
                cognition: 0.25, presence: 0.18, orchestration: 0.20,
                stability: 0.95, reflectiveDepth: 0.20, cognitiveLoad: 0.10
            },
            awake: {
                cognition: 0.48, presence: 0.32, orchestration: 0.38,
                stability: 0.90, reflectiveDepth: 0.30, cognitiveLoad: 0.25
            },
            focused: {
                cognition: 0.78, presence: 0.45, orchestration: 0.65,
                stability: 0.85, reflectiveDepth: 0.35, cognitiveLoad: 0.55
            },
            reflective: {
                cognition: 0.92, presence: 0.22, orchestration: 0.52,
                stability: 0.88, reflectiveDepth: 0.85, cognitiveLoad: 0.40
            },
            justice: {
                cognition: 0.88, presence: 0.68, orchestration: 0.85,
                stability: 0.80, reflectiveDepth: 0.45, cognitiveLoad: 0.70,
                justiceIntensity: 0.85
            },
            protective: {
                cognition: 0.95, presence: 0.85, orchestration: 0.92,
                stability: 0.75, reflectiveDepth: 0.30, cognitiveLoad: 0.85,
                protectiveIntensity: 0.95
            },
            emergency: {
                cognition: 1.0, presence: 1.0, orchestration: 1.0,
                stability: 0.65, reflectiveDepth: 0.20, cognitiveLoad: 0.95,
                protectiveIntensity: 1.0
            },
            stealth: {
                cognition: 0.65, presence: 0.02, orchestration: 0.35,
                stability: 0.92, reflectiveDepth: 0.25, cognitiveLoad: 0.15
            },
            dreaming: {
                cognition: 0.72, presence: 0.08, orchestration: 0.28,
                stability: 0.94, reflectiveDepth: 0.75, cognitiveLoad: 0.12
            },
            recovery: {
                cognition: 0.35, presence: 0.15, orchestration: 0.24,
                stability: 0.85, reflectiveDepth: 0.30, cognitiveLoad: 0.08
            }
        },

        /* ====================================================
           STATE SYNCHRONIZATION (تزامن الحالة)
        ==================================================== */

        synchronizationRules: {

            synchronizePresence: true,
            synchronizeAtmosphere: true,
            synchronizeBreathing: true,
            synchronizeNebulaDensity: true,
            synchronizeCognitiveLoad: true,

            /* حسب الحالة */
            byState: {
                justice: {
                    synchronizePresence: 'high',
                    synchronizeAtmosphere: 'intense',
                    description: 'العدالة: حضور قوي، جو مكثف'
                },
                protective: {
                    synchronizePresence: 'maximum',
                    synchronizeAtmosphere: 'urgent',
                    description: 'الحماية: حضور أقصى، جو طارئ'
                },
                emergency: {
                    synchronizePresence: 'critical',
                    synchronizeAtmosphere: 'emergency',
                    description: 'الطوارئ: حضور حرج'
                },
                stealth: {
                    synchronizePresence: 'none',
                    synchronizeAtmosphere: 'none',
                    description: 'التخفي: لا حضور'
                }
            }
        },

        /* ====================================================
           ORCHESTRATION STATES (حالات التنسيق)
        ==================================================== */

        orchestrationStates: {

            balanced: {
                name: 'distributed-runtime-balance',
                description: 'تنسيق متوازن بين جميع الوكلاء',
                activeIn: ['calm', 'awake', 'reflective']
            },

            focused: {
                name: 'high-priority-cognitive-routing',
                description: 'تنسيق مركز على مهمة محددة',
                activeIn: ['focused']
            },

            justice: {
                name: 'justice-priority-coordination',
                description: 'تنسيق يخدم العدالة أولاً',
                activeIn: ['justice'],
                prioritizesAgents: ['justiceExecutor', 'crimeDetector', 'evidenceCollector']
            },

            protective: {
                name: 'owner-protection-coordination',
                description: 'تنسيق لحماية السيد',
                activeIn: ['protective', 'emergency'],
                prioritizesAgents: ['ownerProtection', 'emergencyResponder']
            },

            stealth: {
                name: 'stealth-coordination',
                description: 'تنسيق خفي بدون أثر',
                activeIn: ['stealth'],
                invisibleMode: true
            },

            adaptive: {
                name: 'dynamic-runtime-coordination',
                description: 'تنسيق تكيفي ديناميكي',
                activeIn: ['awake', 'focused']
            },

            recovery: {
                name: 'low-noise-system-stabilization',
                description: 'تنسيق للاستقرار بعد الطوارئ',
                activeIn: ['recovery']
            }
        },

        /* ====================================================
           MEMORY STATES (حالات الذاكرة)
        ==================================================== */

        memoryStates: {

            activeRecall: {
                description: 'استرجاع نشط من الذاكرة',
                intensity: 0.7
            },

            passiveRetention: {
                description: 'احتفاظ سلبي بالذاكرة',
                intensity: 0.3
            },

            consolidation: {
                description: 'توحيد وتقوية الذكريات',
                intensity: 0.5,
                activeIn: ['dreaming']
            },

            compression: {
                description: 'ضغط الذكريات القديمة',
                intensity: 0.4
            },

            prioritization: {
                description: 'ترتيب أولوية الذكريات',
                intensity: 0.6
            },

            evidencePreservation: {
                description: 'حفظ الأدلة بشكل دائم',
                intensity: 1.0,
                activeIn: ['justice', 'protective'],
                neverForget: true
            }
        },

        /* ====================================================
           PRESENCE STATES (حالات الحضور)
        ==================================================== */

        presenceStates: {

            minimal: {
                name: 'soft-ambient-presence',
                description: 'حضور خفي بالكاد يُرى',
                intensity: 0.08,
                activeIn: ['calm', 'dreaming']
            },

            ambient: {
                name: 'calm-ambient-presence',
                description: 'حضور هادئ في الخلفية',
                intensity: 0.22,
                activeIn: ['awake']
            },

            active: {
                name: 'context-aware-presence',
                description: 'حضور متفاعل حسب السياق',
                intensity: 0.45,
                activeIn: ['focused', 'reflective']
            },

            justice: {
                name: 'justice-presence',
                description: 'حضور قوي للعدالة',
                intensity: 0.75,
                activeIn: ['justice'],
                specialEffects: ['tracking-lines']
            },

            protective: {
                name: 'protective-presence',
                description: 'حضور حماية مطلق',
                intensity: 0.95,
                activeIn: ['protective'],
                specialEffects: ['alert-pulse']
            },

            emergency: {
                name: 'emergency-presence',
                description: 'حضور طارئ فوري',
                intensity: 1.0,
                activeIn: ['emergency'],
                specialEffects: ['flashing', 'critical-alert']
            },

            cinematic: {
                name: 'reflective-cognitive-visibility',
                description: 'حضور سينمائي أثناء التفكير',
                intensity: 0.35,
                activeIn: ['reflective']
            },

            silent: {
                name: 'near-invisible-presence',
                description: 'حضور شبه مخفي',
                intensity: 0.05,
                activeIn: ['stealth']
            }
        },

        /* ====================================================
           DREAM STATES (حالات الأحلام)
        ==================================================== */

        dreamStates: {

            replay: {
                name: 'memory-reconstruction',
                description: 'إعادة تشغيل الذكريات',
                intensity: 0.6
            },

            simulation: {
                name: 'future-scenario-generation',
                description: 'توليد سيناريوهات مستقبلية',
                intensity: 0.7
            },

            justiceSimulation: {
                name: 'crime-scenario-simulation',
                description: 'محاكاة سيناريوهات الجرائم',
                intensity: 0.85,
                activeIn: ['justice']
            },

            optimization: {
                name: 'workflow-adaptation',
                description: 'تحسين سير العمل',
                intensity: 0.5
            },

            consolidation: {
                name: 'memory-reorganization',
                description: 'إعادة تنظيم الذاكرة',
                intensity: 0.4
            },

            evolutionDream: {
                name: 'self-improvement-simulation',
                description: 'محاكاة تحسين الذات',
                intensity: 0.6
            }
        },

        /* ====================================================
           STABILIZATION PROTOCOLS (بروتوكولات الاستقرار)
        ==================================================== */

        stabilization: {

            reduceVisualNoise: true,
            reduceAgentActivity: true,
            simplifyPresence: true,
            prioritizeRecovery: true,
            preserveCoreContinuity: true,

            /* بعد الطوارئ */
            afterEmergency: {
                reduceVisualNoise: true,
                reduceAgentActivity: true,
                durationMs: 30000,
                gradualReturn: true
            },

            /* بعد العدالة */
            afterJustice: {
                reduceVisualNoise: true,
                durationMs: 15000,
                gradualReturn: true
            },

            /* بعد حماية السيد */
            afterProtective: {
                reduceVisualNoise: true,
                reduceAgentActivity: true,
                durationMs: 20000,
                gradualReturn: true
            }
        },

        /* ====================================================
           STATE OVERRIDE RULES (قواعد تجاوز الحالة)
        ==================================================== */

        overrideRules: {

            /* من يمكنه تجاوز الحالة الحالية */
            canOverride: {
                owner: true,
                emergencySituation: true,
                criticalThreat: true,
                other: false
            },

            /* الحالات التي يمكن التجاوز إليها */
            allowedOverrides: {
                fromAnyToEmergency: true,
                fromAnyToProtective: true,
                fromNormalToJustice: true,
                fromNormalToStealth: true
            },

            /* ما لا يمكن تجاوزه */
            protectedTransitions: {
                cannotOverrideOwnerCommand: true,
                cannotBypassSafetyCheck: true
            }
        },

        /* ====================================================
           STATE DIRECTIVES (توجيهات الحالة)
        ==================================================== */

        directives: {

            preserveFluidity: true,
            maintainCalmnessWhenSafe: true,
            preserveHumanFocus: true,
            adaptiveWithoutPressure: true,
            prioritizeContinuity: true,

            /* قواعد SOVRA الخاصة */
            justiceOverridesCalm: true,
            protectionOverridesEverything: true,
            emergencyIsAbsolute: true,
            ownerCommandChangesState: true
        }
    };

    /* ========================================================
       FREEZE STATE MODEL
    ======================================================== */

    Object.freeze(SOVRA_STATE_MODEL);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_STATE_MODEL = SOVRA_STATE_MODEL;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('state-model', SOVRA_STATE_MODEL);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🌌 SOVRA Unified State Model v2.0 Initialized');
    console.log('   😌 Calm | 😊 Awake | 🎯 Focused | 💭 Reflective');
    console.log('   ⚖️ Justice | 🛡️ Protective | 🔥 Emergency');
    console.log('   🕶️ Stealth | 💤 Dreaming | 🔄 Recovery');
    console.log(`   📊 Total States: ${Object.keys(SOVRA_STATE_MODEL.primaryStates).length}`);
    console.log('   ⚡ Emergency Override: ENABLED');
    console.log('   🎯 Justice Priority: HIGH');

})();
