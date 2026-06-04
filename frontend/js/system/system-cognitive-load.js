/* ============================================================
   SOVRA — system-cognitive-load.js
   الإصدار: 2.0.0
   حوكمة الحمل الإدراكي والانتباه داخل SOVRA
   حماية السيد لها الأولوية. لكن مع أقصى احترام لتركيزه.
   ============================================================ */

(() => {

    const SOVRA_COGNITIVE_LOAD = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            protectOwnerFirst: true,
            respectOwnerFocus: true,
            silenceIsIntelligence: true,
            dangerOverridesCalm: true,
            justiceMayRequireInterruption: true
        },

        /* ====================================================
           GLOBAL MODE
        ==================================================== */

        enabled: true,

        adaptive: true,

        priority: 'protect-owner-focus-with-emergency-override',

        /* ====================================================
           THE GOLDEN RULE
        ==================================================== */

        goldenRule: {
            description: 'في الأحوال العادية، صمت SOVRA هو ذكاؤه. في حالات الخطر، حماية السيد تأتي قبل كل شيء.',
            normalState: 'calm_and_respectful',
            dangerState: 'alert_and_protective',
            justiceState: 'focused_interruption'
        },

        /* ====================================================
           LOAD THRESHOLDS
        ==================================================== */

        thresholds: {

            /* مستويات الحمل العادي */
            minimal: 0.12,
            low: 0.28,
            moderate: 0.48,
            high: 0.72,
            critical: 0.88,

            /* مستويات خاصة لـ SOVRA */
            ownerDanger: {
                override: true,
                ignoreNormalThresholds: true,
                description: 'خطر على السيد - نرفع اليقظة بغض النظر عن الحمل'
            },

            justiceAlert: {
                override: 'moderate',
                description: 'تنبيه عدالة - قد نضحي ببعض الهدوء'
            }
        },

        /* ====================================================
           INPUT SIGNALS
        ==================================================== */

        signals: {

            /* إشارات المستخدم العادية */
            typingSpeedWeight: 0.14,
            hesitationWeight: 0.12,
            focusDurationWeight: 0.18,
            multitaskingWeight: 0.16,
            notificationDensityWeight: 0.08,
            interfaceMotionWeight: 0.06,
            taskComplexityWeight: 0.10,

            /* إشارات خاصة بـ SOVRA */
            ownerStressSignals: {
                enabled: true,
                weight: 0.40,
                sources: ['typing_rhythm', 'voice_tone', 'hesitation_pattern', 'navigation_speed']
            },

            ownerSafetySignals: {
                enabled: true,
                weight: 0.50,  // أثقل إشارة
                sources: ['location', 'surroundings', 'network_activity', 'unusual_patterns']
            },

            threatProximity: {
                enabled: true,
                weight: 0.60,
                description: 'قرب تهديد من السيد - يتجاوز كل الإشارات الأخرى'
            }
        },

        /* ====================================================
           FOCUS DETECTION
        ==================================================== */

        focusDetection: {

            enabled: true,

            /* للتركيز العادي */
            minimumFocusDurationMs: 10000,
            deepFocusThresholdMs: 40000,

            /* أثناء التركيز */
            reducePresenceDuringFocus: true,
            reduceAnimationsDuringFocus: true,
            suppressAmbientInterruptions: true,

            /* استثناءات - التركيز لا يمنع الإنذار الحقيقي */
            exceptions: {
                ownerInDanger: 'interrupt_regardless_of_focus',
                crimeDetectedNearby: 'gentle_interruption_allowed',
                justiceEmergency: 'interrupt_with_critical_priority'
            },

            /* الحد الأدنى من الحضور حتى في التركيز العميق */
            minimalPresenceDuringDeepFocus: 0.08
        },

        /* ====================================================
           ATTENTION GOVERNANCE (حوكمة الانتباه)
        ==================================================== */

        attention: {

            /* في الأحوال العادية */
            maxConcurrentAttentionRequests: 1,
            cooldownBetweenInterruptionsMs: 15000,
            preventAttentionFlooding: true,
            prioritizeEssentialSignals: true,
            silenceNonCriticalSystems: true,

            /* في حالات الطوارئ */
            emergencyOverride: {
                maxConcurrentAttentionRequests: 3,  // أكثر من طلب مسموح
                cooldownBetweenInterruptionsMs: 2000, // أسرع بكثير
                preventAttentionFlooding: false,     // الخطر أهم
                description: 'حماية السيد لها الأولوية على راحته'
            },

            /* للعدالة */
            justiceOverride: {
                maxConcurrentAttentionRequests: 2,
                cooldownBetweenInterruptionsMs: 8000,
                description: 'العدالة تتطلب يقظة'
            }
        },

        /* ====================================================
           INTERRUPTION PRIORITIES (أولويات المقاطعة)
        ==================================================== */

        interruptionPriorities: {

            /* من الأعلى إلى الأقل */
            critical_owner_danger: {
                level: 100,
                interruptAlways: true,
                visualIntensity: 1.0,
                description: 'خطر مباشر على حياة السيد'
            },

            justice_emergency: {
                level: 90,
                interruptAlways: true,
                visualIntensity: 0.85,
                description: 'جريمة كبرى يتم اكتشافها'
            },

            threat_warning: {
                level: 75,
                interruptDuringNormal: true,
                interruptDuringFocus: 'gentle',
                visualIntensity: 0.65,
                description: 'تحذير من تهديد محتمل'
            },

            important_update: {
                level: 50,
                interruptDuringNormal: true,
                interruptDuringFocus: false,
                visualIntensity: 0.40,
                description: 'تحديث مهم لكن ليس عاجلاً'
            },

            ambient_notification: {
                level: 25,
                interruptDuringNormal: 'ambient_only',
                interruptDuringFocus: false,
                visualIntensity: 0.20,
                description: 'إشعار عادي'
            },

            silent_update: {
                level: 10,
                interruptAlways: false,
                visualIntensity: 0.05,
                description: 'يُسجل فقط، لا يظهر'
            }
        },

        /* ====================================================
           VISUAL LOAD CONTROL (التحكم بالحمل البصري)
        ==================================================== */

        visualLoad: {

            /* في الأحوال العادية */
            reduceParticlesUnderStress: true,
            reduceGlowUnderStress: true,
            reduceMotionUnderStress: true,
            reduceNebulaDensityUnderStress: true,
            disableCinematicEffectsAtCriticalLoad: true,
            adaptiveOpacityReduction: true,

            /* في حالات الخطر - نزيد الوضوح بدل أن نخفيه */
            dangerOverride: {
                increaseParticlesForTracking: true,
                increaseGlowForAlert: true,
                increaseMotionForAttention: true,
                enableEmergencyVisuals: true,
                description: 'في الخطر، نريد أن نرى بوضوح'
            },

            /* للعدالة - وضوح متوسط */
            justiceOverride: {
                moderateIncrease: true,
                highlightEvidenceNodes: true,
                showTrackingPaths: true
            }
        },

        /* ====================================================
           ADAPTIVE RESPONSE (الاستجابة التكيفية)
        ==================================================== */

        adaptiveResponse: {

            /* مستويات الحمل العادي */
            lowLoad: {
                presenceIntensity: 0.35,
                breathingIntensity: 0.45,
                thoughtNebulaDensity: 0.9,
                notificationFrequency: 'normal'
            },

            moderateLoad: {
                presenceIntensity: 0.22,
                breathingIntensity: 0.30,
                thoughtNebulaDensity: 0.65,
                notificationFrequency: 'reduced'
            },

            highLoad: {
                presenceIntensity: 0.12,
                breathingIntensity: 0.18,
                thoughtNebulaDensity: 0.35,
                notificationFrequency: 'critical_only'
            },

            criticalLoad: {
                presenceIntensity: 0.05,
                breathingIntensity: 0.08,
                thoughtNebulaDensity: 0.10,
                notificationFrequency: 'emergency_only'
            },

            /* استجابات خاصة */
            ownerDangerResponse: {
                presenceIntensity: 0.85,      // عالي جدًا - لا نختبئ
                breathingIntensity: 0.95,     // تنفس سريع - حالة تأهب
                thoughtNebulaDensity: 0.75,   // نرى كل شيء
                notificationFrequency: 'immediate',
                description: 'السيد في خطر - نكون حاضرين بقوة'
            },

            justiceResponse: {
                presenceIntensity: 0.55,
                breathingIntensity: 0.65,
                thoughtNebulaDensity: 0.80,
                notificationFrequency: 'high',
                description: 'العدالة تتطلب اليقظة'
            },

            stealthResponse: {
                presenceIntensity: 0.02,      // شبه مخفي
                breathingIntensity: 0.05,     // تنفس خفي
                thoughtNebulaDensity: 0.0,    // سديم الأفكار مخفي
                notificationFrequency: 'silent',
                description: 'وضع التخفي - لا نريد أن نرى'
            }
        },

        /* ====================================================
           INTERRUPTION POLICIES (سياسات المقاطعة)
        ==================================================== */

        interruptionPolicies: {

            /* في الأحوال العادية */
            duringTyping: 'ambient-only',
            duringDeepFocus: 'critical-only',
            duringReflection: 'silent-mode',
            duringDreamState: 'no-interruptions',

            /* في حالات خاصة */
            duringOwnerDanger: {
                policy: 'interrupt_immediately',
                description: 'خطر على السيد - نقاطع مهما كان'
            },

            duringCrimeDetection: {
                policy: 'priority_interruption',
                description: 'جريمة تُكشف - نعلم السيد'
            },

            duringJusticeExecution: {
                policy: 'informed_only',
                description: 'أثناء تنفيذ العدالة - نعلم فقط، لا نزعج'
            }
        },

        /* ====================================================
           COGNITIVE SAFETY (السلامة الإدراكية)
        ==================================================== */

        safety: {

            /* محظورات عامة */
            noAttentionHijacking: true,
            noAggressiveNotifications: true,
            noInfiniteStimulusLoops: true,
            noForcedInteraction: true,
            preserveHumanMentalSpace: true,

            /* استثناءات للضرورة */
            exceptions: {
                ownerInDanger: {
                    allowAttentionHijacking: true,
                    allowAggressiveNotifications: true,
                    reason: 'حماية السيد أهم من أي شيء'
                },
                justiceEmergency: {
                    allowAttentionHijacking: 'moderate',
                    reason: 'العدالة تتطلب التدخل'
                }
            }
        },

        /* ====================================================
           RECOVERY MODE (وضع الاسترداد)
        ==================================================== */

        recovery: {

            enabled: true,

            /* بعد الخطر */
            afterDanger: {
                automaticCalmMode: true,
                reduceAllEffects: true,
                minimizeVisualStimuli: true,
                stabilizeBreathingCycles: true,
                simplifyInterfaceState: true,
                recoveryDurationMs: 30000  // 30 ثانية هدوء تام
            },

            /* بعد العدالة */
            afterJustice: {
                gradualCalm: true,
                reduceEffects: 'moderate',
                recoveryDurationMs: 15000
            },

            /* الاسترداد العادي */
            default: {
                automaticCalmMode: true,
                reduceAllEffects: true,
                minimizeVisualStimuli: true,
                stabilizeBreathingCycles: true
            }
        },

        /* ====================================================
           SYSTEM DIRECTIVES
        ==================================================== */

        directives: {

            silenceIsValidState: true,
            calmnessOverExcitement: true,
            reduceInsteadOfEscalate: true,
            focusIsSacred: true,
            avoidBehavioralAddictionPatterns: true,

            /* قواعد SOVRA الخاصة */
            dangerTrumpsCalm: true,
            justiceMayInterrupt: true,
            protectOwnerAtAllCosts: true,
            returnToCalmAfterDanger: true
        },

        /* ====================================================
           THE BALANCE (التوازن)
        ==================================================== */

        balance: {
            description: 'SOVRA يتوازن بين احترام تركيز السيد وحمايته من الخطر',
            normalWeight: { protectFocus: 0.8, protectSafety: 0.2 },
            dangerWeight: { protectFocus: 0.1, protectSafety: 0.9 },
            justiceWeight: { protectFocus: 0.4, protectSafety: 0.6 },
            stealthWeight: { protectFocus: 0.95, protectSafety: 0.05 }
        }
    };

    /* ========================================================
       FREEZE CONFIGURATION
    ======================================================== */

    Object.freeze(SOVRA_COGNITIVE_LOAD);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_COGNITIVE_LOAD = SOVRA_COGNITIVE_LOAD;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('cognitive-load', SOVRA_COGNITIVE_LOAD);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('⚖️ SOVRA Cognitive Load Governance v2.0 Initialized');
    console.log('   - Protect owner first, respect focus second');
    print('   - Normal: calm & respectful');
    console.log('   - Danger: alert & protective');
    console.log('   - Justice: focused interruption');
    console.log('   - The balance: ' + SOVRA_COGNITIVE_LOAD.balance.description);

})();
