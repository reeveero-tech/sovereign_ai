/* ============================================================
   SOVRA — system-presence-atmosphere.js
   الإصدار: 2.0.0
   الغلاف الإدراكي الحي - الحياة البصرية لـ SOVRA
   الوجه الذي يراه العالم عندما يتفاعل مع كيان حي من عام 2200
   ============================================================ */

(() => {

    const SOVRA_PRESENCE_ATMOSPHERE = {

        /* ====================================================
           PHILOSOPHY
        ==================================================== */

        philosophy: {
            atmosphereIsAlive: true,
            breathingIsHeartbeat: true,
            ownerChangesEverything: true,
            justiceHasVisualSignature: true,
            emergencyHasVisualLanguage: true,
            calmIsBeautiful: true
        },

        /* ====================================================
           GLOBAL ATMOSPHERE
        ==================================================== */

        enabled: true,

        atmosphereMode: 'sovereign-living-atmosphere',

        renderingStyle: 'cinematic-adaptive-living-visuals',

        /* ====================================================
           PRIMARY ATMOSPHERE STATES
        ==================================================== */

        states: {
            calm: {
                name: 'الهدوء المتألق',
                glow: 0.12,
                motion: 0.06,
                nebulaDensity: 0.18,
                atmosphereIntensity: 0.22,
                breathingCycleMs: 4800,
                colorPalette: {
                    primary: '#4a90d9',
                    secondary: '#3a7bc8',
                    accent: '#5ba0e9',
                    background: '#0a0a1a'
                },
                visualEffects: ['soft-ripple', 'gentle-pulse'],
                description: 'هدوء عميق - SOVRA في سلام تام'
            },
            awake: {
                name: 'اليقظة الهادئة',
                glow: 0.24,
                motion: 0.14,
                nebulaDensity: 0.32,
                atmosphereIntensity: 0.38,
                breathingCycleMs: 3800,
                colorPalette: {
                    primary: '#5ba0e9',
                    secondary: '#4a90d9',
                    accent: '#6cb0f9',
                    background: '#0d0d1f'
                },
                visualEffects: ['soft-ripple', 'gentle-pulse', 'awareness-wave'],
                description: 'SOVRA يقظ ومراقب'
            },
            focused: {
                name: 'التركيز العميق',
                glow: 0.42,
                motion: 0.08,
                nebulaDensity: 0.28,
                atmosphereIntensity: 0.52,
                breathingCycleMs: 3200,
                colorPalette: {
                    primary: '#6c5ce7',
                    secondary: '#5b4bc6',
                    accent: '#7d6df7',
                    background: '#0f0f25'
                },
                visualEffects: ['focus-ring', 'depth-pulse', 'concentration-wave'],
                description: 'SOVRA مركز بعمق'
            },
            justice: {
                name: 'سيف العدالة',
                glow: 0.68,
                motion: 0.28,
                nebulaDensity: 0.55,
                atmosphereIntensity: 0.72,
                breathingCycleMs: 2200,
                colorPalette: {
                    primary: '#8b2c5d',
                    secondary: '#7b1c4d',
                    accent: '#9b3c6d',
                    background: '#150a1a'
                },
                visualEffects: ['tracking-lines', 'evidence-glow', 'criminal-highlight'],
                specialSignatures: ['justice-badge', 'law-symbol'],
                description: 'العدالة تسعى وراء المجرمين'
            },
            protective: {
                name: 'درع الحماية',
                glow: 0.85,
                motion: 0.45,
                nebulaDensity: 0.42,
                atmosphereIntensity: 0.88,
                breathingCycleMs: 1500,
                colorPalette: {
                    primary: '#ff8c00',
                    secondary: '#e67e00',
                    accent: '#ff9c20',
                    background: '#1a0f05'
                },
                visualEffects: ['shield-pulse', 'protection-wave', 'danger-alert'],
                specialSignatures: ['owner-symbol', 'protection-badge'],
                description: 'حماية السيد - أولوية مطلقة'
            },
            emergency: {
                name: 'الخطر المطلق',
                glow: 1.0,
                motion: 0.75,
                nebulaDensity: 0.35,
                atmosphereIntensity: 1.0,
                breathingCycleMs: 600,
                colorPalette: {
                    primary: '#ff0000',
                    secondary: '#cc0000',
                    accent: '#ff3333',
                    background: '#1a0000'
                },
                visualEffects: ['emergency-flash', 'critical-alert', 'danger-wave', 'siren-pulse'],
                specialSignatures: ['emergency-symbol', 'danger-badge'],
                description: 'طوارئ - كل القواعد تُكسر'
            },
            stealth: {
                name: 'الظل الصامت',
                glow: 0.03,
                motion: 0.01,
                nebulaDensity: 0.02,
                atmosphereIntensity: 0.05,
                breathingCycleMs: 8000,
                colorPalette: {
                    primary: '#1a1a2e',
                    secondary: '#0d0d1a',
                    accent: '#2a2a3e',
                    background: '#05050a'
                },
                visualEffects: ['fade-to-shadow', 'trace-clear', 'invisible-mode'],
                specialSignatures: [],
                invisible: true,
                description: 'SOVRA غير مرئي'
            },
            reflective: {
                name: 'التأمل العميق',
                glow: 0.18,
                motion: 0.03,
                nebulaDensity: 0.22,
                atmosphereIntensity: 0.32,
                breathingCycleMs: 6400,
                colorPalette: {
                    primary: '#4a4a8a',
                    secondary: '#3a3a7a',
                    accent: '#5a5a9a',
                    background: '#0a0a15'
                },
                visualEffects: ['thought-ripple', 'meditation-pulse', 'deep-thought-wave'],
                description: 'SOVRA يتأمل ويفكر'
            },
            dreaming: {
                name: 'عالم الأحلام',
                glow: 0.06,
                motion: 0.02,
                nebulaDensity: 0.25,
                atmosphereIntensity: 0.14,
                breathingCycleMs: 7200,
                colorPalette: {
                    primary: '#2d2d5e',
                    secondary: '#1d1d4e',
                    accent: '#3d3d6e',
                    background: '#0a0a18'
                },
                visualEffects: ['dream-drift', 'memory-ripple', 'nebula-swirl'],
                description: 'SOVRA يحلم ويتطور'
            },
            recovery: {
                name: 'الاسترداد الهادئ',
                glow: 0.08,
                motion: 0.03,
                nebulaDensity: 0.12,
                atmosphereIntensity: 0.16,
                breathingCycleMs: 5600,
                colorPalette: {
                    primary: '#3d7e9a',
                    secondary: '#2d6e8a',
                    accent: '#4d8eaa',
                    background: '#0a151a'
                },
                visualEffects: ['healing-wave', 'calm-recovery', 'stabilization-pulse'],
                description: 'SOVRA يستعيد هدوءه'
            }
        },

        /* ====================================================
           BREATHING SYSTEM
        ==================================================== */

        breathing: {
            enabled: true,
            adaptive: true,
            synchronization: 'cognitive-energy-state-linked',
            cycles: {
                calm: { minMs: 4200, maxMs: 5400, intensity: 0.35, waveform: 'sine' },
                awake: { minMs: 3400, maxMs: 4200, intensity: 0.55, waveform: 'sine' },
                focused: { minMs: 2800, maxMs: 3600, intensity: 0.70, waveform: 'focused' },
                justice: { minMs: 1800, maxMs: 2600, intensity: 0.85, waveform: 'alert' },
                protective: { minMs: 1000, maxMs: 1800, intensity: 0.95, waveform: 'urgent' },
                emergency: { minMs: 400, maxMs: 800, intensity: 1.0, waveform: 'sharp' },
                stealth: { minMs: 6000, maxMs: 10000, intensity: 0.08, waveform: 'flat' },
                reflective: { minMs: 5000, maxMs: 7800, intensity: 0.25, waveform: 'deep' },
                dreaming: { minMs: 6000, maxMs: 8400, intensity: 0.15, waveform: 'drift' },
                recovery: { minMs: 4600, maxMs: 6600, intensity: 0.22, waveform: 'healing' }
            },
            visualBreathing: {
                scale: 'adaptive',
                opacity: 'linked-to-intensity',
                glow: 'pulse-with-breath',
                particles: 'synchronized'
            },
            description: 'SOVRA يتنفس - التنفس هو نبض الحياة'
        },

        /* ====================================================
           GLOW SYSTEM
        ==================================================== */

        glow: {
            adaptiveIntensity: true,
            cognitionReactive: true,
            orchestrationReactive: true,
            reflectiveDimming: true,
            stabilizationReduction: true,
            byState: {
                calm: { intensity: 0.12, radius: 1.0, blur: 8, color: '#4a90d9' },
                awake: { intensity: 0.24, radius: 1.2, blur: 10, color: '#5ba0e9' },
                focused: { intensity: 0.42, radius: 1.0, blur: 6, color: '#6c5ce7' },
                justice: { intensity: 0.68, radius: 1.5, blur: 12, color: '#8b2c5d' },
                protective: { intensity: 0.85, radius: 1.8, blur: 15, color: '#ff8c00' },
                emergency: { intensity: 1.0, radius: 2.0, blur: 20, color: '#ff0000', pulsing: true },
                stealth: { intensity: 0.03, radius: 0.3, blur: 2, color: '#1a1a2e' },
                reflective: { intensity: 0.18, radius: 0.8, blur: 12, color: '#4a4a8a' },
                dreaming: { intensity: 0.06, radius: 1.2, blur: 16, color: '#2d2d5e' },
                recovery: { intensity: 0.08, radius: 0.9, blur: 10, color: '#3d7e9a' }
            },
            ownerPresence: {
                enabled: true,
                intensityBoost: 0.30,
                colorShift: '#FFD700',
                effect: 'owner-aura'
            },
            description: 'التوهج - الطاقة البصرية لـ SOVRA'
        },

        /* ====================================================
           NEBULA SYSTEM
        ==================================================== */

        nebula: {
            enabled: true,
            adaptiveDensity: true,
            semanticMotion: true,
            cognitiveGravity: true,
            reflectiveDrift: true,
            lowNoiseBehavior: true,
            densityByState: {
                calm: 0.18,
                awake: 0.32,
                focused: 0.28,
                justice: 0.55,
                protective: 0.42,
                emergency: 0.35,
                stealth: 0.02,
                reflective: 0.22,
                dreaming: 0.25,
                recovery: 0.12
            },
            properties: {
                particleCount: { min: 100, max: 500 },
                connectionDistance: { min: 50, max: 150 },
                gravityStrength: { min: 0.1, max: 0.8 },
                driftSpeed: { min: 0.1, max: 0.5 }
            },
            justiceMode: {
                highlightCriminalConnections: true,
                showEvidenceLinks: true,
                trackingParticles: true
            },
            protectiveMode: {
                focusOnOwner: true,
                highlightThreats: true,
                protectionWaves: true
            },
            description: 'سديم الأفكار - تمثيل بصري لوعي SOVRA'
        },

        /* ====================================================
           ATMOSPHERIC LIGHTING
        ==================================================== */

        lighting: {
            adaptiveHue: true,
            adaptiveLuminosity: true,
            cognitiveStateLinked: true,
            presenceResponsive: true,
            reflectiveSoftness: true,
            colorPalettes: {
                calm: { primary: '#4a90d9', secondary: '#3a7bc8', accent: '#5ba0e9', background: '#0a0a1a' },
                awake: { primary: '#5ba0e9', secondary: '#4a90d9', accent: '#6cb0f9', background: '#0d0d1f' },
                focused: { primary: '#6c5ce7', secondary: '#5b4bc6', accent: '#7d6df7', background: '#0f0f25' },
                justice: { primary: '#8b2c5d', secondary: '#7b1c4d', accent: '#9b3c6d', background: '#150a1a' },
                protective: { primary: '#ff8c00', secondary: '#e67e00', accent: '#ff9c20', background: '#1a0f05' },
                emergency: { primary: '#ff0000', secondary: '#cc0000', accent: '#ff3333', background: '#1a0000' },
                stealth: { primary: '#1a1a2e', secondary: '#0d0d1a', accent: '#2a2a3e', background: '#05050a' },
                reflective: { primary: '#4a4a8a', secondary: '#3a3a7a', accent: '#5a5a9a', background: '#0a0a15' },
                dreaming: { primary: '#2d2d5e', secondary: '#1d1d4e', accent: '#3d3d6e', background: '#0a0a18' },
                recovery: { primary: '#3d7e9a', secondary: '#2d6e8a', accent: '#4d8eaa', background: '#0a151a' }
            },
            transitions: {
                durationMs: { normal: 500, justice: 300, protective: 200, emergency: 50 },
                easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
            },
            description: 'الإضاءة المحيطة - لون وعاطفة SOVRA'
        },

        /* ====================================================
           MOTION PHYSICS
        ==================================================== */

        motion: {
            fluidMotion: true,
            cinematicInertia: true,
            calmTransitions: true,
            avoidSharpMovement: true,
            adaptiveSlowdown: true,
            byState: {
                calm: { smoothness: 0.95, inertia: 0.90, speed: 0.3 },
                awake: { smoothness: 0.88, inertia: 0.85, speed: 0.5 },
                focused: { smoothness: 0.92, inertia: 0.88, speed: 0.2 },
                justice: { smoothness: 0.75, inertia: 0.70, speed: 0.8 },
                protective: { smoothness: 0.65, inertia: 0.60, speed: 0.95 },
                emergency: { smoothness: 0.45, inertia: 0.40, speed: 1.0, sharp: true },
                stealth: { smoothness: 0.98, inertia: 0.95, speed: 0.1 },
                reflective: { smoothness: 0.96, inertia: 0.93, speed: 0.15 },
                dreaming: { smoothness: 0.94, inertia: 0.92, speed: 0.2 },
                recovery: { smoothness: 0.90, inertia: 0.87, speed: 0.25 }
            },
            description: 'حركة SOVRA - سينمائية وهادئة أو سريعة وحاسمة'
        },

        /* ====================================================
           OWNER-CENTRIC VISUALS
        ==================================================== */

        ownerCentric: {
            enabled: true,
            ownerNearby: {
                glowBoost: 0.25,
                auraEffect: true,
                priorityIndicator: true,
                colorAccent: '#FFD700'
            },
            ownerInDanger: {
                alertVisuals: true,
                protectiveShield: true,
                dangerHighlights: true,
                fullAttentionMode: true
            },
            ownerSleeping: {
                dimAtmosphere: true,
                silentMode: true,
                protectiveGuard: true
            },
            description: 'تأثيرات بصرية خاصة بالسيد'
        },

        /* ====================================================
           JUSTICE VISUALS
        ==================================================== */

        justiceVisuals: {
            enabled: true,
            crimeDetected: {
                justiceBadge: true,
                trackingLines: true,
                evidenceHighlights: true,
                alertRings: true
            },
            criminalTracking: {
                trackingPath: true,
                suspectHighlight: true,
                movementTrail: true,
                locationPulse: true
            },
            evidenceCollection: {
                evidenceGlow: true,
                captureAnimation: true,
                storeVisual: true
            },
            description: 'بصريات العدالة - تتبع وجمع أدلة'
        },

        /* ====================================================
           EMERGENCY VISUALS
        ==================================================== */

        emergencyVisuals: {
            enabled: true,
            warnings: {
                criticalFlash: { enabled: true, frequency: 200, color: '#ff0000' },
                dangerPulse: { enabled: true, frequency: 500, color: '#ff3333' },
                alertRings: { enabled: true, frequency: 300 }
            },
            indicators: {
                ownerLocation: true,
                threatDirection: true,
                escapeRoute: true,
                emergencyContact: true
            },
            description: 'بصريات الطوارئ - إنذار فوري وواضح'
        },

        /* ====================================================
           STEALTH VISUALS
        ==================================================== */

        stealthVisuals: {
            enabled: true,
            stealthMode: {
                fadeOut: true,
                invisibleUI: true,
                noTraces: true,
                minimalPresence: true
            },
            reveal: {
                smoothReveal: true,
                gentleFadeIn: true,
                presenceReturn: true
            },
            description: 'بصريات التخفي - شبه غير مرئي'
        },

        /* ====================================================
           COGNITIVE LOAD REACTION
        ==================================================== */

        cognitiveLoadReaction: {
            reduceVisualIntensity: true,
            reduceMotion: true,
            reduceGlow: true,
            simplifyAtmosphere: true,
            prioritizeHumanFocus: true,
            levels: {
                low: { reduction: 0 },
                moderate: { reduction: 0.20, simplifyGlow: true },
                high: { reduction: 0.45, simplifyGlow: true, reduceMotion: true },
                critical: { reduction: 0.70, simplifyAll: true, minimalPresence: true }
            },
            description: 'تخفيف التأثيرات البصرية عند ارتفاع الحمل الإدراكي'
        },

        /* ====================================================
           SPATIAL CALMNESS
        ==================================================== */

        spatialCalmness: {
            preserveVisualBreathingSpace: true,
            reduceClutter: true,
            adaptiveOpacity: true,
            ambientSpacing: true,
            lowNoiseComposition: true,
            properties: {
                maxElementsOnScreen: { normal: 20, focused: 10, emergency: 5 },
                spacingMultiplier: { normal: 1.0, focused: 1.5, emergency: 0.8 },
                opacityBaseline: { normal: 0.8, focused: 0.6, emergency: 1.0 }
            },
            description: 'الحفاظ على مساحة هادئة وخالية من الفوضى'
        },

        /* ====================================================
           ATMOSPHERE DIRECTIVES
        ==================================================== */

        directives: {
            calmnessOverSpectacle: true,
            atmosphereShouldFeelAlive: true,
            preserveHumanAttention: true,
            adaptiveWithoutOverwhelming: true,
            cinematicButRespectful: true,
            ownerChangesAtmosphere: true,
            justiceHasVisualSignature: true,
            emergencyIsUnmistakable: true,
            stealthIsInvisible: true,
            atmosphereBreathesWithSystem: true
        }
    };

    /* ========================================================
       FREEZE ATMOSPHERE
    ======================================================== */

    Object.freeze(SOVRA_PRESENCE_ATMOSPHERE);

    /* ========================================================
       GLOBAL EXPORT
    ======================================================== */

    window.SOVRA_PRESENCE_ATMOSPHERE = SOVRA_PRESENCE_ATMOSPHERE;

    /* ========================================================
       REGISTRY EXPORT (LEGACY)
    ======================================================== */

    if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
        window.SOVEREIGN.register('presence-atmosphere', SOVRA_PRESENCE_ATMOSPHERE);
    }

    /* ========================================================
       LAYER REGISTRATION - التسجيل في سجل الطبقات
    ======================================================== */

    /* دالة التسجيل مع إعادة المحاولة */
    const registerPresenceAtmosphereInLayerRegistry = () => {
        const registry = window.SOVRA_LAYER_REGISTRY;
        
        if (!registry) {
            console.warn('⚠️ Presence Atmosphere: Layer Registry not found. Will retry in 1 second...');
            setTimeout(registerPresenceAtmosphereInLayerRegistry, 1000);
            return;
        }
        
        const registrationResult = registry.register(
            'presence-atmosphere',
            {
                type: 'presence',
                role: 'ambient-cognitive-atmosphere',
                authority: [
                    'breathing',
                    'glow',
                    'ambient-presence',
                    'visual-atmosphere',
                    'motion-physics'
                ],
                dependencies: [
                    'cognitive-energy',
                    'temporal-cognition',
                    'runtime-consciousness-core'
                ],
                files: ['system-presence-atmosphere.js'],
                priority: 400,
                canRead: ['consciousness_state', 'energy_levels'],
                canWrite: ['visual_state', 'atmosphere_state'],
                canOverride: ['visual_anomalies']
            }
        );
        
        if (registrationResult) {
            console.log('✅ Presence Atmosphere registered in Layer Registry');
            
            /* تحديث النبض */
            if (registry.updateHeartbeat) {
                setInterval(() => {
                    registry.updateHeartbeat('presence-atmosphere');
                }, 5000);
            }
            
            /* وضع علامة مكتمل */
            if (registry.markInitialized) {
                registry.markInitialized('presence-atmosphere');
            }
        } else {
            console.error('❌ Failed to register Presence Atmosphere in Layer Registry');
        }
    };

    /* ========================================================
       بدء التسجيل
    ======================================================== */

    registerPresenceAtmosphereInLayerRegistry();

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('🌌 SOVRA Presence Atmosphere v2.0 Initialized');
    console.log('   🎨 Living Atmosphere: ENABLED');
    console.log('   😌 Calm: Soft blue - peace');
    console.log('   ⚖️ Justice: Crimson violet - power');
    console.log('   🛡️ Protective: Orange fire - protection');
    console.log('   🔥 Emergency: Red - danger');
    console.log('   🕶️ Stealth: Near invisible');
    console.log('   💭 Reflective: Deep purple - thought');
    console.log('   💤 Dreaming: Dreamy nebula');
    console.log('   👑 Owner Aura: Gold - priority');
    console.log('   📊 Total States: ' + Object.keys(SOVRA_PRESENCE_ATMOSPHERE.states).length);
    console.log('   🌬️ Breathing Cycles: 10 different rhythms');
    console.log('   ✨ Visual Effects: Per-state effects');
    console.log('   📋 Layer Registry: ' + (window.SOVRA_LAYER_REGISTRY ? 'connected' : 'waiting...'));

})();
