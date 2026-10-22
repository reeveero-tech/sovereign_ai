/* ============================================================
   SOVRA — cognitive-input.js
   الإصدار: 2.0.0
   واجهة الإدخال الإدراكية الحية - بوابة العقل
   حيث يتفاعل السيد مع SOVRA عبر الكلمات، الأفكار، والأوامر
   ============================================================ */

(() => {

    class SovraCognitiveInput {

        constructor() {

            /* العناصر */
            this.element = null;
            this.input = null;
            this.suggestionsPanel = null;
            this.contextIndicator = null;
            this.thoughtParticles = null;
            
            /* الحالة */
            this.initialized = false;
            this.isExpanded = false;
            this.currentContext = 'neutral';
            this.thoughtHistory = [];
            this.suggestions = [];
            
            /* الإعدادات */
            this.config = {
                maxHistory: 50,
                autoSuggest: true,
                contextAware: true,
                thoughtAnimation: true,
                particleCount: 30
            };
            
            /* مقاييس التفكير */
            this.thoughtMetrics = {
                wordsTyped: 0,
                thoughtsSubmitted: 0,
                averageLength: 0,
                lastThoughtTime: null
            };
            
            /* التسجيل في Layer Registry */
            this.layerRegistered = false;
            
            console.log('⌨️ SOVRA Cognitive Input v2.0.0 Created');
        }

        /* ====================================================
           INIT - التهيئة الكاملة
        ==================================================== */

        init() {
            this.create();
            this.bindEvents();
            this.registerWithLayerRegistry();
            this.startThoughtMonitoring();
            this.initialized = true;
            
            console.log('🧠 SOVRA Cognitive Input Initialized');
            console.log('   📝 Type your thoughts. SOVRA is listening.');
            
            return this;
        }

        /* ====================================================
           REGISTER WITH LAYER REGISTRY - التسجيل في سجل الطبقات
        ==================================================== */

        registerWithLayerRegistry() {
            const registry = window.SOVRA_LAYER_REGISTRY;
            
            if (!registry) {
                console.warn('⚠️ Cognitive Input: Layer Registry not found. Will retry...');
                setTimeout(() => this.registerWithLayerRegistry(), 1000);
                return;
            }
            
            const result = registry.register(
                'cognitive-input',
                {
                    type: 'ui',
                    role: 'human-cognitive-input-surface',
                    authority: [
                        'human-input',
                        'thought-capture',
                        'command-routing'
                    ],
                    dependencies: [
                        'neural-runtime-bus',
                        'runtime-orchestrator-ai',
                        'presence-atmosphere'
                    ],
                    files: ['ui/cognitive-input.js'],
                    priority: 300,
                    canRead: ['user_input'],
                    canWrite: ['command_queue', 'thought_stream'],
                    canOverride: ['none']
                }
            );
            
            if (result) {
                this.layerRegistered = true;
                console.log('✅ Cognitive Input registered in Layer Registry');
                
                if (registry.updateHeartbeat) {
                    setInterval(() => {
                        registry.updateHeartbeat('cognitive-input');
                    }, 5000);
                }
                
                if (registry.markInitialized) {
                    registry.markInitialized('cognitive-input');
                }
            }
        }

        /* ====================================================
           CREATE - إنشاء الواجهة الكاملة
        ==================================================== */

        create() {
            /* الحاوية الرئيسية */
            this.element = document.createElement('div');
            this.element.className = 'sovra-cognitive-container';
            this.element.setAttribute('data-state', 'collapsed');
            /* R-715: يبدأ مصغّرًا (فقاعة 🧠) كي لا يغطي المحتوى؛ النقر يفتحه */
            this.element.setAttribute('data-minimized', 'true');
            
            /* منطقة الإدخال الرئيسية */
            const inputArea = document.createElement('div');
            inputArea.className = 'sovra-cognitive-input-area';
            
            /* أيقونة الحضور */
            const presenceIcon = document.createElement('div');
            presenceIcon.className = 'sovra-cognitive-presence';
            presenceIcon.innerHTML = '🧠';
            presenceIcon.setAttribute('data-active', 'false');
            presenceIcon.title = 'انقر للفتح/الإخفاء — اسحب للتحريك';
            
            /* حقل الإدخال */
            this.input = document.createElement('textarea');
            this.input.className = 'sovra-cognitive-input';
            this.input.placeholder = 'اكتب فكرتك هنا... SOVRA يستمع...';
            this.input.rows = 1;
            this.input.setAttribute('data-cognitive-state', 'idle');
            
            /* أزرار الإجراءات */
            const actionBar = document.createElement('div');
            actionBar.className = 'sovra-cognitive-actions';
            
            const submitBtn = document.createElement('button');
            submitBtn.className = 'sovra-cognitive-submit';
            submitBtn.innerHTML = '📤 إرسال';
            submitBtn.setAttribute('aria-label', 'إرسال الفكرة');
            
            const expandBtn = document.createElement('button');
            expandBtn.className = 'sovra-cognitive-expand';
            expandBtn.innerHTML = '🔽 تكبير';
            expandBtn.setAttribute('aria-label', 'توسيع الحقل');
            
            const clearBtn = document.createElement('button');
            clearBtn.className = 'sovra-cognitive-clear';
            clearBtn.innerHTML = '🗑️ مسح';
            clearBtn.setAttribute('aria-label', 'مسح الحقل');
            
            /* R-715: زر إخفاء — الحاوية كانت ثابتة فوق المحتوى بلا إغلاق ولا تحريك */
            const minimizeBtn = document.createElement('button');
            minimizeBtn.className = 'sovra-cognitive-minimize';
            minimizeBtn.innerHTML = '➖ إخفاء';
            minimizeBtn.setAttribute('aria-label', 'إخفاء الحقل');
            
            actionBar.appendChild(submitBtn);
            actionBar.appendChild(expandBtn);
            actionBar.appendChild(clearBtn);
            actionBar.appendChild(minimizeBtn);
            
            /* لوحة الاقتراحات */
            this.suggestionsPanel = document.createElement('div');
            this.suggestionsPanel.className = 'sovra-cognitive-suggestions';
            this.suggestionsPanel.style.display = 'none';
            
            /* مؤشر السياق */
            this.contextIndicator = document.createElement('div');
            this.contextIndicator.className = 'sovra-cognitive-context';
            this.contextIndicator.innerHTML = '🎯 السياق: عام';
            
            /* جسيمات الفكر */
            this.thoughtParticles = document.createElement('div');
            this.thoughtParticles.className = 'sovra-cognitive-particles';
            
            /* تجميع العناصر */
            inputArea.appendChild(presenceIcon);
            inputArea.appendChild(this.input);
            inputArea.appendChild(actionBar);
            
            this.element.appendChild(inputArea);
            this.element.appendChild(this.suggestionsPanel);
            this.element.appendChild(this.contextIndicator);
            this.element.appendChild(this.thoughtParticles);
            
            /* إضافة إلى DOM */
            const appRoot = document.getElementById('app-root');
            if (appRoot) {
                appRoot.appendChild(this.element);
            } else {
                document.body.appendChild(this.element);
            }
            
            /* إضافة الأنماط الديناميكية */
            this.injectStyles();
        }

        /* ====================================================
           INJECT STYLES - إضافة الأنماط الديناميكية
        ==================================================== */

        injectStyles() {
            const styleId = 'sovra-cognitive-styles';
            if (document.getElementById(styleId)) return;
            
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                .sovra-cognitive-container {
                    position: fixed;
                    bottom: 100px;
                    right: 30px;
                    width: 380px;
                    max-width: calc(100vw - 60px);
                    background: rgba(10, 10, 20, 0.85);
                    backdrop-filter: blur(20px);
                    border-radius: 24px;
                    border: 1px solid rgba(100, 150, 255, 0.3);
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3), 0 0 20px rgba(100, 150, 255, 0.1);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    z-index: 10000;
                    font-family: 'Cairo', sans-serif;
                }
                
                .sovra-cognitive-container:hover {
                    border-color: rgba(100, 150, 255, 0.6);
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(100, 150, 255, 0.2);
                }
                
                /* R-715: وضع مصغّر — فقاعة صغيرة فقط */
                .sovra-cognitive-container[data-minimized="true"] {
                    width: auto;
                    border-radius: 50%;
                }
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-input-area {
                    padding: 8px;
                }
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-input,
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-actions,
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-suggestions,
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-context,
                .sovra-cognitive-container[data-minimized="true"] .sovra-cognitive-particles {
                    display: none !important;
                }
                .sovra-cognitive-presence {
                    touch-action: none;
                }
                .sovra-cognitive-container.sovra-dragging {
                    transition: none;
                }
                
                .sovra-cognitive-container[data-state="expanded"] {
                    width: 600px;
                    bottom: 50px;
                    right: 50px;
                }
                
                .sovra-cognitive-input-area {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 16px;
                }
                
                .sovra-cognitive-presence {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #4a90d9, #6c5ce7);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 22px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 0 15px rgba(100, 150, 255, 0.3);
                }
                
                .sovra-cognitive-presence[data-active="true"] {
                    animation: cognitivePulse 1.5s ease-in-out infinite;
                    box-shadow: 0 0 25px rgba(100, 150, 255, 0.6);
                }
                
                @keyframes cognitivePulse {
                    0%, 100% { transform: scale(1); opacity: 0.8; }
                    50% { transform: scale(1.1); opacity: 1; }
                }
                
                .sovra-cognitive-input {
                    flex: 1;
                    background: rgba(0, 0, 0, 0.5);
                    border: none;
                    border-radius: 20px;
                    padding: 12px 16px;
                    color: #e0e0ff;
                    font-size: 15px;
                    font-family: inherit;
                    resize: none;
                    outline: none;
                    transition: all 0.2s ease;
                    line-height: 1.5;
                }
                
                .sovra-cognitive-input:focus {
                    background: rgba(0, 0, 0, 0.7);
                    box-shadow: 0 0 0 2px rgba(100, 150, 255, 0.3);
                }
                
                .sovra-cognitive-input[data-cognitive-state="focused"] {
                    border-left: 3px solid #6c5ce7;
                }
                
                .sovra-cognitive-actions {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .sovra-cognitive-submit,
                .sovra-cognitive-minimize,
                .sovra-cognitive-expand,
                .sovra-cognitive-clear {
                    background: rgba(100, 150, 255, 0.15);
                    border: 1px solid rgba(100, 150, 255, 0.3);
                    border-radius: 12px;
                    padding: 8px 12px;
                    color: #c0c0ff;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-family: inherit;
                }
                
                .sovra-cognitive-submit:hover {
                    background: rgba(100, 150, 255, 0.3);
                    border-color: rgba(100, 150, 255, 0.6);
                    transform: scale(1.02);
                }
                
                .sovra-cognitive-expand:hover {
                    background: rgba(100, 150, 255, 0.3);
                    transform: scale(1.02);
                }
                
                .sovra-cognitive-clear:hover {
                    background: rgba(255, 100, 100, 0.3);
                    border-color: rgba(255, 100, 100, 0.6);
                }
                
                .sovra-cognitive-suggestions {
                    padding: 0 16px 16px 16px;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    border-top: 1px solid rgba(100, 150, 255, 0.1);
                }
                
                .sovra-cognitive-suggestion {
                    background: rgba(100, 150, 255, 0.1);
                    border-radius: 20px;
                    padding: 6px 14px;
                    font-size: 12px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .sovra-cognitive-suggestion:hover {
                    background: rgba(100, 150, 255, 0.25);
                    transform: translateY(-1px);
                }
                
                .sovra-cognitive-context {
                    padding: 8px 16px;
                    font-size: 11px;
                    color: #8a8aaa;
                    border-top: 1px solid rgba(100, 150, 255, 0.1);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .sovra-cognitive-particles {
                    position: absolute;
                    bottom: 100%;
                    right: 0;
                    pointer-events: none;
                }
                
                .cognitive-particle {
                    position: absolute;
                    width: 4px;
                    height: 4px;
                    background: radial-gradient(circle, #6c5ce7, #4a90d9);
                    border-radius: 50%;
                    opacity: 0;
                    animation: particleFloat 2s ease-out forwards;
                }
                
                @keyframes particleFloat {
                    0% {
                        opacity: 0.8;
                        transform: translateY(0) scale(1);
                    }
                    100% {
                        opacity: 0;
                        transform: translateY(-60px) scale(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        /* ====================================================
           BIND EVENTS - ربط الأحداث
        ==================================================== */

        bindEvents() {
            /* التركيز على الحقل */
            this.input.addEventListener('focus', () => {
                this.input.setAttribute('data-cognitive-state', 'focused');
                this.updateCognitiveState('focused');
                
                /* إرسال إشارة التركيز */
                this.sendToBus('cognitive:focus', {
                    timestamp: Date.now()
                });
            });
            
            /* فقدان التركيز */
            this.input.addEventListener('blur', () => {
                this.input.setAttribute('data-cognitive-state', 'idle');
                this.updateCognitiveState('idle');
            });
            
            /* الكتابة */
            this.input.addEventListener('input', (e) => {
                const value = e.target.value;
                const wordCount = value.trim().split(/\s+/).filter(w => w.length > 0).length;
                
                this.thoughtMetrics.wordsTyped++;
                
                /* تغيير ارتفاع الحقل تلقائياً */
                this.input.style.height = 'auto';
                this.input.style.height = Math.min(120, this.input.scrollHeight) + 'px';
                
                /* تحديث السياق بناءً على المحتوى */
                if (this.config.contextAware) {
                    this.updateContextFromContent(value);
                }
                
                /* اقتراحات تلقائية */
                if (this.config.autoSuggest && value.length > 10) {
                    this.generateSuggestions(value);
                }
                
                /* إرسال إشارة التفكير */
                this.sendToBus('cognitive:typing', {
                    length: value.length,
                    wordCount: wordCount,
                    timestamp: Date.now()
                });
            });
            
            /* إرسال الفكرة */
            const submitBtn = this.element.querySelector('.sovra-cognitive-submit');
            if (submitBtn) {
                submitBtn.addEventListener('click', () => {
                    this.submitThought();
                });
            }
            
            /* توسيع الحقل */
            const expandBtn = this.element.querySelector('.sovra-cognitive-expand');
            if (expandBtn) {
                expandBtn.addEventListener('click', () => {
                    this.toggleExpand();
                });
            }
            
            /* R-715: إخفاء/إظهار + سحب من أيقونة الحضور */
            const minimizeBtn = this.element.querySelector('.sovra-cognitive-minimize');
            if (minimizeBtn) {
                minimizeBtn.addEventListener('click', () => this.setMinimized(true));
            }
            this.bindDrag();
            
            /* مسح الحقل */
            const clearBtn = this.element.querySelector('.sovra-cognitive-clear');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.clearInput();
                });
            }
            
            /* إرسال بالضغط على Enter + Ctrl */
            this.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.submitThought();
                }
                
                /* تكبير بالضغط على Ctrl + ↑ */
                if (e.key === 'ArrowUp' && e.ctrlKey) {
                    e.preventDefault();
                    this.toggleExpand();
                }
            });
        }

        /* ====================================================
           R-715: MINIMIZE / DRAG
        ==================================================== */

        setMinimized(minimized) {
            this.element.setAttribute('data-minimized', minimized ? 'true' : 'false');
            if (!minimized && this.input) {
                this.input.focus();
            }
        }

        bindDrag() {
            const handle = this.element.querySelector('.sovra-cognitive-presence');
            if (!handle) return;
            let start = null;
            let moved = false;

            handle.addEventListener('pointerdown', (e) => {
                const r = this.element.getBoundingClientRect();
                start = { x: e.clientX, y: e.clientY, left: r.left, top: r.top };
                moved = false;
                handle.setPointerCapture?.(e.pointerId);
            });

            handle.addEventListener('pointermove', (e) => {
                if (!start) return;
                const dx = e.clientX - start.x;
                const dy = e.clientY - start.y;
                if (!moved && Math.abs(dx) + Math.abs(dy) < 6) return;
                moved = true;
                this.element.classList.add('sovra-dragging');
                const w = this.element.offsetWidth;
                const h = this.element.offsetHeight;
                const left = Math.max(0, Math.min(window.innerWidth - w, start.left + dx));
                const top = Math.max(0, Math.min(window.innerHeight - h, start.top + dy));
                this.element.style.left = left + 'px';
                this.element.style.top = top + 'px';
                this.element.style.right = 'auto';
                this.element.style.bottom = 'auto';
            });

            const end = (e) => {
                if (!start) return;
                handle.releasePointerCapture?.(e.pointerId);
                this.element.classList.remove('sovra-dragging');
                if (!moved) {
                    const isMin = this.element.getAttribute('data-minimized') === 'true';
                    this.setMinimized(!isMin);
                }
                start = null;
            };
            handle.addEventListener('pointerup', end);
            handle.addEventListener('pointercancel', end);
        }

        /* ====================================================
           SUBMIT THOUGHT - إرسال الفكرة
        ==================================================== */

        submitThought() {
            const thought = this.input.value.trim();
            if (!thought) return;
            
            /* تسجيل في السجل */
            this.thoughtHistory.unshift({
                content: thought,
                timestamp: Date.now(),
                context: this.currentContext
            });
            
            if (this.thoughtHistory.length > this.config.maxHistory) {
                this.thoughtHistory.pop();
            }
            
            /* تحديث المقاييس */
            this.thoughtMetrics.thoughtsSubmitted++;
            const words = thought.split(/\s+/).length;
            this.thoughtMetrics.averageLength = 
                (this.thoughtMetrics.averageLength * (this.thoughtMetrics.thoughtsSubmitted - 1) + words) / 
                this.thoughtMetrics.thoughtsSubmitted;
            this.thoughtMetrics.lastThoughtTime = Date.now();
            
            /* إرسال عبر الناقل العصبي */
            this.sendToBus('cognitive:thought', {
                content: thought,
                length: thought.length,
                words: words,
                context: this.currentContext,
                timestamp: Date.now()
            });
            
            /* إظهار تأثير الجسيمات */
            this.showThoughtParticles();
            
            /* تحديث مؤشر الحضور */
            const presenceIcon = this.element.querySelector('.sovra-cognitive-presence');
            if (presenceIcon) {
                presenceIcon.setAttribute('data-active', 'true');
                setTimeout(() => {
                    presenceIcon.setAttribute('data-active', 'false');
                }, 500);
            }
            
            /* R-715: كان الحقل يضيف النص محليًا فقط (لا مشترك في cognitive:thought)
               ⇒ يبدو أنه أُرسل ولم يصل للخادم. الآن يمر بمسار المحادثة الحقيقي. */
            if (window.SOVEREIGN_BRIDGE && typeof window.SOVEREIGN_BRIDGE.handleModernChat === 'function') {
                window.SOVEREIGN_BRIDGE.handleModernChat(thought);
            } else {
                this.addToDialogue(thought);
                window.SOVEREIGN_NOTIFY?.warning?.('لم يُرسل: مسار المحادثة غير متاح');
            }
            
            /* مسح الحقل */
            this.clearInput();
            
            console.log(`📝 Thought submitted: ${thought.substring(0, 50)}...`);
        }

        /* ====================================================
           CLEAR INPUT - مسح الحقل
        ==================================================== */

        clearInput() {
            this.input.value = '';
            this.input.style.height = 'auto';
            this.input.focus();
            
            /* إخفاء الاقتراحات */
            if (this.suggestionsPanel) {
                this.suggestionsPanel.style.display = 'none';
            }
        }

        /* ====================================================
           TOGGLE EXPAND - تكبير/تصغير الحقل
        ==================================================== */

        toggleExpand() {
            this.isExpanded = !this.isExpanded;
            this.element.setAttribute('data-state', this.isExpanded ? 'expanded' : 'collapsed');
            this.input.rows = this.isExpanded ? 6 : 1;
            
            const expandBtn = this.element.querySelector('.sovra-cognitive-expand');
            if (expandBtn) {
                expandBtn.innerHTML = this.isExpanded ? '🔼 تصغير' : '🔽 تكبير';
            }
            
            /* إرسال إشارة التوسيع */
            this.sendToBus('cognitive:expand', {
                expanded: this.isExpanded,
                timestamp: Date.now()
            });
        }

        /* ====================================================
           UPDATE CONTEXT - تحديث السياق
        ==================================================== */

        updateContextFromContent(content) {
            /* تحليل بسيط للسياق */
            let newContext = 'عام';
            
            if (content.includes('حماية') || content.includes('أمن') || content.includes('خطر')) {
                newContext = 'حماية';
            } else if (content.includes('عدالة') || content.includes('جريمة') || content.includes('مجرم')) {
                newContext = 'عدالة';
            } else if (content.includes('سؤال') || content.includes('استفسار')) {
                newContext = 'استفسار';
            } else if (content.includes('أمر') || content.includes('نفذ')) {
                newContext = 'أمر';
            }
            
            if (newContext !== this.currentContext) {
                this.currentContext = newContext;
                this.contextIndicator.innerHTML = `🎯 السياق: ${newContext}`;
                
                /* تغيير لون المؤشر حسب السياق */
                const colors = {
                    'عام': '#8a8aaa',
                    'حماية': '#ff8c00',
                    'عدالة': '#dc143c',
                    'استفسار': '#4a90d9',
                    'أمر': '#FFD700'
                };
                this.contextIndicator.style.color = colors[newContext] || '#8a8aaa';
            }
        }

        /* ====================================================
           GENERATE SUGGESTIONS - توليد الاقتراحات
        ==================================================== */

        generateSuggestions(input) {
            /* اقتراحات بسيطة مبنية على الكلمات المفتاحية */
            const suggestions = [];
            
            if (input.includes('حماية')) {
                suggestions.push('نظام الحماية', 'مراقبة الأمن', 'تنبيهات الطوارئ');
            } else if (input.includes('عدالة')) {
                suggestions.push('تتبع المجرمين', 'جمع الأدلة', 'الإبلاغ عن جريمة');
            } else if (input.includes('ذاكرة')) {
                suggestions.push('استرجاع الذاكرة', 'البحث في السجل', 'الذاكرة طويلة المدى');
            } else if (input.includes('حالة')) {
                suggestions.push('حالة النظام', 'حالة الطاقة', 'حالة الوعي');
            }
            
            if (suggestions.length > 0) {
                this.showSuggestions(suggestions);
            } else {
                this.suggestionsPanel.style.display = 'none';
            }
        }

        /* ====================================================
           SHOW SUGGESTIONS - عرض الاقتراحات
        ==================================================== */

        showSuggestions(suggestions) {
            this.suggestionsPanel.innerHTML = '';
            suggestions.forEach(suggestion => {
                const chip = document.createElement('div');
                chip.className = 'sovra-cognitive-suggestion';
                chip.textContent = suggestion;
                chip.addEventListener('click', () => {
                    this.input.value = suggestion;
                    this.submitThought();
                });
                this.suggestionsPanel.appendChild(chip);
            });
            this.suggestionsPanel.style.display = 'flex';
        }

        /* ====================================================
           SHOW THOUGHT PARTICLES - إظهار جسيمات الفكر
        ==================================================== */

        showThoughtParticles() {
            const rect = this.input.getBoundingClientRect();
            const particleCount = this.config.particleCount;
            
            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'cognitive-particle';
                particle.style.left = (rect.left + Math.random() * rect.width) + 'px';
                particle.style.top = (rect.top - 10) + 'px';
                particle.style.animationDelay = Math.random() * 0.5 + 's';
                particle.style.width = (Math.random() * 6 + 2) + 'px';
                particle.style.height = particle.style.width;
                document.body.appendChild(particle);
                
                setTimeout(() => {
                    particle.remove();
                }, 2000);
            }
        }

        /* ====================================================
           ADD TO DIALOGUE - إضافة إلى المحادثة
        ==================================================== */

        addToDialogue(thought) {
            /* البحث عن عنصر المحادثة */
            const dialogueGroups = document.getElementById('dialogue-groups');
            if (!dialogueGroups) return;
            
            /* إزالة الحالة الفارغة */
            const emptyState = dialogueGroups.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }
            
            /* إضافة الفكرة */
            const messageElement = document.createElement('div');
            messageElement.className = 'dialogue-message user-message';
            messageElement.innerHTML = `
                <div class="message-avatar">👤</div>
                <div class="message-content">
                    <div class="message-text">${this.escapeHtml(thought)}</div>
                    <div class="message-time">${new Date().toLocaleTimeString()}</div>
                </div>
            `;
            
            dialogueGroups.appendChild(messageElement);
            dialogueGroups.scrollTop = dialogueGroups.scrollHeight;
        }

        /* ====================================================
           SEND TO BUS - إرسال عبر الناقل العصبي
        ==================================================== */

        sendToBus(event, data) {
            const bus = window.SOVEREIGN_BUS || window.SOVEREIGN_ACCESS?.bus?.();
            if (bus && typeof bus.publishWithoutMiddleware === 'function') {
                bus.publishWithoutMiddleware(event, data);
            }
        }

        /* ====================================================
           UPDATE COGNITIVE STATE - تحديث الحالة الإدراكية
        ==================================================== */

        updateCognitiveState(state) {
            if (window.SOVRA_PRESENCE_ATMOSPHERE) {
                /* تحديث الحالة في الغلاف الإدراكي */
                document.body.dataset.cognitiveState = state;
            }
        }

        /* ====================================================
           START THOUGHT MONITORING - بدء مراقبة التفكير
        ==================================================== */

        startThoughtMonitoring() {
            /* تحديث المقاييس كل دقيقة */
            setInterval(() => {
                this.updateMetrics();
            }, 60000);
        }

        /* ====================================================
           UPDATE METRICS - تحديث المقاييس
        ==================================================== */

        updateMetrics() {
            /* تحديث عداد الأوامر في الواجهة */
            const commandCount = document.getElementById('sir-command-count');
            if (commandCount) {
                commandCount.textContent = this.thoughtMetrics.thoughtsSubmitted;
            }
            
            const chatCount = document.getElementById('chat-input-count');
            if (chatCount) {
                chatCount.textContent = this.thoughtMetrics.thoughtsSubmitted;
            }
        }

        /* ====================================================
           ESCAPE HTML - ترميز HTML
        ==================================================== */

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        /* ====================================================
           GET STATUS - الحصول على الحالة
        ==================================================== */

        getStatus() {
            return {
                initialized: this.initialized,
                isExpanded: this.isExpanded,
                currentContext: this.currentContext,
                thoughtMetrics: { ...this.thoughtMetrics },
                thoughtHistoryCount: this.thoughtHistory.length,
                layerRegistered: this.layerRegistered
            };
        }

        /* ====================================================
           DESTROY - تدمير الواجهة
        ==================================================== */

        destroy() {
            if (this.element) {
                this.element.remove();
            }
            
            const registry = window.SOVRA_LAYER_REGISTRY;
            if (registry && registry.markUnhealthy) {
                registry.markUnhealthy('cognitive-input', 'destroyed');
            }
            
            console.log('⌨️ SOVRA Cognitive Input Destroyed');
        }
    }

    /* ========================================================
       CREATE INSTANCE - إنشاء المثيل
    ======================================================== */

    const cognitiveInput = new SovraCognitiveInput();

    /* ========================================================
       GLOBAL EXPORT - التصدير العام
    ======================================================== */

    window.SOVRA_COGNITIVE_INPUT = cognitiveInput;

    /* ========================================================
       LAYER REGISTRATION - التسجيل في سجل الطبقات
    ======================================================== */

    const registerWithRegistry = () => {
        const registry = window.SOVRA_LAYER_REGISTRY;
        if (registry && cognitiveInput) {
            const result = registry.register(
                'cognitive-input',
                {
                    type: 'ui',
                    role: 'human-cognitive-input-surface',
                    authority: [
                        'human-input',
                        'thought-capture',
                        'command-routing'
                    ],
                    dependencies: [
                        'neural-runtime-bus',
                        'runtime-orchestrator-ai',
                        'presence-atmosphere'
                    ],
                    files: ['ui/cognitive-input.js'],
                    priority: 300,
                    canRead: ['user_input'],
                    canWrite: ['command_queue', 'thought_stream'],
                    canOverride: ['none']
                }
            );
            
            if (result) {
                console.log('✅ cognitive-input registered in Layer Registry');
                if (registry.markInitialized) {
                    registry.markInitialized('cognitive-input');
                }
            }
        } else {
            setTimeout(registerWithRegistry, 100);
        }
    };

    /* ========================================================
       AUTO INIT - التهيئة التلقائية
    ======================================================== */

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                cognitiveInput.init();
                registerWithRegistry();
            }, 100);
        });
    } else {
        setTimeout(() => {
            cognitiveInput.init();
            registerWithRegistry();
        }, 100);
    }

    /* ========================================================
       CONSOLE
    ======================================================== */

    console.log('⌨️ SOVRA Cognitive Input Module Loaded');
    console.log('   📝 Type your thoughts. SOVRA is listening.');
    console.log('   💡 Press Ctrl+Enter to submit');
    console.log('   🔽 Press Ctrl+↑ to expand');

})();
