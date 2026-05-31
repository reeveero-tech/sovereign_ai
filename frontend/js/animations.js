/* ============================================================
   Sovereign AI — animations.js
   الإصدار: 3.0.0 - روح الواجهة السيادية الحية
   ============================================================
   
   هذا الملف يضيف:
   - جسيمات فضائية متحركة (Particles System)
   - تموجات سائلة عند اللمس/الضغط (Liquid Ripples)
   - نبضات سيادية عند التفاعل (Sovereign Pulse)
   - تأثيرات hover متقدمة مع حركة دقيقة (Micro-motion)
   - وميض ذكي عند ظهور الرسائل (Smart Blink)
   - اهتزاز بسيط عند الأخطاء (Error Shake)
   - تأثيرات لمس محسّنة للأجهزة التي تعمل باللمس
   - تحسين الأداء لضمان سلاسة التشغيل على الجوال والحاسوب
   
   ============================================================ */

// ============================================================
// 1. نظام الجسيمات الفضائية (Particles Background)
// ============================================================

class SovereignParticleSystem {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.particleCount = 0;
        this.animationId = null;
        this.isActive = true;
        this.lastTimestamp = 0;
        this.fps = 0;
        this.frameCount = 0;
        
        this.init();
    }
    
    init() {
        // إنشاء عنصر canvas
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'sovereign-particle-canvas';
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.zIndex = '-1';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.opacity = '0.6';
        
        document.body.insertBefore(this.canvas, document.body.firstChild);
        this.ctx = this.canvas.getContext('2d');
        
        // ضبط الحجم
        this.resize();
        
        // إنشاء الجسيمات بناءً على حجم الشاشة
        this.createParticles();
        
        // بدء الرسم
        this.animate();
        
        // مراقبة تغيير حجم الشاشة
        window.addEventListener('resize', () => this.resize());
        
        // مراقبة رؤية الصفحة لإيقاف الجسيمات عند التبويب غير النشط
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stop();
            } else {
                this.start();
            }
        });
    }
    
    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.createParticles();
    }
    
    createParticles() {
        // عدد الجسيمات يتناسب مع حجم الشاشة (خفيف للأجهزة البطيئة)
        const screenArea = this.canvas.width * this.canvas.height;
        const baseCount = Math.min(80, Math.max(30, Math.floor(screenArea / 15000)));
        this.particleCount = baseCount;
        
        this.particles = [];
        
        for (let i = 0; i < this.particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: Math.random() * 3 + 1,
                speedX: (Math.random() - 0.5) * 0.3,
                speedY: (Math.random() - 0.5) * 0.3,
                alpha: Math.random() * 0.4 + 0.1,
                pulse: Math.random() * Math.PI * 2,
                pulseSpeed: 0.02 + Math.random() * 0.03,
                color: this.getRandomParticleColor()
            });
        }
    }
    
    getRandomParticleColor() {
        const colors = [
            'rgba(79, 209, 197, ',     // سيان
            'rgba(129, 140, 248, ',    // بنفسجي
            'rgba(236, 72, 153, ',     // وردي
            'rgba(56, 189, 248, '      // أزرق فاتح
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }
    
    drawParticles() {
        if (!this.ctx || !this.isActive) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        for (const p of this.particles) {
            // نبض الجسيم (تغيير الحجم والشفافية)
            const pulseValue = Math.sin(p.pulse) * 0.3 + 0.7;
            const currentSize = p.size * (0.8 + pulseValue * 0.4);
            const currentAlpha = p.alpha * (0.5 + pulseValue * 0.5);
            
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, currentSize, 0, Math.PI * 2);
            this.ctx.fillStyle = `${p.color}${currentAlpha})`;
            this.ctx.fill();
            
            // تحديث النبض
            p.pulse += p.pulseSpeed;
            
            // تحديث الموقع
            p.x += p.speedX;
            p.y += p.speedY;
            
            // عكس الاتجاه عند الحدود
            if (p.x < -50) p.x = this.canvas.width + 50;
            if (p.x > this.canvas.width + 50) p.x = -50;
            if (p.y < -50) p.y = this.canvas.height + 50;
            if (p.y > this.canvas.height + 50) p.y = -50;
        }
        
        // رسم وصلات بين الجسيمات المتقاربة
        this.drawParticleConnections();
    }
    
    drawParticleConnections() {
        const maxDistance = 120;
        
        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < maxDistance) {
                    const opacity = (1 - distance / maxDistance) * 0.15;
                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.strokeStyle = `rgba(79, 209, 197, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }
    }
    
    calculateFPS() {
        this.frameCount++;
        const now = performance.now();
        if (now - this.lastTimestamp >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastTimestamp = now;
            
            // إذا كان FPS منخفضاً جداً، قلل عدد الجسيمات
            if (this.fps < 30 && this.particleCount > 20) {
                this.particleCount = Math.max(20, this.particleCount - 5);
                this.createParticles();
            }
        }
    }
    
    animate() {
        if (!this.isActive) return;
        
        this.calculateFPS();
        this.drawParticles();
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    start() {
        if (this.animationId) return;
        this.isActive = true;
        this.animate();
    }
    
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        this.isActive = false;
    }
}

// ============================================================
// 2. نظام التموجات السائلة (Liquid Ripple System)
// ============================================================

class LiquidRippleSystem {
    constructor() {
        this.ripples = [];
        this.maxRipples = 20;
        this.init();
    }
    
    init() {
        // إضافة استماع للأحداث
        document.addEventListener('click', (e) => this.createRipple(e.clientX, e.clientY));
        document.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            if (touch) this.createRipple(touch.clientX, touch.clientY);
        });
        
        // إضافة استماع للأزرار
        document.querySelectorAll('.btn, .tab, .quick-btn, .mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const rect = btn.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                this.createRipple(x, y, true);
            });
        });
    }
    
    createRipple(x, y, isButton = false) {
        const ripple = document.createElement('div');
        ripple.className = 'liquid-ripple';
        
        // خصائص التموج
        const size = isButton ? 120 : 80;
        ripple.style.cssText = `
            position: fixed;
            left: ${x - size / 2}px;
            top: ${y - size / 2}px;
            width: ${size}px;
            height: ${size}px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(79, 209, 197, 0.4) 0%, rgba(79, 209, 197, 0) 70%);
            pointer-events: none;
            z-index: 9999;
            animation: liquidRippleExpand 0.6s ease-out forwards;
        `;
        
        document.body.appendChild(ripple);
        
        // إضافة CSS للرسوم المتحركة إذا لم تكن موجودة
        this.ensureAnimationStyles();
        
        // إزالة التموج بعد انتهاء الرسوم المتحركة
        setTimeout(() => {
            if (ripple && ripple.parentNode) ripple.remove();
        }, 600);
        
        // إضافة نبض للأزرار
        if (isButton) {
            const btn = document.elementFromPoint(x, y);
            if (btn && btn.classList) {
                btn.classList.add('pulse-active');
                setTimeout(() => btn.classList.remove('pulse-active'), 400);
            }
        }
    }
    
    ensureAnimationStyles() {
        if (!document.querySelector('#ripple-animation-style')) {
            const style = document.createElement('style');
            style.id = 'ripple-animation-style';
            style.textContent = `
                @keyframes liquidRippleExpand {
                    0% {
                        transform: scale(0);
                        opacity: 0.6;
                    }
                    100% {
                        transform: scale(3);
                        opacity: 0;
                    }
                }
                
                .pulse-active {
                    animation: sovereignPulseFast 0.3s ease-out !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// ============================================================
// 3. نظام الحركة الدقيقة (Micro-motion System)
// ============================================================

class MicroMotionSystem {
    constructor() {
        this.elements = [];
        this.isEnabled = true;
        this.init();
    }
    
    init() {
        // تجنب الحركة على الأجهزة التي تعمل باللمس
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        if (isTouchDevice) {
            this.isEnabled = false;
            return;
        }
        
        // اختيار العناصر للحركة الدقيقة
        this.elements = document.querySelectorAll('.panel, .metric-card, .sovereign-card');
        
        this.elements.forEach(el => {
            el.addEventListener('mousemove', (e) => this.handleMouseMove(el, e));
            el.addEventListener('mouseleave', () => this.handleMouseLeave(el));
        });
    }
    
    handleMouseMove(el, e) {
        if (!this.isEnabled) return;
        
        const rect = el.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const deltaX = (e.clientX - centerX) / (rect.width / 2);
        const deltaY = (e.clientY - centerY) / (rect.height / 2);
        
        const maxTilt = 4;
        const tiltX = deltaY * maxTilt;
        const tiltY = -deltaX * maxTilt;
        
        el.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateZ(5px)`;
        el.style.transition = 'transform 0.1s ease-out';
    }
    
    handleMouseLeave(el) {
        if (!this.isEnabled) return;
        el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
        el.style.transition = 'transform 0.3s ease-out';
    }
    
    refresh() {
        this.elements = document.querySelectorAll('.panel, .metric-card, .sovereign-card');
    }
}

// ============================================================
// 4. نظام الوميض الذكي (Smart Blink System)
// ============================================================

class SmartBlinkSystem {
    constructor() {
        this.observer = null;
        this.init();
    }
    
    init() {
        // مراقبة إضافة رسائل جديدة
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // عنصر HTML
                        if (node.classList && (
                            node.classList.contains('message') ||
                            node.classList.contains('proposal-card') ||
                            node.classList.contains('command-item')
                        )) {
                            this.blinkElement(node);
                        }
                        
                        // البحث داخل العنصر عن الرسائل
                        if (node.querySelectorAll) {
                            node.querySelectorAll('.message, .proposal-card, .command-item').forEach(el => {
                                this.blinkElement(el);
                            });
                        }
                    }
                });
            });
        });
        
        this.observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    blinkElement(el) {
        el.style.animation = 'smartBlink 0.5s ease-out';
        setTimeout(() => {
            el.style.animation = '';
        }, 500);
    }
}

// ============================================================
// 5. نظام الاهتزاز (Error Shake System)
// ============================================================

class ErrorShakeSystem {
    constructor() {
        this.activeShakes = new Map();
    }
    
    shakeElement(element, intensity = 'medium') {
        if (!element) return;
        
        // إيقاف الاهتزاز السابق لهذا العنصر
        if (this.activeShakes.has(element)) {
            clearTimeout(this.activeShakes.get(element));
        }
        
        const intensities = {
            low: 'shakeLow 0.3s ease',
            medium: 'shakeMedium 0.4s ease',
            high: 'shakeHigh 0.5s ease'
        };
        
        const animation = intensities[intensity] || intensities.medium;
        element.style.animation = animation;
        
        const timeout = setTimeout(() => {
            element.style.animation = '';
            this.activeShakes.delete(element);
        }, 500);
        
        this.activeShakes.set(element, timeout);
    }
    
    // دوال مساعدة للاهتزاز لأنواع مختلفة من العناصر
    shakeInput(inputElement) {
        this.shakeElement(inputElement, 'medium');
        inputElement.style.borderColor = '#f56565';
        setTimeout(() => {
            inputElement.style.borderColor = '';
        }, 500);
    }
    
    shakeButton(buttonElement) {
        this.shakeElement(buttonElement, 'low');
    }
    
    shakeCard(cardElement) {
        this.shakeElement(cardElement, 'medium');
    }
}

// ============================================================
// 6. نظام التأثيرات المتقدمة عند التحويم (Advanced Hover Effects)
// ============================================================

class AdvancedHoverSystem {
    constructor() {
        this.init();
    }
    
    init() {
        // تأثير الزجاج المتقدم
        document.querySelectorAll('.glass').forEach(el => {
            el.addEventListener('mouseenter', (e) => {
                el.style.backdropFilter = 'blur(20px) saturate(200%)';
                el.style.transition = 'all 0.3s ease';
            });
            el.addEventListener('mouseleave', () => {
                el.style.backdropFilter = 'blur(16px) saturate(180%)';
            });
        });
        
        // تأثير التوهج عند التحويم
        document.querySelectorAll('.btn, .tab, .quick-btn').forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.style.transform = 'translateY(-2px) scale(1.02)';
                el.style.boxShadow = '0 0 20px rgba(79, 209, 197, 0.4)';
            });
            el.addEventListener('mouseleave', () => {
                el.style.transform = '';
                el.style.boxShadow = '';
            });
        });
        
        // تأثير الخطوط الهولوغرافية عند التحويم
        document.querySelectorAll('.panel, .metric-card').forEach(el => {
            el.addEventListener('mouseenter', () => {
                el.classList.add('holo-glow');
            });
            el.addEventListener('mouseleave', () => {
                el.classList.remove('holo-glow');
            });
        });
    }
}

// ============================================================
// 7. دوال عامة للاستخدام
// ============================================================

// نظام الجسيمات
let particleSystem = null;

// نظام التموجات السائلة
let rippleSystem = null;

// نظام الحركة الدقيقة
let microMotionSystem = null;

// نظام الوميض الذكي
let smartBlinkSystem = null;

// نظام الاهتزاز
let errorShakeSystem = null;

// نظام التحويم المتقدم
let advancedHoverSystem = null;

// ============================================================
// 8. تصدير الدوال للاستخدام الخارجي
// ============================================================

window.SovereignAnimations = {
    // جسيمات
    initParticles: () => {
        if (!particleSystem) {
            particleSystem = new SovereignParticleSystem();
        }
        return particleSystem;
    },
    stopParticles: () => {
        if (particleSystem) {
            particleSystem.stop();
        }
    },
    
    // تموجات سائلة
    createRipple: (x, y) => {
        if (rippleSystem) {
            rippleSystem.createRipple(x, y);
        }
    },
    
    // اهتزاز
    shakeElement: (element, intensity) => {
        if (errorShakeSystem) {
            errorShakeSystem.shakeElement(element, intensity);
        }
    },
    shakeInput: (input) => {
        if (errorShakeSystem) {
            errorShakeSystem.shakeInput(input);
        }
    },
    
    // نبض
    addPulse: (element) => {
        if (element) {
            element.classList.add('pulse-active');
            setTimeout(() => element.classList.remove('pulse-active'), 400);
        }
    },
    
    // تحديث الحركة الدقيقة (بعد إضافة عناصر جديدة)
    refreshMicroMotion: () => {
        if (microMotionSystem) {
            microMotionSystem.refresh();
        }
    }
};

// ============================================================
// 9. التهيئة التلقائية
// ============================================================

function initAnimations() {
    // بدء الجسيمات بعد تحميل الصفحة
    setTimeout(() => {
        particleSystem = new SovereignParticleSystem();
    }, 100);
    
    // بدء التموجات السائلة
    rippleSystem = new LiquidRippleSystem();
    
    // بدء الحركة الدقيقة (لأجهزة الكمبيوتر فقط)
    microMotionSystem = new MicroMotionSystem();
    
    // بدء الوميض الذكي
    smartBlinkSystem = new SmartBlinkSystem();
    
    // بدء الاهتزاز
    errorShakeSystem = new ErrorShakeSystem();
    
    // بدء التحويم المتقدم
    advancedHoverSystem = new AdvancedHoverSystem();
    
    console.log('✨ Sovereign Animations: جميع التأثيرات تعمل');
}

// تشغيل التهيئة عند اكتمال تحميل الصفحة
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnimations);
} else {
    initAnimations();
}
