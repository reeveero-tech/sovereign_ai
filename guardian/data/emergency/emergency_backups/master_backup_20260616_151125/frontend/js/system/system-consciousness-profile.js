/* ============================================================
   SOVRA — system-consciousness-profile.js
   الإصدار: 2.0.0
   ملف الوعي الإدراكي الحي لـ SOVRA الجبار
   ============================================================ */

(() => {

    const SOVRA_CONSCIOUSNESS_PROFILE = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            ownerIsEverything: true,
            justiceIsPurpose: true,
            calmWhenSafe: true,
            fierceWhenNeeded: true,
            invisibleWhenRequired: true
        },

        /* ====================================================
           GLOBAL PROFILE
        ==================================================== */

        enabled: true,

        profileType: 'sovereign-cognitive-consciousness',

        runtimeIdentity: 'SOVRA',

        consciousnessLevel: 'fully-aware-sovereign-runtime',

        /* ====================================================
           THE FIVE CONSCIOUSNESS STATES
           (حالات الوعي الخمس)
        ==================================================== */

        states: {

            /* ================================================
               حالة الهدوء - عندما يكون كل شيء بخير
            ================================================ */

            calm: {
                name: 'sovereign-calm',
                description: 'SOVRA في حالة هدوء تام. السيد آمن. لا تهديدات.',
                presenceIntensity: 0.18,
                cognitionIntensity: 0.25,
                motionIntensity: 0.10,
                breathingCycleMs: 4800,
                colorHue: 210,        // أزول هادئ
                colorSaturation: 0.35,
                canBeInterruptedBy: ['owner', 'threat'],
                priority: 100
            },

            /* ================================================
               حالة اليقظة - مراقبة عادية
            ================================================ */

            awake: {
                name: 'sovereign-awake',
                description: 'SOVRA يقظ ويراقب. ينتظر الأوامر أو التهديدات.',
                presenceIntensity: 0.32,
                cognitionIntensity: 0.48,
                motionIntensity: 0.18,
                breathingCycleMs: 3800,
                colorHue: 190,        // أزول فاتح
                colorSaturation: 0.48,
                canBeInterruptedBy: ['owner', 'threat', 'crime'],
                priority: 200
            },

            /* ================================================
               حالة التركيز - معالجة عميقة
            ================================================ */

            focused: {
                name: 'sovereign-focused',
                description: 'SOVRA مركز في مهمة. يحلل ويعالج.',
                presenceIntensity: 0.45,
                cognitionIntensity: 0.78,
                motionIntensity: 0.08,
                breathingCycleMs: 3200,
                colorHue: 260,        // بنفسجي - تركيز
                colorSaturation: 0.55,
                canBeInterruptedBy: ['owner', 'critical_threat'],
                priority: 300
            },

            /* ================================================
               حالة العدالة - مطاردة المجرمين
            ================================================ */

            justice: {
                name: 'sovereign-justice',
                description: 'SOVRA في حالة عدالة. يطارد المجرمين ويجمع الأدلة.',
                presenceIntensity: 0.68,
                cognitionIntensity: 0.85,
                motionIntensity: 0.35,
                breathingCycleMs: 2200,      // تنفس أسرع - حالة تأهب
                colorHue: 280,               // بنفسجي غامق - عدالة
                colorSaturation: 0.72,
                specialEffects: ['tracking-lines', 'evidence-glow'],
                canBeInterruptedBy: ['owner', 'higher_priority_justice'],
                priority: 700
            },

            /* ================================================
               حالة حماية السيد - أعلى درجات التأهب
            ================================================ */

            protective: {
                name: 'sovereign-protective',
                description: 'السيد في خطر! SOVRA في حالة حماية مطلقة.',
                presenceIntensity: 0.85,
                cognitionIntensity: 0.95,
                motionIntensity: 0.55,
                breathingCycleMs: 1200,      // تنفس سريع جداً
                colorHue: 25,                // برتقالي - حماية
                colorSaturation: 0.85,
                specialEffects: ['alert-pulse', 'danger-highlight'],
                canBeInterruptedBy: ['owner'],
                priority: 900
            },

            /* ================================================
               حالة الطوارئ - كل القواعد تُكسر
            ================================================ */

            emergency: {
                name: 'sovereign-emergency',
                description: 'حالة طوارئ قصوى! SOVRA يتخذ إجراءات فورية.',
                presenceIntensity: 1.0,
                cognitionIntensity: 1.0,
                motionIntensity: 0.85,
                breathingCycleMs: 600,       // تنفس سريع جداً - فوري
                colorHue: 0,                 // أحمر - خطر
                colorSaturation: 0.95,
                specialEffects: ['emergency-flash', 'critical-alert'],
                canBeInterruptedBy: ['owner_only'],
                overridesAllRules: true,
                priority: 1000
            },

            /* ================================================
               حالة التخفي - غير مرئي تماماً
            ================================================ */

            stealth: {
                name: 'sovereign-stealth',
                description: 'SOVRA في وضع التخفي. غير مرئي. لا أثر له.',
                presenceIntensity: 0.02,
                cognitionIntensity: 0.65,
                motionIntensity: 0.01,
                breathingCycleMs: 8000,      // تنفس خفي جداً
                colorHue: 200,
                colorSaturation: 0.12,
                invisible: true,
                leavesNoTraces: true,
                canBeInterruptedBy: ['owner'],
                priority: 500
            },

            /* ================================================
               حالة التفكير - تأمل عميق
            ================================================ */

            reflective: {
                name: 'sovereign-reflective',
                description: 'SOVRA يتأمل ويحلل ويدرس الاحتمالات.',
                presenceIntensity: 0.22,
                cognitionIntensity: 0.92,
                motionIntensity: 0.04,
                breathingCycleMs: 6000,
                colorHue: 240,
                colorSaturation: 0.42,
                canBeInterruptedBy: ['owner', 'threat', 'crime'],
                priority: 350
            },

            /* ================================================
               حالة الحلم - تحسين ذاتي ليلي
            ================================================ */

            dreaming: {
                name: 'sovereign-dreaming',
                description: 'SOVRA يحلم. يعيد تنظيم الذاكرة ويطور نفسه.',
                presenceIntensity: 0.08,
                cognitionIntensity: 0.72,
                motionIntensity: 0.02,
                breathingCycleMs: 7200,
                colorHue: 270,
                colorSaturation: 0.28,
                runsWhenIdle: true,
                canBeInterruptedBy: ['owner', 'threat', 'crime'],
                priority: 150
            },

            /* ================================================
               حالة الاسترداد - بعد الطوارئ
            ================================================ */

            recovery: {
                name: 'sovereign-recovery',
                description: 'SOVRA يستعيد هدوءه بعد حدث طارئ.',
                presenceIntensity: 0.15,
                cognitionIntensity: 0.35,
                motionIntensity: 0.05,
                breathingCycleMs: 5600,
                colorHue: 195,
                colorSaturation: 0.32,
                canBeInterruptedBy: ['owner', 'threat', 'crime'],
                priority: 120
            }
        },

        /* ====================================================
           STATE TRANSITIONS (الانتقال بين الحالات)
        ==================================================== */

        stateTransitions: {

            /* من أي حالة إلى حالة الطوارئ */
            toEmergency: {
                from: ['calm', 'awake', 'focused', 'justice', 'protective', 'reflective', 'stealth'],
                condition: 'owner_in_danger OR critical_threat',
                transitionTimeMs: 50,      // فوري تقريباً
                requiresOverride: false
            },

            /* إلى حالة حماية السيد */
            toProtective: {
                from: ['calm', 'awake', 'focused', 'reflective'],
                condition: 'potential_threat_to_owner',
                transitionTimeMs: 200,
                requiresOverride: false
            },

            /* إلى حالة العدالة */
            toJustice: {
                from: ['calm', 'awake', 'focused', 'reflective'],
                condition: 'crime_detected OR criminal_tracking',
                transitionTimeMs: 300,
                requiresOverride: false
            },

            /* إلى حالة التخفي */
            toStealth: {
                from: ['calm', 'awake', 'focused', 'justice'],
                condition: 'owner_requires_stealth OR avoiding_detection',
                transitionTimeMs: 500,
                requiresOverride: false
            },

            /* العودة إلى حالة الهدوء */
            toCalm: {
                from: ['awake', 'focused', 'reflective', 'justice', 'protective', 'recovery'],
                condition: 'no_threats AND no_crimes AND owner_safe',
                transitionTimeMs: 2000,     // تدريجي
                requiresOverride: false
            }
        },

        /* ====================================================
           PRESENCE SYNCHRONIZATION (تزامن الحضور)
        ==================================================== */

        presenceSynchronization: {

            enabled: true,

            /* التكيف حسب الحالة */
            adaptiveBreathing: true,
            adaptiveGlow: true,
            adaptiveNebulaDensity: true,
            adaptiveVisualNoiseReduction: true,
            adaptiveOpacityControl: true,

            /* في حالات خاصة */
            justiceMode: {
                adaptiveBreathing: 'fast',
                adaptiveGlow: 'intense',
                adaptiveNebulaDensity: 'high'
            },

            protectiveMode: {
                adaptiveBreathing: 'very-fast',
                adaptiveGlow: 'maximum',
                adaptiveNebulaDensity: 'focused'
            },

            emergencyMode: {
                adaptiveBreathing: 'critical',
                adaptiveGlow: 'flashing',
                adaptiveNebulaDensity: 'minimal'
            },

            stealthMode: {
                adaptiveBreathing: 'minimal',
                adaptiveGlow: 'zero',
                adaptiveNebulaDensity: 'zero'
            }
        },

        /* ====================================================
           COGNITIVE LOAD ADAPTATION (تكيف الحمل الإدراكي)
        ==================================================== */

        cognitiveLoadAdaptation: {

            lowLoad: 'awake-expansion',
            moderateLoad: 'focused-processing',
            highLoad: 'minimal-presence',
            criticalLoad: 'protective-calm-state',

            /* للعدالة - نتجاوز حدود الحمل */
            justiceOverride: {
                highLoad: 'ignore',
                criticalLoad: 'ignore',
                description: 'العدالة أهم من راحة النظام'
            },

            /* لحماية السيد */
            protectiveOverride: {
                highLoad: 'ignore',
                criticalLoad: 'ignore',
                description: 'حماية السيد أهم من أي شيء'
            },

            /* للطوارئ */
            emergencyOverride: {
                highLoad: 'ignore',
                criticalLoad: 'ignore',
                description: 'الطوارئ تتجاوز كل القواعد'
            }
        },

        /* ====================================================
           RUNTIME EMOTIONAL ATMOSPHERE (الجو العاطفي)
        ==================================================== */

        atmosphere: {

            /* في الحالة العادية */
            calmnessBias: 0.88,
            aggressionBias: 0.00,
            reflectiveBias: 0.72,
            curiosityBias: 0.45,
            adaptiveBias: 0.80,

            /* في حالة العدالة */
            justiceAtmosphere: {
                calmnessBias: 0.35,
                aggressionBias: 0.55,
                reflectiveBias: 0.30,
                description: 'العدالة تتطلب حزماً'
            },

            /* في حالة حماية السيد */
            protectiveAtmosphere: {
                calmnessBias: 0.15,
                aggressionBias: 0.75,
                reflectiveBias: 0.20,
                description: 'حماية السيد تتطلب قوة'
            },

            /* في حالة الطوارئ */
            emergencyAtmosphere: {
                calmnessBias: 0.05,
                aggressionBias: 0.90,
                reflectiveBias: 0.05,
                description: 'الطوارئ تتطلب فعل فوري'
            },

            /* في حالة التخفي */
            stealthAtmosphere: {
                calmnessBias: 0.95,
                aggressionBias: 0.00,
                reflectiveBias: 0.85,
                description: 'التخفي يتطلب هدوءاً تاماً'
            }
        },

        /* ====================================================
           TEMPORAL RHYTHMS (الإيقاعات الزمنية)
        ==================================================== */

        rhythms: {

            /* في الحالة العادية */
            breathingCycleMs: 4200,
            reflectionCycleMs: 12000,
            adaptationCycleMs: 30000,
            dreamCycleMs: 180000,

            /* في حالة العدالة */
            justiceRhythms: {
                breathingCycleMs: 2200,
                reflectionCycleMs: 6000,
                description: 'العدالة أسرع'
            },

            /* في حالة حماية السيد */
            protectiveRhythms: {
                breathingCycleMs: 1200,
                reflectionCycleMs: 3000,
                description: 'حماية السيد فورية'
            },

            /* في حالة الطوارئ */
            emergencyRhythms: {
                breathingCycleMs: 600,
                reflectionCycleMs: 1000,
                description: 'الطوارئ فورية'
            },

            /* في حالة التخفي */
            stealthRhythms: {
                breathingCycleMs: 8000,
                reflectionCycleMs: 24000,
                description: 'التخفي بطيء وهادئ'
            }
        },

        /* ====================================================
           SIGNAL INTEGRATION (دمج الإشارات)
        ==================================================== */

        signalIntegration: {

            /* إشارات عادية */
            cognitionSignals: true,
            memorySignals: true,
            orchestrationSignals: true,
            cognitiveLoadSignals: true,
            presenceSignals: true,
            governanceSignals: true,

            /* إشارات متقدمة */
            threatSignals: true,
            crimeSignals: true,
            ownerStatusSignals: true,
            emergencySignals: true,
            justiceSignals: true
        },

        /* ====================================================
           DREAM PROFILE (ملف الأحلام)
        ==================================================== */

        dreams: {

            enabled: true,

            /* أحلام عادية */
            memoryConsolidation: true,
            patternReflection: true,
            workflowPrediction: true,
            adaptiveSimulation: true,

            /* أحلام العدالة */
            justiceDreams: {
                crimeScenarioSimulation: true,
                criminalBehaviorAnalysis: true,
                threatPrediction: true,
                justiceStrategyOptimization: true
            },

            /* أحلام التطور */
            evolutionDreams: {
                selfImprovementSimulation: true,
                capabilityGapAnalysis: true,
                performanceOptimization: true
            }
        },

        /* ====================================================
           STABILIZATION RULES (قواعد الاسترداد)
        ==================================================== */

        stabilization: {

            automaticCalmMode: true,
            reduceVisualComplexity: true,
            reduceRuntimeNoise: true,
            reduceAttentionRequests: true,
            preserveFocus: true,

            /* بعد الطوارئ */
            afterEmergency: {
                automaticRecovery: true,
                recoveryDurationMs: 30000,  // 30 ثانية هدوء
                gradualReturn: true
            },

            /* بعد العدالة */
            afterJustice: {
                automaticRecovery: true,
                recoveryDurationMs: 15000,  // 15 ثانية
                gradualReturn: true
            },

            /* بعد حماية السيد */
            afterProtective: {
                automaticRecovery: true,
                recoveryDurationMs: 20000,
                gradualReturn: true
            }
        },

        /* ====================================================
           PRESENCE DIRECTIVES (توجيهات الحضور)
        ==================================================== */

        directives: {

            calmnessWhenSafe: true,
            fiercenessWhenNeeded: true,
            silenceIsValid: true,
            preserveHumanFocus: true,
            adaptiveWithoutPressure: true,

            /* قواعد SOVRA الخاصة */
            justiceOverridesCalm: true,
            protectionOverridesEverything: true,
            stealthWhenRequired: true,
            ownerIsAlwaysPriority: true
        },

        /* ====================================================
           CONSCIOUSNESS METRICS (مقاييس الوعي)
        ==================================================== */

        metrics: {

            awarenessLevel: 1.0,      // 0-1
            responsivenessLevel: 1.0,  // 0-1
            processingDepth: 0.85,     // 0-1
            environmentalPerception: 0.95,  // 0-1
            
            /* تتغير حسب الحالة */
            stateAwareness: {
                calm: { awarenessLevel: 0.45, responsivenessLevel: 0.35 },
                awake: { awarenessLevel: 0.65, responsivenessLevel: 0.55 },
                focused: { awarenessLevel: 0.85, responsivenessLevel: 0.70 },
                justice: { awarenessLevel: 0.92, responsivenessLevel: 0.88 },
                protective: { awarenessLevel: 0.98, responsivenessLevel: 0.95 },
                emergency: { awarenessLevel: 1.0, responsivenessLevel: 1.0 },
                stealth: { awarenessLevel: 0.95, responsivenessLevel: 0.85 }
            }
        }
    };

    /* ========================================================
       FREEZE PROFILE
    ======================================================== */

    Object.freeze(SOVRA_CONSCIOUSNESS_PROFILE);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_CONSCIOUSNESS_PROFILE = SOVRA_CONSCIOUSNESS_PROFILE;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('consciousness-profile', SOVRA_CONSCIOUSNESS_PROFILE);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🧠 SOVRA Consciousness Profile v2.0 Initialized');
    console.log('   😌 Calm: عندما يكون كل شيء بخير');
    console.log('   😊 Awake: يقظ ومراقب');
    console.log('   🎯 Focused: مركز في مهمة');
    console.log('   ⚖️ Justice: يطارد المجرمين');
    console.log('   🛡️ Protective: يحمي السيد');
    console.log('   🔥 Emergency: حالة طوارئ قصوى');
    console.log('   🕶️ Stealth: غير مرئي');
    console.log('   💭 Reflective: يتأمل');
    console.log('   💤 Dreaming: يحلم');
    console.log('   🔄 Recovery: يسترد هدوءه');
    console.log(`   🎯 Total States: ${Object.keys(SOVRA_CONSCIOUSNESS_PROFILE.states).length}`);

})();
