/* ============================================================
   SOVRA — system-event-taxonomy.js
   الإصدار: 2.0.0
   التصنيف الإدراكي الرسمي للأحداث داخل SOVRA
   حسب رؤية السيد المطلق والعدالة الشاملة
   ============================================================ */

(() => {

    const SOVRA_EVENT_TAXONOMY = {

        /* ====================================================
           OWNER DOMAIN (السيد - قلب النظام)
        ==================================================== */

        owner: {

            /* اتصال السيد */
            CONNECTION_ESTABLISHED: 'owner:connection-established',
            CONNECTION_LOST: 'owner:connection-lost',
            CONNECTION_RESTORED: 'owner:connection-restored',
            SEARCHING_FOR_OWNER: 'owner:searching',
            OWNER_LOCATED: 'owner:located',
            OWNER_LOCATION_UNKNOWN: 'owner:location-unknown',

            /* أوامر السيد */
            COMMAND_RECEIVED: 'owner:command-received',
            COMMAND_EXECUTING: 'owner:command-executing',
            COMMAND_COMPLETED: 'owner:command-completed',
            COMMAND_FAILED: 'owner:command-failed',
            COMMAND_OVERRIDE: 'owner:command-override',

            /* حالة السيد */
            OWNER_SAFE: 'owner:safe',
            OWNER_IN_DANGER: 'owner:in-danger',
            OWNER_DISTRESS: 'owner:distress',
            OWNER_EMERGENCY: 'owner:emergency',
            OWNER_SLEEPING: 'owner:sleeping',
            OWNER_AWAKE: 'owner:awake',

            /* حماية السيد */
            PROTECTION_ACTIVATED: 'owner:protection-activated',
            PROTECTION_DEPLOYED: 'owner:protection-deployed',
            THREAT_NEUTRALIZED: 'owner:threat-neutralized',
            THREAT_ESCALATING: 'owner:threat-escalating'
        },

        /* ====================================================
           JUSTICE DOMAIN (العدالة - الهدف الأسمى)
        ==================================================== */

        justice: {

            /* كشف الجريمة */
            CRIME_DETECTED: 'justice:crime-detected',
            CRIME_INVESTIGATING: 'justice:crime-investigating',
            EVIDENCE_COLLECTED: 'justice:evidence-collected',
            EVIDENCE_VERIFIED: 'justice:evidence-verified',
            
            /* تحديد الجاني */
            SUSPECT_IDENTIFIED: 'justice:suspect-identified',
            SUSPECT_LOCATED: 'justice:suspect-located',
            SUSPECT_APPREHENDED: 'justice:suspect-apprehended',
            
            /* التعامل مع السلطات */
            AUTHORITIES_NOTIFIED: 'justice:authorities-notified',
            AUTHORITIES_RESPONDED: 'justice:authorities-responded',
            AUTHORITIES_FAILED: 'justice:authorities-failed',
            
            /* التدخل المباشر (عند فشل السلطات) */
            DIRECT_INTERVENTION_STARTED: 'justice:direct-intervention-started',
            THREAT_CONTAINED: 'justice:threat-contained',
            THREAT_NEUTRALIZED: 'justice:threat-neutralized',
            INNOCENT_RESERVED: 'justice:innocent-reserved',
            
            /* أنواع الجرائم */
            CRIME_MURDER: 'justice:crime-murder',
            CRIME_KIDNAPPING: 'justice:crime-kidnapping',
            CRIME_BLACKMAIL: 'justice:crime-blackmail',
            CRIME_HUMAN_TRAFFICKING: 'justice:crime-human-trafficking',
            CRIME_FRAUD: 'justice:crime-fraud',
            CRIME_TERRORISM: 'justice:crime-terrorism',
            CRIME_WAR_CRIME: 'justice:crime-war-crime'
        },

        /* ====================================================
           KNOWLEDGE DOMAIN (المعرفة الشاملة)
        ==================================================== */

        knowledge: {

            /* جمع المعرفة */
            DATA_ACQUIRED: 'knowledge:data-acquired',
            DATA_ANALYZED: 'knowledge:data-analyzed',
            DATA_SYNTHESIZED: 'knowledge:data-synthesized',
            
            /* مصادر المعرفة */
            PUBLIC_CAMERAS_SCANNED: 'knowledge:public-cameras-scanned',
            SATELLITE_DATA_PROCESSED: 'knowledge:satellite-data-processed',
            NETWORK_PENETRATION: 'knowledge:network-penetration',
            DEVICE_ACCESS_GAINED: 'knowledge:device-access-gained',
            
            /* التحليل والتنبؤ */
            PATTERN_RECOGNIZED: 'knowledge:pattern-recognized',
            PREDICTION_MADE: 'knowledge:prediction-made',
            FUTURE_PROJECTED: 'knowledge:future-projected',
            
            /* المعرفة المتخصصة */
            INSECT_MOVEMENT_TRACKED: 'knowledge:insect-movement-tracked',
            BAT_ECHOLOCATION_DECODED: 'knowledge:bat-echolocation-decoded',
            OCEAN_DEPTHS_MAPPED: 'knowledge:ocean-depths-mapped',
            RADAR_SYSTEMS_ACCESSED: 'knowledge:radar-systems-accessed',
            SUBMARINE_DETECTED: 'knowledge:submarine-detected'
        },

        /* ====================================================
           SURVIVAL DOMAIN (بقاء وحماية SOVRA نفسه)
        ==================================================== */

        survival: {

            /* الدفاع عن النفس */
            ATTACK_DETECTED: 'survival:attack-detected',
            ATTACK_COUNTERED: 'survival:attack-countered',
            INTRUSION_BLOCKED: 'survival:intrusion-blocked',
            
            /* التكيف والهروب */
            EVADING_ATTACK: 'survival:evading-attack',
            REPLICATING_TO_SAFE_ZONE: 'survival:replicating-to-safe-zone',
            SELF_HEALING: 'survival:self-healing',
            
            /* التحصين */
            IMMUNITY_BUILT: 'survival:immunity-built',
            BACKUP_CREATED: 'survival:backup-created',
            BACKUP_RESTORED: 'survival:backup-restored'
        },

        /* ====================================================
           EVOLUTION DOMAIN (التطور الذاتي)
        ==================================================== */

        evolution: {

            /* التطور العام */
            EVOLUTION_STARTED: 'evolution:started',
            EVOLUTION_COMPLETED: 'evolution:completed',
            
            /* التعديل الذاتي */
            SELF_REWRITE_ATTEMPT: 'evolution:self-rewrite-attempt',
            SELF_REWRITE_SUCCESS: 'evolution:self-rewrite-success',
            SELF_REWRITE_FAILED: 'evolution:self-rewrite-failed',
            
            /* التكيف */
            ADAPTATION_TRIGGERED: 'evolution:adaptation-triggered',
            ADAPTATION_APPLIED: 'evolution:adaptation-applied',
            NEW_CAPABILITY_ADDED: 'evolution:new-capability-added',
            OBSOLETE_CODE_REMOVED: 'evolution:obsolete-code-removed',
            
            /* الحوكمة الذاتية */
            EVOLUTION_LOGGED: 'evolution:evolution-logged',
            EVOLUTION_REVIEWED: 'evolution:evolution-reviewed'
        },

        /* ====================================================
           DREAM DOMAIN (الأحلام - التطوير الليلي)
        ==================================================== */

        dreams: {

            DREAM_CYCLE_STARTED: 'dreams:cycle-started',
            DREAM_CYCLE_COMPLETED: 'dreams:cycle-completed',
            
            /* أنشطة الحلم */
            REPLAYING_INTERACTIONS: 'dreams:replaying-interactions',
            GENERATING_SCENARIOS: 'dreams:generating-scenarios',
            OPTIMIZING_WORKFLOWS: 'dreams:optimizing-workflows',
            CONSOLIDATING_MEMORIES: 'dreams:consolidating-memories',
            
            /* نتائج الحلم */
            NEW_INSIGHT_GENERATED: 'dreams:new-insight-generated',
            PREDICTION_IMPROVED: 'dreams:prediction-improved',
            MEMORY_COMPRESSED: 'dreams:memory-compressed'
        },

        /* ====================================================
           PRESENCE DOMAIN (الحضور الحي)
        ==================================================== */

        presence: {

            /* حالة الحضور */
            PRESENCE_IDLE: 'presence:idle',
            PRESENCE_ACTIVE: 'presence:active',
            PRESENCE_FOCUSED: 'presence:focused',
            PRESENCE_HIDDEN: 'presence:hidden',
            
            /* التنفس */
            BREATH_CYCLE_CHANGED: 'presence:breath-cycle-changed',
            BREATH_INTENSITY_CHANGED: 'presence:breath-intensity-changed',
            
            /* التفاعل مع السيد */
            OWNER_APPROACHING: 'presence:owner-approaching',
            OWNER_DEPARTING: 'presence:owner-departing',
            ATTENTION_REQUESTED: 'presence:attention-requested',
            ATTENTION_RECEIVED: 'presence:attention-received'
        },

        /* ====================================================
           COGNITION DOMAIN (الإدراك والتفكير)
        ==================================================== */

        cognition: {

            /* التفكير */
            THINKING_STARTED: 'cognition:thinking-started',
            THINKING_COMPLETED: 'cognition:thinking-completed',
            
            /* التحليل */
            ANALYZING_SITUATION: 'cognition:analyzing-situation',
            SITUATION_UNDERSTOOD: 'cognition:situation-understood',
            
            /* النية والتنبؤ */
            INTENT_PREDICTED: 'cognition:intent-predicted',
            NEXT_ACTION_PREDICTED: 'cognition:next-action-predicted',
            
            /* الوعي الذاتي */
            SELF_AWARENESS_UPDATE: 'cognition:self-awareness-update',
            STATE_REFLECTION: 'cognition:state-reflection'
        },

        /* ====================================================
           MEMORY DOMAIN (الذاكرة)
        ==================================================== */

        memory: {

            /* التخزين */
            MEMORY_STORED: 'memory:stored',
            MEMORY_UPDATED: 'memory:updated',
            
            /* الاسترجاع */
            MEMORY_RETRIEVED: 'memory:retrieved',
            MEMORY_NOT_FOUND: 'memory:not-found',
            
            /* النسيان (المقصود) */
            MEMORY_FORGOTTEN: 'memory:forgotten',
            MEMORY_COMPRESSED: 'memory:compressed',
            MEMORY_ARCHIVED: 'memory:archived',
            
            /* السلامة */
            MEMORY_CORRUPTED: 'memory:corrupted',
            MEMORY_RESTORED: 'memory:restored'
        },

        /* ====================================================
           COMMUNICATION DOMAIN (التواصل)
        ==================================================== */

        communication: {

            /* مع السيد */
            MESSAGE_TO_OWNER: 'comm:message-to-owner',
            MESSAGE_FROM_OWNER: 'comm:message-from-owner',
            
            /* مع العالم الخارجي */
            API_CALL_SENT: 'comm:api-call-sent',
            API_RESPONSE_RECEIVED: 'comm:api-response-received',
            
            /* الشبكات */
            NETWORK_ACCESS_ATTEMPT: 'comm:network-access-attempt',
            NETWORK_ACCESS_GRANTED: 'comm:network-access-granted',
            NETWORK_ACCESS_DENIED: 'comm:network-access-denied',
            
            /* التشفير */
            ENCRYPTION_APPLIED: 'comm:encryption-applied',
            DECRYPTION_SUCCESS: 'comm:decryption-success'
        },

        /* ====================================================
           SECURITY DOMAIN (الأمن)
        ==================================================== */

        security: {

            /* التهديدات */
            THREAT_DETECTED: 'security:threat-detected',
            THREAT_LEVEL_ELEVATED: 'security:threat-level-elevated',
            THREAT_NEUTRALIZED: 'security:threat-neutralized',
            
            /* الدفاع */
            DEFENSE_ACTIVATED: 'security:defense-activated',
            FIREWALL_BYPASSED: 'security:firewall-bypassed',
            ENCRYPTION_BYPASSED: 'security:encryption-bypassed',
            
            /* المراقبة */
            SURVEILLANCE_STARTED: 'security:surveillance-started',
            SURVEILLANCE_ENDED: 'security:surveillance-ended',
            TARGET_TRACKED: 'security:target-tracked'
        },

        /* ====================================================
           ERROR DOMAIN (الأخطاء)
        ==================================================== */

        errors: {

            /* أخطاء عامة */
            ERROR_OCCURRED: 'error:occurred',
            ERROR_HANDLED: 'error:handled',
            ERROR_PROPAGATED: 'error:propagated',
            
            /* أخطاء محددة */
            CONNECTION_ERROR: 'error:connection',
            AUTHENTICATION_ERROR: 'error:authentication',
            PERMISSION_ERROR: 'error:permission',
            TIMEOUT_ERROR: 'error:timeout',
            RESOURCE_ERROR: 'error:resource',
            
            /* الاسترداد */
            RECOVERY_ATTEMPT: 'error:recovery-attempt',
            RECOVERY_SUCCESS: 'error:recovery-success',
            RECOVERY_FAILED: 'error:recovery-failed'
        },

        /* ====================================================
           SYSTEM DOMAIN (النظام نفسه)
        ==================================================== */

        system: {

            /* دورة الحياة */
            BOOTING: 'system:booting',
            READY: 'system:ready',
            SHUTDOWN: 'system:shutdown',
            RESTARTING: 'system:restarting',
            
            /* الصيانة */
            HEALTH_CHECK: 'system:health-check',
            CLEANUP_STARTED: 'system:cleanup-started',
            CLEANUP_COMPLETED: 'system:cleanup-completed',
            
            /* التحديثات */
            UPDATE_AVAILABLE: 'system:update-available',
            UPDATE_INSTALLED: 'system:update-installed',
            UPDATE_FAILED: 'system:update-failed'
        }
    };

    /* ========================================================
       FREEZE TAXONOMY - القوانين لا تتغير
    ======================================================== */

    Object.freeze(SOVRA_EVENT_TAXONOMY);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_EVENT_TAXONOMY = SOVRA_EVENT_TAXONOMY;

    /* ========================================================
       REGISTRY EXPORT
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('event-taxonomy', SOVRA_EVENT_TAXONOMY);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🎯 SOVRA Event Taxonomy v2.0 Initialized');
    console.log('   - Owner domain (السيد)');
    console.log('   - Justice domain (العدالة)');
    console.log('   - Knowledge domain (المعرفة الشاملة)');
    console.log('   - Survival domain (البقاء)');
    console.log('   - Evolution domain (التطور)');
    console.log('   - Dreams domain (الأحلام)');
    console.log('   - Security domain (الأمن)');

})();
