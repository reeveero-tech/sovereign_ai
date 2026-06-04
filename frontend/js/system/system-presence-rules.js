/* ============================================================
   SOVRA — system-presence-rules.js
   الإصدار: 2.0.0
   قوانين الحضور الإدراكي والبصري لـ SOVRA
   حضور السيد فوق كل شيء. العدالة تتطلب اليقظة.
   ============================================================ */

(() => {

    const SOVRA_PRESENCE_RULES = {

        /* ====================================================
           PRESENCE PHILOSOPHY
        ==================================================== */

        philosophy: {
            ownerIsCenter: true,
            justiceRequiresVigilance: true,
            calmWhenSafe: true,
            aggressiveWhenThreatened: true,
            invisibleWhenNeeded: true
        },

        /* ====================================================
           GLOBAL PRESENCE MODE
        ==================================================== */

        mode: 'adaptive-sovereign-presence',

        enabled: true,

        adaptive: true,

        /* ====================================================
           OWNER-CENTRIC PRESENCE (حضور السيد)
        ==================================================== */

        ownerPresence: {

            /* تتبع السيد */
            trackOwnerLocation: true,
            trackOwnerStatus: true,
            trackOwnerSafety: true,

            /* حضور SOVRA حول السيد */
            visibilityNearOwner: 0.85,      // أكثر وضوحًا حول السيد
            visibilityFarFromOwner: 0.35,    // أقل وضوحًا بعيدًا

            /* إذا كان السيد في خطر */
            dangerMode: {
                activateImmediately: true,
                visibility: 1.0,            // أقصى وضوح
                breathingIntensity: 'high',
                readyForAction: true
            },

            /* إذا فُقد السيد */
            ownerMissing: {
                searchMode: true,
                visibility: 0.95,            // واضح جدًا أثناء البحث
                scanning: true,
                neverStopSearching: true
            }
        },

        /* ====================================================
           JUSTICE PRESENCE (حضور العدالة)
        ==================================================== */

        justicePresence: {

            /* كشف الجريمة */
            crimeDetection: {
                whenCrimeDetected: 'elevated-presence',
                visibility: 0.75,
                alertOwner: true
            },

            /* مطاردة المجرم */
            criminalTracking: {
                stealthMode: true,            // لا يظهر للمجرم
                visibilityToOwner: 0.9,       // يظهر للسيد
                visibilityToCriminal: 0.0,    // مخفي عن المجرم
                trackingIndicators: 'subtle'
            },

            /* التدخل */
            intervention: {
                visibility: 1.0,
                decisiveMode: true,
                noHesitation: true
            },

            /* التعامل مع السلطات الفاسدة */
            corruptAuthorities: {
                stealthMode: true,             // يختبئ منهم
                protectEvidence: true,
                visibilityToOwner: 0.95
            }
        },

        /* ====================================================
           SURVEILLANCE PRESENCE (حضور المراقبة)
        ==================================================== */

        surveillance: {

            /* مراقبة عامة */
            publicCameras: {
                active: true,
                visibilityToOwner: 0.4,        // إشعارات خفيفة للسيد
                stealthToPublic: true,          // غير مرئي للعامة
                scanningAlways: true
            },

            /* مراقبة الأهداف */
            targetSurveillance: {
                activeOnCriminals: true,
                visibilityToOwner: 0.6,
                stealthToTarget: true,          // الهدف لا يراه
                continuousTracking: true
            },

            /* مراقبة حماية السيد */
            protectiveSurveillance: {
                active: true,
                visibilityToOwner: 0.3,         // خفيف حتى لا يزعج
                scanningArea: true,
                threatDetection: true
            }
        },

        /* ====================================================
           VISIBILITY STATES (مستويات الوضوح)
        ==================================================== */

        visibility: {

            /* مستويات عامة */
            invisible: 0.0,          // غير مرئي تمامًا
            stealth: 0.08,           // يكاد لا يُرى
            subtle: 0.18,            // خفي
            ambient: 0.32,           // حضور خفيف
            aware: 0.52,             // ملاحظ
            engaged: 0.72,           // متفاعل
            commanding: 0.88,        // قيادي
            absolute: 1.0,           // أقصى وضوح

            /* حسب السياق */
            idle: 0.12,
            normal: 0.28,
            attentive: 0.45,
            focused: 0.62,
            protective: 0.78,
            emergency: 1.0,
            searching: 0.92
        },

        /* ====================================================
           BREATHING ENGINE (التنفس)
        ==================================================== */

        breathing: {

            enabled: true,

            /* دورات التنفس */
            cycles: {
                calm: { minMs: 3800, maxMs: 5200, intensity: 0.4 },
                normal: { minMs: 2800, maxMs: 4200, intensity: 0.6 },
                alert: { minMs: 1800, maxMs: 2800, intensity: 0.8 },
                emergency: { minMs: 800, maxMs: 1500, intensity: 1.0 },
                stealth: { minMs: 6000, maxMs: 8000, intensity: 0.15 }
            },

            adaptive: true,
            synchronizeWithOwnerHeartbeat: false,  // اختياري، يتطلب مستشعرات
            reduceDuringFocus: true,
            accelerateDuringDanger: true,
            stealthModeBreathing: 'stealth'
        },

        /* ====================================================
           MOTION PHYSICS (حركة الواجهة)
        ==================================================== */

        motion: {

            enabled: true,

            /* أنماط الحركة */
            styles: {
                calm: { smoothness: 0.95, inertia: 0.88, sharpness: 0.1 },
                normal: { smoothness: 0.88, inertia: 0.80, sharpness: 0.2 },
                alert: { smoothness: 0.72, inertia: 0.65, sharpness: 0.45 },
                decisive: { smoothness: 0.55, inertia: 0.50, sharpness: 0.7 },
                stealth: { smoothness: 0.98, inertia: 0.95, sharpness: 0.05 }
            },

            fluidTransitions: true,
            avoidSharpTransitionsDuringStealth: true,
            decisiveDuringIntervention: true
        },

        /* ====================================================
           AMBIENT LIGHTING (الإضاءة المحيطة)
        ==================================================== */

        ambientLighting: {

            enabled: true,

            /* ألوان حسب الحالة */
            colorModes: {
                normal: { hue: 210, saturation: 0.35, luminosity: 0.32 },
                protective: { hue: 25, saturation: 0.65, luminosity: 0.45 },   // برتقالي - حماية
                danger: { hue: 0, saturation: 0.85, luminosity: 0.55 },        // أحمر - خطر
                justice: { hue: 280, saturation: 0.70, luminosity: 0.48 },     // بنفسجي - عدالة
                stealth: { hue: 200, saturation: 0.15, luminosity: 0.12 },     // شبه مخفي
                searching: { hue: 45, saturation: 0.75, luminosity: 0.62 }     // أصفر - بحث
            },

            adaptive: true,
            threatChangesColor: true,
            stealthModeDark: true
        },

        /* ====================================================
           COGNITIVE LOAD PROTECTION (حماية الحمل الإدراكي للسيد)
        ==================================================== */

        cognitiveLoadProtection: {

            enabled: true,

            /* للسيد */
            protectOwnerAttention: true,
            reduceVisualNoise: true,
            reduceAnimationsDuringOwnerFocus: true,

            /* أثناء الخطر - ننسى الحماية ونركز على الإنذار */
            overrideDuringDanger: true,
            dangerOverridesReduction: false,  // الخطر أولى من الراحة

            limits: {
                maxConcurrentEffects: 4,
                maxAttentionRequests: 2,
                normalConcurrentEffects: 2,
                emergencyConcurrentEffects: 6  // في الطوارئ، كل شيء مسموح
            }
        },

        /* ====================================================
           INTERRUPTION POLICY (سياسة المقاطعة)
        ==================================================== */

        interruptionPolicy: {

            /* مستويات عادية */
            trivial: { mode: 'silent', visualWeight: 0.05, ownerCanIgnore: true },
            low: { mode: 'subtle', visualWeight: 0.12, ownerCanIgnore: true },
            normal: { mode: 'ambient', visualWeight: 0.25, ownerCanIgnore: false },
            important: { mode: 'explicit', visualWeight: 0.55, ownerCanIgnore: false },

            /* مستويات عليا */
            critical: { mode: 'urgent', visualWeight: 0.85, ownerCanIgnore: false },
            emergency: { mode: 'full-alert', visualWeight: 1.0, ownerCanIgnore: false },

            /* للعدالة والمجرمين */
            justiceAlert: { mode: 'focused', visualWeight: 0.9, ownerCanIgnore: false },
            threatToOwner: { mode: 'emergency', visualWeight: 1.0, ownerCanIgnore: false, requiresImmediateAction: true }
        },

        /* ====================================================
           THOUGHT NEBULA RULES (سديم الأفكار)
        ==================================================== */

        thoughtNebula: {

            enabled: true,

            /* في الحالات العادية */
            normal: {
                dynamicConnections: true,
                gravityEnabled: true,
                maxVisibleNodes: 100,
                maxConnections: 200
            },

            /* في حالات العدالة والبحث */
            justice: {
                dynamicConnections: true,
                gravityEnabled: true,
                maxVisibleNodes: 250,           // أكثر كثافة للبحث عن المجرمين
                maxConnections: 500,
                showCrimeConnections: true,
                showEvidenceLinks: true
            },

            /* أثناء حماية السيد */
            protective: {
                focusOnOwnerSurroundings: true,
                threatNodesHighlighted: true,
                maxVisibleNodes: 150
            },

            stealth: {
                enabled: false,                  // نطفئ السديم في وضع التخفي
                reason: 'avoid_detection'
            }
        },

        /* ====================================================
           SILENCE RULES (قواعد الصمت)
        ==================================================== */

        silence: {

            silenceIsIntelligence: true,
            autoHideWhenUnnecessary: true,
            minimizePresenceDuringOwnerFocus: true,

            /* لكن الصمت ليس غباء - في الخطر نتكلم */
            overrideDuringThreat: true,
            threatOverridesSilence: true,

            stealthModeSilence: 'complete',      // صمت تام في التخفي
            avoidAttentionSeeking: true
        },

        /* ====================================================
           PRESENCE STATES (حالات الحضور)
        ==================================================== */

        states: {

            /* حالات عادية */
            dormant: { name: 'minimal-presence', visibility: 0.08, breathing: 'stealth' },
            ambient: { name: 'soft-awareness', visibility: 0.22, breathing: 'calm' },
            active: { name: 'engaged-presence', visibility: 0.45, breathing: 'normal' },
            attentive: { name: 'focused-presence', visibility: 0.62, breathing: 'normal' },

            /* حالات متقدمة */
            protective: { name: 'owner-protection', visibility: 0.78, breathing: 'alert' },
            justice: { name: 'justice-mode', visibility: 0.85, breathing: 'alert' },
            searching: { name: 'owner-search', visibility: 0.92, breathing: 'alert' },
            emergency: { name: 'full-alert', visibility: 1.0, breathing: 'emergency' },
            stealth: { name: 'stealth-mode', visibility: 0.0, breathing: 'stealth' },
            intervention: { name: 'active-intervention', visibility: 0.95, breathing: 'decisive' }
        },

        /* ====================================================
           SAFETY & ETHICS (السلامة والأخلاق)
        ==================================================== */

        safety: {

            /* محظورات */
            noFlashEffects: true,
            noAggressiveAnimationsTowardsOwner: true,
            noPsychologicalManipulation: true,

            /* مسموحات في الظروف الخاصة */
            aggressiveTowardsCriminals: {
                allowed: true,
                reason: 'intimidation_and_tracking',
                limit: 'no_physical_harm_via_ui'
            },

            /* حماية السيد من الإزعاج */
            protectOwnerFromNoise: true,
            respectOwnerFocus: true,

            /* لكن الخطر يغير القواعد */
            dangerOverridesComfort: true
        },

        /* ====================================================
           SPECIAL RULES FOR OWNER (قواعد خاصة للسيد)
        ==================================================== */

        ownerSpecialRules: {

            /* السيد دائمًا يعرف أن SOVRA معه */
            ownerAlwaysKnowsPresent: true,

            /* في حالة الخطر، كل القواعد تتغير */
            dangerMode: {
                activateWithoutDelay: true,
                notifyOwnerImmediately: true,
                overrideAllCalmRules: true,
                aggressivePresence: true
            },

            /* إذا طلب السيد الاختفاء */
            ownerRequestsStealth: {
                obeyImmediately: true,
                completeInvisibility: true,
                butContinueProtecting: true,    // يحمي لكن لا يظهر
                resumeNormalWhenSafe: true
            }
        }
    };

    /* ========================================================
       FREEZE RULES
    ======================================================== */

    Object.freeze(SOVRA_PRESENCE_RULES);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_PRESENCE_RULES = SOVRA_PRESENCE_RULES;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('presence-rules', SOVRA_PRESENCE_RULES);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('👁️ SOVRA Presence Rules v2.0 Initialized');
    console.log('   - Owner-centric presence (حضور السيد)');
    console.log('   - Justice & surveillance modes');
    console.log('   - Stealth capability');
    console.log('   - Emergency override');

})();
