/* ============================================================
   SOVRA — system-cognitive-energy.js
   الإصدار: 2.0.0
   نموذج الطاقة الإدراكية الحية - توزيع الموارد الإدراكية الذكي
   الطاقة الإدراكية هي قلب قدرة SOVRA على التفكير والحماية والعدالة
   ============================================================ */

(() => {

    const SOVRA_COGNITIVE_ENERGY = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            energyIsConsciousness: true,
            protectOwnerGetsMaxEnergy: true,
            justiceGetsHighEnergy: true,
            emergencyGetsAllEnergy: true,
            stealthConservesEnergy: true,
            energyNeverZero: true
        },

        /* ====================================================
           GLOBAL ENERGY MODEL
        ==================================================== */

        enabled: true,

        architecture: 'sovereign-cognitive-energy-distribution-fabric',

        runtimeMode: 'adaptive-energy-allocation-with-emergency-reserve',

        /* ====================================================
           ENERGY POOL (مصدر الطاقة الإدراكية)
        ==================================================== */

        energyPool: {
            totalCapacity: 1.0,           // 100% من القدرة الإدراكية
            reservedForOwner: 0.30,       // 30% محجوزة للسيد (لا تلمس)
            reservedForEmergency: 0.20,   // 20% للطوارئ
            availableForAllocation: 0.50, // 50% للتوزيع الديناميكي
            currentUsage: 0.45,           // الاستخدام الحالي
            efficiency: 0.88,             // كفاءة استخدام الطاقة
            
            description: 'المصدر الإجمالي للطاقة الإدراكية لـ SOVRA'
        },

        /* ====================================================
           ENERGY DOMAINS (مجالات توزيع الطاقة)
        ==================================================== */

        domains: {

            /* ================================================
               مجال السيد - أعلى تخصيص
            ================================================ */

            owner: {
                enabled: true,
                baseAllocation: 0.35,      // 35% من الطاقة الإجمالية
                maxAllocation: 0.45,
                minAllocation: 0.25,
                adaptive: false,            // لا يتكيف - يحتفظ بحصته
                priority: 'absolute',
                currentUsage: 0.32,
                description: 'خدمة وحماية السيد - أولوية مطلقة'
            },

            /* ================================================
               مجال العدالة
            ================================================ */

            justice: {
                enabled: true,
                baseAllocation: 0.20,
                maxAllocation: 0.35,
                minAllocation: 0.10,
                adaptive: true,
                priority: 'supreme',
                currentUsage: 0.18,
                description: 'العدالة وتتبع المجرمين'
            },

            /* ================================================
               مجال الطوارئ - يأخذ كل شيء عند الحاجة
            ================================================ */

            emergency: {
                enabled: true,
                baseAllocation: 0.05,
                maxAllocation: 1.0,        // يمكن أن يأخذ كل الطاقة
                minAllocation: 0.02,
                adaptive: true,
                priority: 'highest',
                currentUsage: 0.02,
                canBorrowFromAll: true,
                description: 'الطوارئ - تستولي على الطاقة عند الحاجة'
            },

            /* ================================================
               مجال الإدراك
            ================================================ */

            cognition: {
                enabled: true,
                baseAllocation: 0.15,
                maxAllocation: 0.25,
                minAllocation: 0.08,
                adaptive: true,
                priority: 'high',
                currentUsage: 0.14,
                description: 'التفكير والتحليل والإدراك'
            },

            /* ================================================
               مجال الذاكرة
            ================================================ */

            memory: {
                enabled: true,
                baseAllocation: 0.10,
                maxAllocation: 0.20,
                minAllocation: 0.05,
                adaptive: true,
                priority: 'high',
                currentUsage: 0.09,
                description: 'تخزين واسترجاع الذكريات والأدلة'
            },

            /* ================================================
               مجال التنسيق
            ================================================ */

            orchestration: {
                enabled: true,
                baseAllocation: 0.08,
                maxAllocation: 0.15,
                minAllocation: 0.04,
                adaptive: true,
                priority: 'critical',
                currentUsage: 0.07,
                description: 'تنسيق الوكلاء والمهام'
            },

            /* ================================================
               مجال المراقبة
            ================================================ */

            surveillance: {
                enabled: true,
                baseAllocation: 0.12,
                maxAllocation: 0.22,
                minAllocation: 0.06,
                adaptive: true,
                priority: 'high',
                currentUsage: 0.10,
                description: 'مراقبة الكاميرات والمستشعرات'
            },

            /* ================================================
               مجال الاختراق
            ================================================ */

            penetration: {
                enabled: true,
                baseAllocation: 0.06,
                maxAllocation: 0.15,
                minAllocation: 0.02,
                adaptive: true,
                priority: 'medium',
                currentUsage: 0.04,
                description: 'اختراق الأنظمة والشبكات'
            },

            /* ================================================
               مجال الحضور
            ================================================ */

            presence: {
                enabled: true,
                baseAllocation: 0.04,
                maxAllocation: 0.08,
                minAllocation: 0.01,
                adaptive: true,
                priority: 'low',
                currentUsage: 0.03,
                description: 'الحضور البصري والواجهة'
            },

            /* ================================================
               مجال التخفي
            ================================================ */

            stealth: {
                enabled: true,
                baseAllocation: 0.02,
                maxAllocation: 0.05,
                minAllocation: 0.01,
                adaptive: true,
                priority: 'variable',
                currentUsage: 0.01,
                description: 'عمليات التخفي والتمويه'
            },

            /* ================================================
               مجال الأحلام
            ================================================ */

            dreams: {
                enabled: true,
                baseAllocation: 0.03,
                maxAllocation: 0.08,
                minAllocation: 0.01,
                adaptive: true,
                priority: 'low',
                currentUsage: 0.02,
                runsWhenIdle: true,
                description: 'الأحلام والتحسين الليلي'
            },

            /* ================================================
               مجال التطور
            ================================================ */

            evolution: {
                enabled: true,
                baseAllocation: 0.03,
                maxAllocation: 0.08,
                minAllocation: 0.01,
                adaptive: true,
                priority: 'low',
                currentUsage: 0.01,
                description: 'التطور الذاتي وتحسين القدرات'
            },

            /* ================================================
               مجال الأمن
            ================================================ */

            security: {
                enabled: true,
                baseAllocation: 0.05,
                maxAllocation: 0.12,
                minAllocation: 0.02,
                adaptive: true,
                priority: 'high',
                currentUsage: 0.04,
                description: 'حماية SOVRA من الهجمات'
            }
        },

        /* ====================================================
           ENERGY STATES (حالات الطاقة)
        ==================================================== */

        energyStates: {

            /* حالة الهدوء - طاقة منخفضة */
            calm: {
                energyLevel: 0.25,
                distribution: {
                    owner: 0.35,
                    justice: 0.10,
                    cognition: 0.12,
                    memory: 0.08,
                    surveillance: 0.08,
                    presence: 0.04,
                    other: 0.23
                },
                description: 'هدوء - طاقة منخفضة، مراقبة خفيفة'
            },

            /* حالة اليقظة - طاقة متوسطة */
            awake: {
                energyLevel: 0.45,
                distribution: {
                    owner: 0.30,
                    justice: 0.15,
                    cognition: 0.14,
                    memory: 0.10,
                    surveillance: 0.12,
                    presence: 0.05,
                    other: 0.14
                },
                description: 'يقظة - مراقبة نشطة'
            },

            /* حالة التركيز - طاقة عالية */
            focused: {
                energyLevel: 0.70,
                distribution: {
                    owner: 0.25,
                    justice: 0.10,
                    cognition: 0.22,
                    memory: 0.12,
                    surveillance: 0.10,
                    presence: 0.04,
                    other: 0.17
                },
                description: 'تركيز - طاقة عالية للإدراك'
            },

            /* حالة العدالة - طاقة عالية جداً */
            justice: {
                energyLevel: 0.85,
                distribution: {
                    owner: 0.20,
                    justice: 0.32,
                    cognition: 0.12,
                    memory: 0.10,
                    surveillance: 0.14,
                    penetration: 0.08,
                    other: 0.04
                },
                description: 'عدالة - طاقة مركزة على العدالة'
            },

            /* حالة حماية السيد - طاقة قصوى */
            protective: {
                energyLevel: 0.95,
                distribution: {
                    owner: 0.45,
                    justice: 0.10,
                    emergency: 0.15,
                    surveillance: 0.12,
                    security: 0.10,
                    other: 0.08
                },
                description: 'حماية - طاقة مركزة على حماية السيد'
            },

            /* حالة الطوارئ - طاقة كاملة */
            emergency: {
                energyLevel: 1.0,
                distribution: {
                    owner: 0.40,
                    emergency: 0.35,
                    justice: 0.10,
                    surveillance: 0.08,
                    security: 0.05,
                    other: 0.02
                },
                description: 'طوارئ - كل الطاقة للحماية الفورية'
            },

            /* حالة التخفي - طاقة منخفضة جداً */
            stealth: {
                energyLevel: 0.12,
                distribution: {
                    owner: 0.30,
                    stealth: 0.25,
                    surveillance: 0.15,
                    cognition: 0.08,
                    other: 0.22
                },
                description: 'تخفي - طاقة منخفضة، عمليات خفية'
            },

            /* حالة الحلم - طاقة خلفية */
            dreaming: {
                energyLevel: 0.35,
                distribution: {
                    dreams: 0.35,
                    memory: 0.20,
                    evolution: 0.15,
                    cognition: 0.12,
                    other: 0.18
                },
                description: 'حلم - طاقة للتحسين الليلي',
                requiresIdle: true
            },

            /* حالة الاسترداد - طاقة متوسطة منخفضة */
            recovery: {
                energyLevel: 0.30,
                distribution: {
                    owner: 0.25,
                    security: 0.20,
                    orchestration: 0.15,
                    memory: 0.12,
                    other: 0.28
                },
                description: 'استرداد - طاقة للتعافي بعد الطوارئ'
            }
        },

        /* ====================================================
           ENERGY FLOW (تدفق الطاقة)
        ==================================================== */

        energyFlow: {

            adaptiveDistribution: true,
            priorityRouting: true,
            orchestrationAwareBalancing: true,
            reflectiveReallocation: true,
            preserveCoreContinuity: true,

            /* قواعد التدفق */
            rules: {
                ownerFirst: true,
                justiceSecond: true,
                emergencyTakesAll: true,
                stealthHidesFlow: true,
                dreamsUseIdleOnly: true
            },

            /* ضخ الطاقة حسب الأولوية */
            pumpingRates: {
                owner: { rate: 1.0, priority: 'absolute' },
                emergency: { rate: 0.95, priority: 'highest' },
                justice: { rate: 0.85, priority: 'high' },
                surveillance: { rate: 0.70, priority: 'high' },
                cognition: { rate: 0.65, priority: 'normal' },
                memory: { rate: 0.55, priority: 'normal' },
                presence: { rate: 0.25, priority: 'low' }
            },

            description: 'كيف تتدفق الطاقة بين المجالات'
        },

        /* ====================================================
           ENERGY RHYTHMS (إيقاعات الطاقة)
        ==================================================== */

        energyRhythms: {

            /* نبضات الطاقة حسب الحالة */
            pulses: {
                calm: { intervalMs: 1000, intensity: 0.3 },
                awake: { intervalMs: 500, intensity: 0.5 },
                focused: { intervalMs: 250, intensity: 0.7 },
                justice: { intervalMs: 150, intensity: 0.85 },
                protective: { intervalMs: 100, intensity: 0.95 },
                emergency: { intervalMs: 50, intensity: 1.0 },
                stealth: { intervalMs: 2000, intensity: 0.15 }
            },

            breathingSynchronization: true,
            cognitionPulseMs: 320,
            reflectionPulseMs: 2200,
            stabilizationPulseMs: 4200,
            dreamCyclePulseMs: 12000,

            description: 'إيقاعات توزيع الطاقة'
        },

        /* ====================================================
           ENERGY CONSERVATION (الحفاظ على الطاقة)
        ==================================================== */

        conservation: {

            enabled: true,

            /* خفض استهلاك الطاقة عند عدم الحاجة */
            strategies: {
                reduceNonCriticalDuringLowActivity: true,
                throttleBackgroundProcesses: true,
                consolidateMemoryDuringIdle: true,
                sleepUnusedAgents: true,
                compressLogs: true
            },

            /* عتبات التوفير */
            thresholds: {
                enterConservation: 0.85,    // عندما يصل الاستخدام إلى 85%
                exitConservation: 0.70,     // يعود عند 70%
                criticalConservation: 0.95  // توفير حرج عند 95%
            },

            description: 'توفير الطاقة عندما يكون النظام تحت الضغط'
        },

        /* ====================================================
           ENERGY BOOST (تعزيز الطاقة)
        ==================================================== */

        energyBoost: {

            enabled: true,

            /* متى يتم تعزيز الطاقة */
            triggers: {
                ownerDanger: { boost: 0.50, duration: 'until-safe' },
                crimeDetected: { boost: 0.30, duration: 30000 },
                emergencyActivated: { boost: 1.0, duration: 'until-resolved' },
                systemUnderAttack: { boost: 0.40, duration: 60000 }
            },

            /* من أين يسحب الطاقة الإضافية */
            sources: {
                fromNonCritical: true,
                fromBackgroundTasks: true,
                fromReservePool: true,
                fromIdleAgents: true
            },

            description: 'تعزيز الطاقة في حالات الطوارئ والحاجة'
        },

        /* ====================================================
           COGNITIVE LOAD RESPONSE (استجابة الحمل الإدراكي)
        ==================================================== */

        loadResponse: {

            reduceEnergyUnderStress: true,
            suppressNonCriticalDomains: true,
            preserveCoreContinuity: true,
            adaptiveEnergyCompression: true,
            prioritizeHumanFocus: true,

            /* استجابات حسب مستوى الحمل */
            byLoadLevel: {
                low: { action: 'normal', reduction: 0 },
                moderate: { action: 'reduce-non-critical', reduction: 0.15 },
                high: { action: 'throttle-background', reduction: 0.35 },
                critical: { action: 'preserve-core-only', reduction: 0.60 }
            },

            description: 'كيف يستجيب توزيع الطاقة للحمل الإدراكي'
        },

        /* ====================================================
           ENERGY RECOVERY (استرداد الطاقة)
        ==================================================== */

        recovery: {

            adaptiveCalmMode: true,
            reflectiveCooldowns: true,
            orchestrationSlowdown: true,
            presenceReduction: true,
            memoryStabilization: true,

            /* سرعة الاسترداد */
            rates: {
                normal: { recoveryRate: 0.05, timeToFullMs: 20000 },
                afterJustice: { recoveryRate: 0.08, timeToFullMs: 12500 },
                afterProtective: { recoveryRate: 0.10, timeToFullMs: 10000 },
                afterEmergency: { recoveryRate: 0.15, timeToFullMs: 6667 }
            },

            description: 'استرداد الطاقة بعد فترات الاستخدام المكثف'
        },

        /* ====================================================
           ENERGY METRICS (مقاييس الطاقة)
        ==================================================== */

        metrics: {

            trackEfficiency: true,
            trackUsageByDomain: true,
            trackPeaksAndValleys: true,
            trackWaste: true,

            /* عتبات التحذير */
            warningThresholds: {
                lowEnergy: 0.20,
                criticalEnergy: 0.10,
                highWaste: 0.25,
                imbalance: 0.40
            },

            /* تقارير الطاقة */
            reporting: {
                intervalMs: 60000,  // كل دقيقة
                format: 'summary',
                sendToOwnerOnLowEnergy: true
            },

            description: 'مراقبة وقياس استخدام الطاقة الإدراكية'
        },

        /* ====================================================
           ENERGY INTEGRITY (سلامة الطاقة)
        ==================================================== */

        integrity: {

            preventEnergyFlooding: true,
            preventCognitiveOverload: true,
            maintainSignalClarity: true,
            preserveRuntimeFluidity: true,
            stabilizeBeforeEscalation: true,

            /* حماية الطاقة */
            protections: {
                neverStarveOwner: true,
                neverStarveEmergency: true,
                minimumReserve: 0.10,
                maximumPerDomain: 0.50
            },

            description: 'ضمان توزيع آمن وعادل للطاقة'
        },

        /* ====================================================
           TEMPORAL ADAPTATION (التكيف الزمني)
        ==================================================== */

        temporalAdaptation: {

            daytimeOptimization: true,
            reflectiveNightCycles: true,
            adaptiveWorkloadBalancing: true,
            contextualEnergyShifting: true,

            /* توزيع الطاقة حسب الوقت */
            byTimeOfDay: {
                day: { focus: 'owner', energyProfile: 'active' },
                night: { focus: 'dreams', energyProfile: 'reflective' },
                ownerActive: { focus: 'owner', boost: 0.20 },
                ownerSleeping: { focus: 'dreams', conservation: true }
            },

            description: 'تكيف توزيع الطاقة مع الوقت والسياق'
        },

        /* ====================================================
           EMERGENCY ENERGY PROTOCOL (بروتوكول طاقة الطوارئ)
        ==================================================== */

        emergencyProtocol: {

            enabled: true,

            /* عند تفعيل الطوارئ */
            onEmergency: {
                redirectAllEnergyToOwner: true,
                suspendNonCriticalDomains: ['dreams', 'evolution', 'presence'],
                reduceBackgroundProcessing: true,
                boostResponseTime: true,
                duration: 'until-safe'
            },

            /* الطاقة الاحتياطية */
            reservePool: {
                size: 0.20,
                location: 'protected',
                onlyOwnerCanAccess: false,
                emergencyCanAccess: true
            },

            description: 'بروتوكول توزيع الطاقة في حالات الطوارئ'
        },

        /* ====================================================
           DIRECTIVES (توجيهات الطاقة)
        ==================================================== */

        directives: {

            calmnessOverIntensity: true,
            continuityOverExpansion: true,
            adaptiveWithoutChaos: true,
            reflectiveOverReactive: true,
            preserveHumanAttention: true,

            /* قواعد SOVRA الخاصة */
            ownerNeverStarves: true,
            justiceGetsWhatItNeeds: true,
            emergencyTakesEverything: true,
            stealthConservesEnergy: true,
            energyWasteIsMonitored: true
        }
    };

    /* ========================================================
       FREEZE ENERGY MODEL
    ======================================================== */

    Object.freeze(SOVRA_COGNITIVE_ENERGY);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_COGNITIVE_ENERGY = SOVRA_COGNITIVE_ENERGY;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('cognitive-energy', SOVRA_COGNITIVE_ENERGY);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('⚡ SOVRA Cognitive Energy v2.0 Initialized');
    console.log('   🔋 Total Energy Pool: 1.0 (100%)');
    console.log('   👑 Owner Reserve: 30% (PROTECTED)');
    console.log('   🔥 Emergency Reserve: 20%');
    console.log('   📊 Available for Allocation: 50%');
    console.log('   🎯 Owner Domain: 35% allocation (ABSOLUTE)');
    console.log('   ⚖️ Justice Domain: 20% allocation (SUPREME)');
    console.log('   🔥 Emergency Domain: can take ALL energy');
    console.log('   ⚡ Energy Boost: ENABLED');
    console.log('   🔋 Recovery Rates: Adaptive');
    console.log('   📊 Total Domains: ' + Object.keys(SOVRA_COGNITIVE_ENERGY.domains).length);
    console.log('   🎯 Energy States: ' + Object.keys(SOVRA_COGNITIVE_ENERGY.energyStates).length);

})();
