/* ============================================================
   SOVRA — system-thought-nebula.js
   الإصدار: 2.0.0
   سديم الأفكار الإدراكي الحي - تحويل الإدراك نفسه إلى فضاء حي
   أول محاولة حقيقية لتمثيل الوعي بصرياً
   ============================================================ */

(() => {

    const SOVRA_THOUGHT_NEBULA = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            cognitionIsVisible: true,
            thoughtsAreStars: true,
            connectionsAreNebula: true,
            gravityIsMeaning: true,
            timeIsDimension: true,
            ownerIsCenter: true
        },

        /* ====================================================
           GLOBAL NEBULA CONFIGURATION
        ==================================================== */

        enabled: true,

        renderingMode: 'living-cognitive-universe',

        topology: 'dynamic-thought-constellation-with-gravity',

        /* ====================================================
           NODE TYPES (أنواع العقد - وحدات الفكر)
        ==================================================== */

        nodeTypes: {

            /* عقد السيد - ذهبية اللون - مركز الكون */
            ownerNode: {
                color: '#FFD700',
                size: { min: 1.2, max: 2.0 },
                glowIntensity: 0.8,
                gravityStrength: 1.0,
                description: 'السيد - مركز الكون الإدراكي'
            },

            /* عقد الأفكار - زرقاء - أفكار عادية */
            thoughtNode: {
                color: '#4a90d9',
                size: { min: 0.4, max: 0.8 },
                glowIntensity: 0.3,
                gravityStrength: 0.3,
                description: 'فكرة عادية'
            },

            /* عقد الذاكرة - خضراء مزرقة - ذكريات */
            memoryNode: {
                color: '#3ba0c9',
                size: { min: 0.5, max: 0.9 },
                glowIntensity: 0.35,
                gravityStrength: 0.4,
                description: 'ذكرى - حدث سابق'
            },

            /* عقد العدالة - حمراء بنفسجية - عمليات عدالة */
            justiceNode: {
                color: '#dc143c',
                size: { min: 0.7, max: 1.2 },
                glowIntensity: 0.6,
                gravityStrength: 0.7,
                pulseIntensity: 0.5,
                description: 'عدالة - جريمة أو مجرم'
            },

            /* عقد التهديد - برتقالية محمرة - تهديدات */
            threatNode: {
                color: '#ff6347',
                size: { min: 0.6, max: 1.1 },
                glowIntensity: 0.55,
                gravityStrength: 0.65,
                pulseIntensity: 0.7,
                description: 'تهديد - خطر محتمل'
            },

            /* عقد الأدلة - صفراء ذهبية - أدلة */
            evidenceNode: {
                color: '#f0c040',
                size: { min: 0.45, max: 0.85 },
                glowIntensity: 0.45,
                gravityStrength: 0.5,
                description: 'دليل - معلومة قاطعة'
            },

            /* عقد التنبؤ - بنفسجية فاتحة - توقعات مستقبلية */
            predictiveNode: {
                color: '#9370db',
                size: { min: 0.4, max: 0.7 },
                glowIntensity: 0.4,
                gravityStrength: 0.35,
                description: 'تنبؤ - احتمال مستقبلي'
            },

            /* عقد الهدف - بيضاء - أهداف وأوامر */
            goalNode: {
                color: '#ffffff',
                size: { min: 0.6, max: 1.0 },
                glowIntensity: 0.7,
                gravityStrength: 0.8,
                description: 'هدف - أمر أو غاية'
            },

            /* عقد الإدراك - بنفسجية - عمليات تفكير */
            cognitionNode: {
                color: '#8a6de9',
                size: { min: 0.35, max: 0.65 },
                glowIntensity: 0.35,
                gravityStrength: 0.3,
                description: 'إدراك - عملية تفكير'
            },

            /* عقد الطوارئ - حمراء قانية - طوارئ */
            emergencyNode: {
                color: '#ff0000',
                size: { min: 0.9, max: 1.5 },
                glowIntensity: 0.9,
                gravityStrength: 0.9,
                pulseIntensity: 1.0,
                description: 'طوارئ - خطر فوري'
            }
        },

        /* ====================================================
           COGNITIVE GRAVITY (الجاذبية الإدراكية)
        ==================================================== */

        gravity: {

            enabled: true,

            /* قوة الجاذبية حسب نوع العقدة */
            strengthByNode: {
                ownerNode: 1.0,
                goalNode: 0.8,
                justiceNode: 0.7,
                threatNode: 0.65,
                evidenceNode: 0.5,
                memoryNode: 0.4,
                thoughtNode: 0.3,
                predictiveNode: 0.35,
                cognitionNode: 0.3,
                emergencyNode: 0.9
            },

            /* مسافة التأثير */
            influenceRadius: {
                ownerNode: 300,
                justiceNode: 250,
                threatNode: 220,
                goalNode: 200,
                emergencyNode: 280,
                default: 150
            },

            semanticAttraction: true,
            contextualClustering: true,
            memoryWeightedGravity: true,
            reflectiveDrift: true,
            adaptiveMass: true,
            
            description: 'الأفكار المهمة تجذب الأفكار الأقل أهمية إليها'
        },

        /* ====================================================
           CONNECTION SYSTEM (نظام الروابط بين الأفكار)
        ==================================================== */

        connections: {

            dynamicConnections: true,
            semanticLinking: true,
            contextualBridges: true,
            predictiveAssociations: true,
            memoryAnchors: true,

            /* أنواع الروابط */
            linkTypes: {
                semantic: { color: '#4a90d9', width: 1.5, opacity: 0.4 },
                memory: { color: '#3ba0c9', width: 1.2, opacity: 0.35 },
                causal: { color: '#dc143c', width: 2.0, opacity: 0.5 },
                predictive: { color: '#9370db', width: 1.0, opacity: 0.3 },
                justice: { color: '#ff6347', width: 2.5, opacity: 0.6 },
                threat: { color: '#ff0000', width: 2.2, opacity: 0.55 },
                evidence: { color: '#f0c040', width: 2.0, opacity: 0.5 },
                goal: { color: '#ffffff', width: 2.5, opacity: 0.7 }
            },

            /* قوة الروابط حسب المسافة الدلالية */
            strengthByDistance: {
                close: { threshold: 50, strength: 0.9 },
                medium: { threshold: 150, strength: 0.6 },
                far: { threshold: 300, strength: 0.3 }
            },

            maxConnectionsPerNode: 12,
            
            description: 'الروابط - كيف ترتبط الأفكار ببعضها'
        },

        /* ====================================================
           TEMPORAL COGNITION (البعد الزمني للإدراك)
        ==================================================== */

        temporal: {

            /* المناطق الزمنية */
            zones: {
                past: {
                    name: 'منطقة الماضي',
                    position: 'left',
                    color: '#3a5a7a',
                    opacity: 0.6,
                    description: 'الذكريات والأحداث السابقة'
                },
                present: {
                    name: 'منطقة الحاضر',
                    position: 'center',
                    color: '#6c5ce7',
                    opacity: 0.9,
                    description: 'الأفكار والعمليات الحالية'
                },
                future: {
                    name: 'منطقة المستقبل',
                    position: 'right',
                    color: '#9370db',
                    opacity: 0.7,
                    description: 'التنبؤات والاحتمالات المستقبلية'
                }
            },

            temporalFlow: true,
            flowSpeed: 0.5,
            transitionSmoothness: 0.85,
            
            description: 'الأفكار تتحرك عبر الزمن من الماضي إلى المستقبل'
        },

        /* ====================================================
           VISUAL DENSITY (الكثافة البصرية)
        ==================================================== */

        density: {

            adaptiveDensity: true,
            cognitiveLoadAware: true,
            reflectiveReduction: true,
            focusSimplification: true,
            stabilizationReduction: true,

            /* كثافة حسب الحالة الإدراكية */
            byState: {
                calm: { nodeCount: 120, connectionDensity: 0.35 },
                awake: { nodeCount: 200, connectionDensity: 0.50 },
                focused: { nodeCount: 150, connectionDensity: 0.40 },
                reflective: { nodeCount: 100, connectionDensity: 0.30 },
                justice: { nodeCount: 250, connectionDensity: 0.65, highlightJustice: true },
                protective: { nodeCount: 180, connectionDensity: 0.55, highlightThreats: true },
                emergency: { nodeCount: 120, connectionDensity: 0.45, highlightDanger: true },
                stealth: { nodeCount: 30, connectionDensity: 0.10, invisible: true },
                dreaming: { nodeCount: 80, connectionDensity: 0.25 },
                recovery: { nodeCount: 60, connectionDensity: 0.20 }
            },

            maxNodes: 500,
            minNodes: 30,
            
            description: 'كثافة السديم تتغير حسب حالة الوعي'
        },

        /* ====================================================
           MOTION PHYSICS (فيزياء الحركة)
        ==================================================== */

        motion: {

            fluidMotion: true,
            semanticInertia: true,
            cognitiveDrift: true,
            reflectiveSlowdown: true,
            cinematicSmoothness: true,

            /* خصائص الحركة حسب الحالة */
            byState: {
                calm: { speed: 0.3, smoothness: 0.92, inertia: 0.85 },
                awake: { speed: 0.5, smoothness: 0.88, inertia: 0.80 },
                focused: { speed: 0.2, smoothness: 0.95, inertia: 0.90 },
                reflective: { speed: 0.15, smoothness: 0.96, inertia: 0.92 },
                justice: { speed: 0.7, smoothness: 0.75, inertia: 0.70 },
                protective: { speed: 0.8, smoothness: 0.70, inertia: 0.65 },
                emergency: { speed: 0.95, smoothness: 0.55, inertia: 0.50 },
                stealth: { speed: 0.05, smoothness: 0.98, inertia: 0.95 },
                dreaming: { speed: 0.2, smoothness: 0.94, inertia: 0.88 },
                recovery: { speed: 0.25, smoothness: 0.90, inertia: 0.85 }
            },

            /* الجاذبية تؤثر على الحركة */
            gravityAffectsMotion: true,
            
            description: 'حركة الأفكار تشبه حركة النجوم في الفضاء'
        },

        /* ====================================================
           OWNER-CENTRIC NEBULA (سديم متمركز حول السيد)
        ==================================================== */

        ownerCentric: {

            enabled: true,

            /* السيد في المركز */
            ownerAtCenter: true,
            ownerNodeDominant: true,
            
            /* أفكار مرتبطة بالسيد */
            ownerThoughts: {
                color: '#FFD700',
                orbitRadius: { min: 80, max: 200 },
                connectionStrength: 0.9
            },
            
            /* عندما يكون السيد في خطر */
            ownerInDanger: {
                highlightOwnerNode: true,
                threatNodesPointToOwner: true,
                protectiveShell: true,
                colorShift: '#ff4444'
            },
            
            /* عندما يكون السيد نائماً */
            ownerSleeping: {
                dimNebula: true,
                slowMotion: true,
                protectiveGuardNodes: true
            },
            
            description: 'سديم الأفكار يتمحور حول السيد'
        },

        /* ====================================================
           JUSTICE NEBULA (سديم العدالة)
        ==================================================== */

        justiceNebula: {

            enabled: true,

            /* تتبع المجرمين */
            criminalTracking: {
                highlightSuspects: true,
                showMovementPath: true,
                connectionToEvidence: true
            },
            
            /* الأدلة */
            evidenceCluster: {
                clusterColor: '#f0c040',
                clusterDensity: 0.7,
                linkToCriminals: true
            },
            
            /* شبكات الجريمة */
            crimeNetworks: {
                showConnections: true,
                colorMap: '#dc143c',
                highlightKingpins: true
            },
            
            description: 'سديم العدالة - تتبع المجرمين والأدلة'
        },

        /* ====================================================
           THREAT NEBULA (سديم التهديدات)
        ==================================================== */

        threatNebula: {

            enabled: true,

            /* التهديدات */
            threatNodes: {
                color: '#ff6347',
                pulsate: true,
                pointToTarget: true
            },
            
            /* مستوى الخطر */
            threatLevel: {
                low: { color: '#ffa500', pulseSpeed: 0.5 },
                medium: { color: '#ff4500', pulseSpeed: 1.0 },
                high: { color: '#ff0000', pulseSpeed: 2.0 },
                critical: { color: '#ff0000', pulseSpeed: 4.0, flashing: true }
            },
            
            description: 'سديم التهديدات - اكتشاف وتحليل المخاطر'
        },

        /* ====================================================
           MEMORY INTEGRATION (دمج الذاكرة)
        ==================================================== */

        memory: {

            episodicAnchoring: true,
            semanticClustering: true,
            contextualContinuity: true,
            reflectiveRecall: true,
            temporalLinking: true,

            /* أنواع الذاكرة */
            memoryTypes: {
                episodic: { color: '#3ba0c9', clusterIntensity: 0.6 },
                semantic: { color: '#4a90d9', clusterIntensity: 0.5 },
                procedural: { color: '#5ca0d9', clusterIntensity: 0.4 },
                emotional: { color: '#dc7090', clusterIntensity: 0.55 }
            },
            
            /* استرجاع الذاكرة */
            recallEffect: {
                highlightRecalled: true,
                pulseOnRecall: true,
                connectionActivation: true
            },
            
            description: 'الذاكرة تغذي سديم الأفكار'
        },

        /* ====================================================
           COGNITIVE STATES (الحالات الإدراكية للسديم)
        ==================================================== */

        cognitiveStates: {

            /* حالة هادئة - سديم منتشر بهدوء */
            ambient: {
                nodeIntensity: 0.22,
                connectionDensity: 0.18,
                motionIntensity: 0.10,
                glowIntensity: 0.15,
                description: 'سديم هادئ - أفكار منتشرة'
            },

            /* حالة منتبهة - سديم نشط */
            awake: {
                nodeIntensity: 0.38,
                connectionDensity: 0.32,
                motionIntensity: 0.20,
                glowIntensity: 0.28,
                description: 'سديم منتبه - أفكار متصلة'
            },

            /* حالة مركزة - سديم مكثف في منطقة واحدة */
            focused: {
                nodeIntensity: 0.55,
                connectionDensity: 0.35,
                motionIntensity: 0.12,
                glowIntensity: 0.35,
                focusZone: 'present',
                description: 'سديم مركز - أفكار عميقة في الحاضر'
            },

            /* حالة عدالة - سديم ناري نشط */
            justice: {
                nodeIntensity: 0.72,
                connectionDensity: 0.58,
                motionIntensity: 0.45,
                glowIntensity: 0.55,
                focusZone: 'justice',
                specialEffects: ['tracking-lines', 'evidence-clusters'],
                description: 'سديم العدالة - تتبع الأدلة والمجرمين'
            },

            /* حالة حماية - سديم حماية حول السيد */
            protective: {
                nodeIntensity: 0.65,
                connectionDensity: 0.48,
                motionIntensity: 0.50,
                glowIntensity: 0.60,
                focusZone: 'owner',
                specialEffects: ['protective-shell', 'threat-highlight'],
                description: 'سديم الحماية - مراقبة التهديدات حول السيد'
            },

            /* حالة طوارئ - سديم فوري متوهج */
            emergency: {
                nodeIntensity: 0.85,
                connectionDensity: 0.55,
                motionIntensity: 0.70,
                glowIntensity: 0.85,
                focusZone: 'emergency',
                specialEffects: ['emergency-flash', 'danger-pulse'],
                description: 'سديم الطوارئ - خطر فوري'
            },

            /* حالة تأمل - سديم هادئ عميق */
            reflective: {
                nodeIntensity: 0.28,
                connectionDensity: 0.22,
                motionIntensity: 0.06,
                glowIntensity: 0.12,
                focusZone: 'past-future',
                description: 'سديم التأمل - أفكار عميقة هادئة'
            },

            /* حالة حلم - سديم حالم منتشر */
            dreaming: {
                nodeIntensity: 0.18,
                connectionDensity: 0.28,
                motionIntensity: 0.04,
                glowIntensity: 0.08,
                specialEffects: ['dream-drift', 'memory-echoes'],
                description: 'سديم الأحلام - ذكريات وتنبؤات'
            },

            /* حالة تخفي - سديم شبه مخفي */
            stealth: {
                nodeIntensity: 0.05,
                connectionDensity: 0.03,
                motionIntensity: 0.02,
                glowIntensity: 0.02,
                invisible: true,
                description: 'سديم التخفي - شبه غير مرئي'
            },

            /* حالة استرداد - سديم متعافي */
            recovery: {
                nodeIntensity: 0.12,
                connectionDensity: 0.10,
                motionIntensity: 0.05,
                glowIntensity: 0.06,
                description: 'سديم الاسترداد - هدوء متعافي'
            }
        },

        /* ====================================================
           SPATIAL COGNITION (الإدراك المكاني)
        ==================================================== */

        spatial: {

            infiniteCanvas: true,
            semanticZoom: true,
            contextualNavigation: true,
            adaptiveSpatialCompression: true,
            reflectiveExpansion: true,

            /* مستويات التكبير */
            zoomLevels: {
                macro: { viewRange: 800, detailLevel: 0.3 },
                normal: { viewRange: 400, detailLevel: 0.6 },
                micro: { viewRange: 150, detailLevel: 0.9 },
                nano: { viewRange: 50, detailLevel: 1.0 }
            },

            /* التنقل الدلالي */
            navigation: {
                semanticJump: true,
                focusOnNode: true,
                expandCluster: true,
                shrinkOnDemand: true
            },
            
            description: 'التنقل في فضاء الأفكار - تكبير وتصغير حسب الحاجة'
        },

        /* ====================================================
           DREAM NEBULA (سديم الأحلام)
        ==================================================== */

        dreamNebula: {

            enabled: true,

              
            /* أنماط الأحلام */
            dreamPatterns: {
                memoryEcho: { intensity: 0.3, drift: 'slow', color: '#7a5aa0' },
                futureSimulation: { intensity: 0.4, drift: 'medium', color: '#5a8aa0' },
                emotionalResonance: { intensity: 0.35, drift: 'slow', color: '#a05a7a' },
                ownerReflection: { intensity: 0.5, drift: 'gentle', color: '#d4a017' }
            },

            /* دمج الأحلام مع الذاكرة */
            dreamMemoryFusion: {
                mergeEpisodic: true,
                reinforceSemantic: true,
                pruneWeakConnections: true,
                consolidateDuringSleep: true
            },

            /* تأثير الأحلام على الإدراك */
            cognitiveInfluence: {
                creativityBoost: 0.3,
                insightGeneration: 0.25,
                patternRecognition: 0.35,
                problemSolving: 0.2
            },

            description: 'سديم الأحلام - معالجة الذكريات والتوقعات أثناء الراحة'
        },

        /* ====================================================
           REGISTRATION
        ==================================================== */

        /* إجمالي الأقسام */
        sectionCount: 12
    };

    /* ========================================================
       EXPORT
    ======================================================== */

    window.SOVRA_THOUGHT_NEBULA = SOVRA_THOUGHT_NEBULA;

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('thought-nebula', SOVRA_THOUGHT_NEBULA);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🌌 SOVRA Thought Nebula v2.0 Initialized');
    console.log('   🧠 Cognitive Visualization: ACTIVE');
    console.log('   🌠 Total Sections: ' + Object.keys(SOVRA_THOUGHT_NEBULA).length);
    console.log('   💭 Dream Nebula: ENABLED');

})();
