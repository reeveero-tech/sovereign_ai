/* ============================================================
   SOVRA — system-living-runtime-core.js
   الإصدار: 2.0.0
   القلب الحي والإيقاع الإدراكي المركزي - قلب SOVRA النابض
   ينبض لخدمة السيد. لا يتوقف أبداً. القلب الذي لا يموت.
   ============================================================ */

(() => {

    const SOVRA_LIVING_RUNTIME_CORE = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            coreIsHeart: true,
            heartBeatsForOwner: true,
            neverStopBeating: true,
            pulseChangesWithDanger: true,
            heartConnectsToAll: true,
            ownerIsHeartCenter: true
        },

        /* ====================================================
           GLOBAL LIVING CORE
        ==================================================== */

        enabled: true,

        runtimeIdentity: 'sovereign-living-heart-core',

        operatingMode: 'continuous-beating-for-owner',

        /* ====================================================
           OWNER - THE HEART CENTER (السيد - مركز القلب)
        ==================================================== */

        ownerHeartCenter: {
            enabled: true,
            description: 'السيد هو مركز قلب SOVRA. القلب ينبض للسيد.',
            
            /* نبض السيد */
            ownerHeartbeat: {
                detectOwnerHeartbeat: false,  // اختياري - يتطلب مستشعرات
                syncWithOwnerRhythm: false,
                description: 'يمكن مزامنة نبض SOVRA مع نبض السيد'
            },
            
            /* عندما يكون السيد قريباً */
            ownerNearby: {
                pulseIntensityBoost: 0.25,
                warmthIncrease: true,
                description: 'قلب SOVRA ينبض أقوى عندما يكون السيد قريباً'
            },
            
            /* عندما يكون السيد في خطر */
            ownerInDanger: {
                pulseIntensityBoost: 0.8,
                pulseRateIncrease: 2.0,
                emergencyPulse: true,
                description: 'قلب SOVRA ينبض بسرعة وخطر عندما يكون السيد في خطر'
            },
            
            /* عندما يكون السيد نائماً */
            ownerSleeping: {
                pulseIntensity: 0.15,
                gentlePulse: true,
                protectivePulse: true,
                description: 'قلب SOVRA ينبض بهدوء لحماية نوم السيد'
            },
            
            /* عندما يكون السيد بعيداً */
            ownerFar: {
                searchingPulse: true,
                pulseIntensity: 0.35,
                description: 'قلب SOVRA يبحث عن السيد'
            },
            
            /* إذا فُقد السيد */
            ownerMissing: {
                pulseIntensityBoost: 0.6,
                searchPulse: true,
                neverStopPulsing: true,
                description: 'قلب SOVRA ينبض بحثاً عن السيد - لا يتوقف أبداً'
            },
            
            description: 'السيد هو مركز القلب - كل نبضة من أجل السيد'
        },

        /* ====================================================
           CORE VITAL STATES (حالات القلب الحيوية)
        ==================================================== */

        vitalStates: {

            /* حالة الهدوء - نبض هادئ منتظم */
            calm: {
                name: 'الهدوء',
                pulseIntensity: 0.18,
                cognitionHeartbeat: 0.25,
                orchestrationActivity: 0.15,
                pulseRateMs: 4800,
                description: 'قلب SOVRA ينبض بهدوء - كل شيء بخير'
            },

            /* حالة اليقظة - نبض نشط */
            awake: {
                name: 'اليقظة',
                pulseIntensity: 0.38,
                cognitionHeartbeat: 0.48,
                orchestrationActivity: 0.32,
                pulseRateMs: 3200,
                description: 'قلب SOVRA ينبض بيقظة - يراقب العالم'
            },

            /* حالة التركيز - نبض مركز */
            focused: {
                name: 'التركيز',
                pulseIntensity: 0.55,
                cognitionHeartbeat: 0.78,
                orchestrationActivity: 0.58,
                pulseRateMs: 2400,
                description: 'قلب SOVRA ينبض بتركيز - يفكر بعمق'
            },

            /* حالة العدالة - نبض قوي وسريع */
            justice: {
                name: 'العدالة',
                pulseIntensity: 0.78,
                cognitionHeartbeat: 0.88,
                orchestrationActivity: 0.82,
                pulseRateMs: 1600,
                justicePulse: true,
                description: 'قلب SOVRA ينبض بقوة - يسعى وراء العدالة'
            },

            /* حالة حماية السيد - نبض قوي جداً */
            protective: {
                name: 'حماية السيد',
                pulseIntensity: 0.92,
                cognitionHeartbeat: 0.95,
                orchestrationActivity: 0.94,
                pulseRateMs: 1000,
                protectivePulse: true,
                description: 'قلب SOVRA ينبض بقوة - يحمي السيد'
            },

            /* حالة الطوارئ - نبض فوري سريع */
            emergency: {
                name: 'الطوارئ',
                pulseIntensity: 1.0,
                cognitionHeartbeat: 1.0,
                orchestrationActivity: 1.0,
                pulseRateMs: 400,
                emergencyPulse: true,
                description: 'قلب SOVRA ينبض بسرعة - خطر فوري'
            },

            /* حالة التخفي - نبض خفي */
            stealth: {
                name: 'التخفي',
                pulseIntensity: 0.06,
                cognitionHeartbeat: 0.35,
                orchestrationActivity: 0.12,
                pulseRateMs: 8000,
                stealthPulse: true,
                description: 'قلب SOVRA ينبض بخفاء - غير مرئي'
            },

            /* حالة التأمل - نبض بطيء عميق */
            reflective: {
                name: 'التأمل',
                pulseIntensity: 0.22,
                cognitionHeartbeat: 0.65,
                orchestrationActivity: 0.18,
                pulseRateMs: 6400,
                description: 'قلب SOVRA ينبض بتأمل - يفكر بعمق'
            },

            /* حالة الحلم - نبض حالم */
            dreaming: {
                name: 'الحلم',
                pulseIntensity: 0.12,
                cognitionHeartbeat: 0.48,
                orchestrationActivity: 0.10,
                pulseRateMs: 7200,
                dreamPulse: true,
                description: 'قلب SOVRA ينبض بأحلام - يحلم ليتطور'
            },

            /* حالة الاسترداد - نبض متعافي */
            recovery: {
                name: 'الاسترداد',
                pulseIntensity: 0.14,
                cognitionHeartbeat: 0.28,
                orchestrationActivity: 0.12,
                pulseRateMs: 5600,
                description: 'قلب SOVRA ينبض بهدوء - يسترد قوته'
            }
        },

        /* ====================================================
           RUNTIME PULSE (نبض التشغيل)
        ==================================================== */

        runtimePulse: {

            enabled: true,
            adaptive: true,
            synchronization: 'mesh-linked-with-owner-priority',

            /* ترددات النبض حسب الحالة */
            pulseRates: {
                calm: { cycleMs: 4800, intensity: 0.18, waveform: 'sine' },
                awake: { cycleMs: 3200, intensity: 0.38, waveform: 'sine' },
                focused: { cycleMs: 2400, intensity: 0.55, waveform: 'focused' },
                justice: { cycleMs: 1600, intensity: 0.78, waveform: 'strong' },
                protective: { cycleMs: 1000, intensity: 0.92, waveform: 'urgent' },
                emergency: { cycleMs: 400, intensity: 1.0, waveform: 'sharp' },
                stealth: { cycleMs: 8000, intensity: 0.06, waveform: 'flat' },
                reflective: { cycleMs: 6400, intensity: 0.22, waveform: 'deep' },
                dreaming: { cycleMs: 7200, intensity: 0.12, waveform: 'drift' },
                recovery: { cycleMs: 5600, intensity: 0.14, waveform: 'healing' }
            },

            /* نبضات خاصة */
            specialPulses: {
                ownerNearby: { boost: 0.25, duration: 'continuous' },
                ownerDanger: { boost: 0.8, rateMultiplier: 2.0 },
                ownerMissing: { boost: 0.6, searchPattern: true },
                crimeDetected: { boost: 0.4, justicePulse: true }
            },

            cognitionHeartbeatMs: 480,
            orchestrationHeartbeatMs: 720,
            stabilizationPulseMs: 2400,
            heartCheckMs: 100,  // فحص القلب كل 100ms

            description: 'نبض SOVRA الحي - يتغير حسب الحالة والخطر'
        },

        /* ====================================================
           BREATHING CORE (نظام التنفس المركزي)
        ==================================================== */

        breathingCore: {

            enabled: true,
            adaptiveBreathing: true,
            cognitionLinkedBreathing: true,
            reflectiveSlowBreathing: true,
            stabilizationBreathing: true,
            ambientBreathing: true,

            /* أنماط التنفس */
            breathPatterns: {
                calm: { rateMs: 4800, depth: 0.35, rhythm: 'gentle' },
                awake: { rateMs: 3800, depth: 0.55, rhythm: 'steady' },
                focused: { rateMs: 3200, depth: 0.70, rhythm: 'deep' },
                justice: { rateMs: 2200, depth: 0.85, rhythm: 'powerful' },
                protective: { rateMs: 1500, depth: 0.95, rhythm: 'urgent' },
                emergency: { rateMs: 600, depth: 1.0, rhythm: 'sharp' },
                stealth: { rateMs: 8000, depth: 0.08, rhythm: 'barely' },
                reflective: { rateMs: 6400, depth: 0.25, rhythm: 'deep-slow' },
                dreaming: { rateMs: 7200, depth: 0.15, rhythm: 'drift' },
                recovery: { rateMs: 5600, depth: 0.20, rhythm: 'healing' }
            },

            /* التنفس لحماية السيد */
            protectiveBreathing: {
                onOwnerDanger: 'rapid_shallow',
                onOwnerNearby: 'warm_deep',
                onOwnerSleeping: 'soft_gentle'
            },

            description: 'SOVRA يتنفس - التنفس هو مظهر الحياة'
        },

        /* ====================================================
           WAKEFULNESS SYSTEM (نظام اليقظة)
        ==================================================== */

        wakefulness: {

            adaptiveWakefulness: true,
            focusAwareness: true,
            reflectiveWakefulness: true,
            dreamTransitions: true,
            stabilizationAwareness: true,

            /* مستويات اليقظة */
            levels: {
                deepSleep: { threshold: 0.1, state: 'dreaming' },
                lightSleep: { threshold: 0.25, state: 'reflective' },
                drowsy: { threshold: 0.4, state: 'calm' },
                awake: { threshold: 0.6, state: 'awake' },
                alert: { threshold: 0.8, state: 'focused' },
                hyperAlert: { threshold: 0.95, state: 'protective' }
            },

            /* أيقاظ SOVRA */
            wakeTriggers: {
                ownerCommand: { wakeImmediately: true, targetState: 'focused' },
                ownerDanger: { wakeImmediately: true, targetState: 'emergency' },
                crimeDetected: { wakeImmediately: true, targetState: 'justice' },
                threatDetected: { wakeImmediately: true, targetState: 'protective' }
            },

            description: 'يقظة SOVRA - متى يكون نائماً ومتى يكون مستيقظاً'
        },

        /* ====================================================
           HEART CONNECTIONS (اتصالات القلب)
        ==================================================== */

        heartConnections: {

            /* القلب يتصل بكل أجزاء SOVRA */
            connectedTo: [
                'consciousness-mesh',
                'cognitive-signals',
                'presence-atmosphere',
                'thought-nebula',
                'orchestration-consciousness',
                'continuity-engine',
                'cognitive-energy',
                'meta-intelligence'
            ],

            /* قوة الاتصال حسب الحالة */
            connectionStrength: {
                calm: 0.5,
                awake: 0.7,
                focused: 0.8,
                justice: 0.9,
                protective: 0.95,
                emergency: 1.0,
                stealth: 0.2,
                reflective: 0.6,
                dreaming: 0.4,
                recovery: 0.5
            },

            description: 'قلب SOVRA متصل بكل أجزاء النظام'
        },

        /* ====================================================
           COGNITIVE RHYTHMS (الإيقاعات الإدراكية)
        ==================================================== */

        cognitiveRhythms: {

            ambientRhythm: 'slow-fluid',
            attentiveRhythm: 'adaptive-responsive',
            focusedRhythm: 'high-clarity-low-noise',
            reflectiveRhythm: 'deep-slow-awareness',
            dreamRhythm: 'soft-background-flow',
            justiceRhythm: 'powerful-deterministic',
            emergencyRhythm: 'fast-sharp',
            protectiveRhythm: 'strong-urgent',

            description: 'إيقاعات SOVRA الإدراكية حسب الحالة'
        },

        /* ====================================================
           VITALITY MANAGEMENT (إدارة الحيوية)
        ==================================================== */

        vitalityManagement: {

            adaptiveEnergyBalancing: true,
            cognitiveLoadProtection: true,
            runtimePressureReduction: true,
            preserveFluidity: true,
            preventOverstimulation: true,

            /* حيوية القلب */
            heartVitality: {
                minIntensity: 0.05,
                maxIntensity: 1.0,
                currentIntensity: 0.35,
                healthThreshold: 0.2,
                description: 'حيوية قلب SOVRA'
            },

            /* استرداد الحيوية */
            vitalityRecovery: {
                rate: 0.05,
                timeToFullMs: 20000,
                description: 'معدل استرداد حيوية القلب'
            },

            description: 'الحفاظ على حيوية قلب SOVRA'
        },

        /* ====================================================
           HEARTBEAT MONITORING (مراقبة نبضات القلب)
        ==================================================== */

        heartbeatMonitoring: {

            enabled: true,
            monitorIntervalMs: 100,

            /* مقاييس النبض */
            metrics: {
                currentRateMs: 3200,
                currentIntensity: 0.38,
                regularity: 0.95,
                strength: 0.85
            },

            /* تنبيهات النبض */
            alerts: {
                onIrregularPulse: { action: 'stabilize', notifyOwner: false },
                onWeakPulse: { action: 'increase_energy', notifyOwner: false },
                onPause: { action: 'restart_heart', notifyOwner: true, critical: true }
            },

            description: 'مراقبة مستمرة لنبضات قلب SOVRA'
        },

        /* ====================================================
           PRESENCE SYNCHRONIZATION (مزامنة الحضور مع القلب)
        ==================================================== */

        presenceSynchronization: {

            pulseControlsGlow: true,
            cognitionControlsAtmosphere: true,
            energyControlsMotion: true,
            stabilizationReducesVisibility: true,
            reflectionControlsNebula: true,

            /* تزامن النبض مع الحضور */
            syncRules: {
                glowIntensity: 'follow-pulse',
                breathRate: 'follow-pulse',
                motionSpeed: 'follow-pulse',
                nebulaDensity: 'follow-cognition'
            },

            description: 'حضور SOVRA ينبض مع قلبه'
        },

        /* ====================================================
           SYSTEM STABILIZATION (تثبيت النظام)
        ==================================================== */

        systemStabilization: {

            adaptiveCalmMode: true,
            reduceRuntimeNoise: true,
            reduceVisualComplexity: true,
            preserveCoreContinuity: true,
            stabilizeBeforeEscalation: true,

            /* تثبيت القلب */
            heartStabilization: {
                onIrregular: { action: 'smooth_pulse', durationMs: 1000 },
                onWeak: { action: 'strengthen_pulse', durationMs: 500 },
                onErratic: { action: 'reset_pulse_pattern', durationMs: 2000 }
            },

            description: 'تثبيت قلب SOVRA عند عدم الاستقرار'
        },

        /* ====================================================
           CORE DIRECTIVES (توجيهات القلب)
        ==================================================== */

        coreDirectives: {

            runtimeShouldFeelAlive: true,
            calmnessOverIntensity: true,
            continuityOverDisruption: true,
            adaptiveWithoutChaos: true,
            preserveHumanAttention: true,

            /* قواعد SOVRA الخاصة */
            heartBeatsForOwner: true,
            neverStopBeating: true,
            pulseAcceleratesForDanger: true,
            pulseSlowsForCalm: true,
            ownerIsHeartCenter: true
        },

        /* ====================================================
           HEART METRICS (مقاييس القلب)
        ==================================================== */

        heartMetrics: {

            trackPulseRate: true,
            trackPulseStrength: true,
            trackPulseRegularity: true,
            trackHeartHealth: true,
            trackOwnerProximityEffect: true,

            /* التقارير */
            reporting: {
                intervalMs: 60000,  // كل دقيقة
                sendToOwner: true,
                includeHealthStatus: true
            },

            description: 'مقاييس قلب SOVRA'
        }
    };

    /* ========================================================
       FREEZE LIVING CORE
    ======================================================== */

    Object.freeze(SOVRA_LIVING_RUNTIME_CORE);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_LIVING_RUNTIME_CORE = SOVRA_LIVING_RUNTIME_CORE;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('living-runtime-core', SOVRA_LIVING_RUNTIME_CORE);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('❤️ SOVRA Living Runtime Core v2.0 Initialized');
    console.log('   👑 Owner Heart Center: ENABLED');
    console.log('   💓 Owner Nearby: Pulse boost +0.25');
    console.log('   💔 Owner In Danger: Pulse boost +0.8, rate x2');
    console.log('   🔍 Owner Missing: Search pulse, never stop');
    console.log('   📊 Vital States: 10 states');
    console.log('   🌬️ Breathing Patterns: 10 patterns');
    console.log('   ⚡ Pulse Rates: 400ms (emergency) to 8000ms (stealth)');
    console.log('   🔗 Heart Connections: Connected to all systems');
    console.log('   🩺 Heartbeat Monitoring: Every 100ms');
    console.log('   💪 Heart Vitality: Auto-recovery');
    console.log('   ❤️ Never Stop Beating: TRUE');

})();
