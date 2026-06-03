/* ============================================================
   Sovereign AI — runtime-execution-scheduler.js
   الإصدار: 8.4.0 (Runtime Flow Stabilization Kernel with Pacing Policies)
   
   مجدول التنفيذ السيادي - إدارة وتنسيق تنفيذ المهام
   
   الوظيفة:
     - إدارة طوابير التنفيذ مع Aging Mechanism (منع Starvation)
     - جدولة المهام حسب الأولوية الديناميكية
     - التحكم في التنفيذ المتزامن
     - تتبع دورة حياة المهام مع Retention Policy
     - توفير Telemetry للتنفيذ
     - Execution Lineage Tracking (parent-child relationships)
     - ✅ Runtime Pacing Policies (عبر runtime-pacing.js)
   
   التقسيم المستقبلي (Runtime Execution Core):
     - QueueManager (إدارة الطوابير مع Aging)
     - LifecycleEngine (إدارة حالات المهام)
     - RetryEngine (معالجة الفشل وإعادة المحاولة)
     - ConcurrencyController (التحكم بالتزامن)
     - PacingController (التحكم في تدفق التنفيذ)
     - TelemetryProfiler (القياس والإحصاءات)
     - ExecutionCoordinator (التنسيق العام)
   
   المرحلة القادمة (Runtime Execution Pacing Policies):
     - Priority-Aware Pacing
     - Critical Task Bypass
     - Degraded Pacing Modes
     - Adaptive Draining
     - Queue Stabilization Strategies
   ============================================================ */

class SovereignRuntimeExecutionScheduler {

    constructor() {

        this.queue = [];

        this.processing = false;

        this.maxConcurrent = 5;

        this.activeTasks = 0;

        // Runtime Pacing (Flow Control) - Global fallback
        this.executionDelay = 0;
        this.minExecutionDelay = 0;
        this.maxExecutionDelay = 5000;
        this.pacingEnabled = true;

        // Task Registry with Lifecycle Tracking
        this.tasks = new Map();

        // Retention Policy
        this.maxStoredTasks = 1000;
        this.cleanupInterval = null;

        // Aging parameters (prevent starvation)
        this.agingFactor = 0.5;
        this.agingEnabled = true;

        // Debug mode
        this.debugMode = false;

        // Telemetry counters
        this.telemetry = {
            tasksScheduled: 0,
            tasksCompleted: 0,
            tasksFailed: 0,
            tasksCanceled: 0,
            tasksExpired: 0,
            totalExecutionTime: 0,
            averageExecutionTime: 0,
            maxQueueSize: 0,
            totalPacingDelay: 0,
            pacingDelaysCount: 0,
            pacingBypassed: 0
        };

        console.log(
            '⏱ Runtime Execution Scheduler Initialized (Pacing Policies Ready)'
        );

        this.init();
    }

    /* ========================================================
       HELPER: Get Pacing Manager (من runtime-pacing.js)
    ======================================================== */
    getPacingManager() {
        return window.SOVEREIGN_ACCESS?.legacy?.('pacing') ||
               window.SOVEREIGN_PACING;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.publishReady();
        this.startCleanupInterval();
    }

    /* ========================================================
       SET DEBUG MODE
    ======================================================== */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        console.log(`🐛 Scheduler debug mode: ${enabled ? 'ON' : 'OFF'}`);
    }

    /* ========================================================
       PACING CONTROL APIS (Global Fallback)
    ======================================================== */
    setExecutionDelay(delayMs) {
        if (!this.pacingEnabled) {
            console.log('⏸️ Pacing is disabled, ignoring setExecutionDelay');
            return false;
        }
        
        if (typeof delayMs !== 'number' || isNaN(delayMs)) {
            console.warn('⚠️ Invalid execution delay value:', delayMs);
            return false;
        }
        
        const newDelay = Math.min(
            this.maxExecutionDelay,
            Math.max(this.minExecutionDelay, delayMs)
        );
        
        const oldDelay = this.executionDelay;
        this.executionDelay = newDelay;
        
        console.log(`⏱️ Global execution pacing set to: ${this.executionDelay}ms (was ${oldDelay}ms)`);
        
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:pacing:changed', {
            oldDelay,
            newDelay: this.executionDelay,
            source: 'backpressure-engine',
            timestamp: Date.now()
        });
        
        return true;
    }

    getExecutionDelay() {
        return this.executionDelay;
    }

    clearExecutionDelay() {
        const oldDelay = this.executionDelay;
        this.executionDelay = 0;
        console.log(`⏱️ Global execution pacing cleared (was ${oldDelay}ms)`);
        
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:pacing:cleared', {
            oldDelay,
            timestamp: Date.now()
        });
        
        return true;
    }

    enablePacing(enabled) {
        this.pacingEnabled = enabled;
        if (!enabled) {
            this.executionDelay = 0;
        }
        console.log(`⏱️ Pacing ${enabled ? 'enabled' : 'disabled'}`);
        return true;
    }

    setPacingLimits(minDelay, maxDelay) {
        if (typeof minDelay !== 'number' || minDelay < 0) {
            console.warn('⚠️ Invalid min delay');
            return false;
        }
        if (typeof maxDelay !== 'number' || maxDelay < minDelay) {
            console.warn('⚠️ Invalid max delay (must be >= min delay)');
            return false;
        }
        
        this.minExecutionDelay = minDelay;
        this.maxExecutionDelay = maxDelay;
        this.executionDelay = Math.min(maxDelay, Math.max(minDelay, this.executionDelay));
        
        console.log(`⏱️ Pacing limits updated: min=${minDelay}ms, max=${maxDelay}ms`);
        return true;
    }

    /* ========================================================
       CLEANUP INTERVAL (Retention Policy)
    ======================================================== */
    startCleanupInterval() {
        this.cleanupInterval = setInterval(() => {
            this.cleanupCompletedTasks();
        }, 60000);
    }

    cleanupCompletedTasks() {
        const terminalStates = ['completed', 'failed', 'canceled'];
        const terminalTasks = [...this.tasks.entries()]
            .filter(([_, task]) => terminalStates.includes(task.state))
            .sort((a, b) => (a[1].completedAt || 0) - (b[1].completedAt || 0));
        
        if (terminalTasks.length > this.maxStoredTasks) {
            const toRemove = terminalTasks.length - this.maxStoredTasks;
            for (let i = 0; i < toRemove; i++) {
                this.tasks.delete(terminalTasks[i][0]);
                this.telemetry.tasksExpired++;
            }
            console.log(`🧹 Cleaned up ${toRemove} old tasks (retention policy)`);
        }
    }

    /* ========================================================
       AGING MECHANISM (منع Starvation)
    ======================================================== */
    calculateEffectivePriority(item) {
        if (!this.agingEnabled) {
            return item.priority;
        }
        
        const waitingTimeMs = Date.now() - (item.createdAt || Date.now());
        const waitingReduction = waitingTimeMs * this.agingFactor / 1000;
        return Math.max(0, item.priority - waitingReduction);
    }

    sortQueue() {
        this.queue.sort((a, b) => {
            const effectiveA = this.calculateEffectivePriority(a);
            const effectiveB = this.calculateEffectivePriority(b);
            return effectiveA - effectiveB;
        });
        
        if (this.queue.length > this.telemetry.maxQueueSize) {
            this.telemetry.maxQueueSize = this.queue.length;
        }
    }

    /* ========================================================
       SCHEDULE (جدولة مهمة جديدة)
    ======================================================== */
    schedule({ 
        id = crypto.randomUUID(), 
        priority = 10, 
        task, 
        metadata = {},
        retryCount = 0,
        parentTaskId = null,
        bypassPacing = false
    }) {
        if (typeof task !== 'function') {
            console.warn('⚠️ Invalid Scheduled Task');
            return false;
        }

        const taskItem = {
            id,
            priority,
            task,
            metadata,
            state: 'queued',
            createdAt: Date.now(),
            retriesLeft: retryCount,
            retriesUsed: 0,
            parentTaskId,
            bypassPacing
        };

        this.queue.push(taskItem);
        
        this.tasks.set(id, {
            ...taskItem,
            startedAt: null,
            completedAt: null,
            error: null,
            executionChain: parentTaskId ? [parentTaskId, id] : [id]
        });

        this.sortQueue();
        this.telemetry.tasksScheduled++;

        console.log(`⏱ Task Scheduled: ${id} (Priority: ${priority})${parentTaskId ? ` (Parent: ${parentTaskId})` : ''}${bypassPacing ? ' [PACING BYPASS]' : ''}`);

        this.processQueue();

        return id;
    }

    /* ========================================================
       PROCESS QUEUE (مع Pacing Policies)
       
       ✅ يستخدم runtime-pacing.js لتأخير مخصص حسب القناة
    ======================================================== */
    async processQueue() {
        if (this.processing) {
            return;
        }

        this.processing = true;

        while (this.queue.length > 0 && this.activeTasks < this.maxConcurrent) {
            this.sortQueue();
            
            const item = this.queue.shift();
            
            if (!item) {
                continue;
            }

            // ============================================
            // Runtime Pacing Policies (عبر runtime-pacing.js)
            // ============================================
            if (this.pacingEnabled) {
                const pacing = this.getPacingManager();
                
                // الحصول على القناة من metadata (إذا كانت موجودة)
                const channel = item.metadata?.channel;
                
                // التحقق مما إذا كانت المهمة حرجة ويجب تجاوز التأخير
                const bypass = pacing?.shouldBypass?.(channel) || item.bypassPacing || false;
                
                // الحصول على التأخير (مخصص حسب القناة أو fallback إلى التأخير العام)
                const delay = pacing?.getDelay?.(channel) ?? this.executionDelay;
                
                if (!bypass && delay > 0) {
                    const pacingStart = Date.now();
                    await new Promise(resolve => setTimeout(resolve, delay));
                    const pacingDelay = Date.now() - pacingStart;
                    
                    this.telemetry.totalPacingDelay += pacingDelay;
                    this.telemetry.pacingDelaysCount++;
                    
                    if (this.debugMode || this.telemetry.pacingDelaysCount % 10 === 0) {
                        console.log(`⏱️ Pacing applied: ${pacingDelay}ms (channel: ${channel || 'default'}, delay: ${delay}ms, avg: ${(this.telemetry.totalPacingDelay / this.telemetry.pacingDelaysCount).toFixed(2)}ms)`);
                    }
                } else if (bypass && this.debugMode) {
                    this.telemetry.pacingBypassed++;
                    console.log(`⏩ Pacing bypassed for task: ${item.id} (channel: ${channel || 'default'})`);
                }
            }

            const taskRecord = this.tasks.get(item.id);
            if (taskRecord) {
                taskRecord.state = 'running';
                taskRecord.startedAt = Date.now();
                this.tasks.set(item.id, taskRecord);
            }

            this.activeTasks++;
            
            this.executeTask(item).finally(() => {
                this.activeTasks--;
                this.processQueue();
            });
        }

        this.processing = false;
    }

    /* ========================================================
       EXECUTE TASK
    ======================================================== */
    async executeTask(item) {
        const startTime = performance.now();
        
        try {
            const result = await item.task();
            
            const duration = performance.now() - startTime;
            
            const taskRecord = this.tasks.get(item.id);
            if (taskRecord) {
                taskRecord.state = 'completed';
                taskRecord.completedAt = Date.now();
                taskRecord.result = result;
                taskRecord.duration = duration;
                this.tasks.set(item.id, taskRecord);
            }
            
            this.telemetry.tasksCompleted++;
            this.telemetry.totalExecutionTime += duration;
            this.telemetry.averageExecutionTime = 
                this.telemetry.totalExecutionTime / this.telemetry.tasksCompleted;
            
            this.publishCompleted(item, duration);
            
        } catch (error) {
            const duration = performance.now() - startTime;
            
            console.error(`⚠️ Scheduled Task Failed: ${item.id}`, error);
            
            if (item.retriesLeft > 0) {
                item.retriesLeft--;
                item.retriesUsed++;
                item.state = 'queued';
                item.createdAt = Date.now();
                
                console.log(`🔄 Retrying task: ${item.id} (${item.retriesUsed}/${item.retriesUsed + item.retriesLeft})`);
                
                const taskRecord = this.tasks.get(item.id);
                if (taskRecord) {
                    taskRecord.state = 'queued';
                    taskRecord.retriesUsed = item.retriesUsed;
                    taskRecord.retriesLeft = item.retriesLeft;
                    taskRecord.lastError = error.message;
                    this.tasks.set(item.id, taskRecord);
                }
                
                this.queue.push(item);
                this.sortQueue();
                this.processQueue();
            } else {
                const taskRecord = this.tasks.get(item.id);
                if (taskRecord) {
                    taskRecord.state = 'failed';
                    taskRecord.completedAt = Date.now();
                    taskRecord.error = error.message;
                    taskRecord.duration = duration;
                    this.tasks.set(item.id, taskRecord);
                }
                
                this.telemetry.tasksFailed++;
                this.publishFailed(item, error);
            }
        }
    }

    /* ========================================================
       CANCEL TASK
    ======================================================== */
    cancelTask(taskId) {
        const queueIndex = this.queue.findIndex(item => item.id === taskId);
        if (queueIndex !== -1) {
            const removed = this.queue.splice(queueIndex, 1)[0];
            
            const taskRecord = this.tasks.get(taskId);
            if (taskRecord) {
                taskRecord.state = 'canceled';
                taskRecord.completedAt = Date.now();
                this.tasks.set(taskId, taskRecord);
            }
            
            this.telemetry.tasksCanceled++;
            console.log(`❌ Task Canceled: ${taskId}`);
            
            this.publishCanceled(removed);
            return true;
        }
        
        const runningTask = this.tasks.get(taskId);
        if (runningTask && runningTask.state === 'running') {
            runningTask.state = 'canceled';
            this.tasks.set(taskId, runningTask);
            console.warn(`⚠️ Task marked for cancellation (already running): ${taskId}`);
            return true;
        }
        
        console.warn(`⚠️ Task not found: ${taskId}`);
        return false;
    }

    /* ========================================================
       CONFIGURATION APIS
    ======================================================== */
    setMaxConcurrent(max) {
        if (typeof max !== 'number' || max < 1) {
            console.warn('⚠️ Invalid maxConcurrent value');
            return false;
        }
        this.maxConcurrent = max;
        console.log(`📊 Max concurrent tasks updated to: ${max}`);
        this.processQueue();
        return true;
    }

    setMaxStoredTasks(max) {
        if (typeof max !== 'number' || max < 100) {
            console.warn('⚠️ Invalid maxStoredTasks value (minimum 100)');
            return false;
        }
        this.maxStoredTasks = max;
        console.log(`📊 Max stored tasks updated to: ${max}`);
        this.cleanupCompletedTasks();
        return true;
    }

    setAgingFactor(factor) {
        if (typeof factor !== 'number' || factor < 0 || factor > 2) {
            console.warn('⚠️ Invalid aging factor (0-2)');
            return false;
        }
        this.agingFactor = factor;
        console.log(`📊 Aging factor updated to: ${factor}`);
        this.sortQueue();
        return true;
    }

    enableAging(enabled) {
        this.agingEnabled = enabled;
        console.log(`📊 Aging ${enabled ? 'enabled' : 'disabled'}`);
        if (enabled) {
            this.sortQueue();
        }
        return true;
    }

    /* ========================================================
       TASK INTROSPECTION APIS
    ======================================================== */
    getTask(taskId) {
        return this.tasks.get(taskId) || null;
    }

    getAllTasks() {
        return [...this.tasks.values()];
    }

    getTasksByState(state) {
        return [...this.tasks.values()].filter(task => task.state === state);
    }

    retryTask(taskId, newPriority = null) {
        const taskRecord = this.tasks.get(taskId);
        if (!taskRecord) {
            console.warn(`⚠️ Task not found: ${taskId}`);
            return false;
        }
        
        if (taskRecord.state !== 'failed') {
            console.warn(`⚠️ Cannot retry task in state: ${taskRecord.state}`);
            return false;
        }
        
        return this.schedule({
            id: crypto.randomUUID(),
            priority: newPriority !== null ? newPriority : taskRecord.priority,
            task: taskRecord.task,
            metadata: { ...taskRecord.metadata, originalTaskId: taskId, isRetry: true },
            retryCount: taskRecord.retriesLeft,
            parentTaskId: taskRecord.parentTaskId || taskId,
            bypassPacing: taskRecord.bypassPacing || false
        });
    }

    /* ========================================================
       QUEUE MANAGEMENT
    ======================================================== */
    clearQueue() {
        const clearedCount = this.queue.length;
        this.queue = [];
        console.log(`🧹 Queue cleared: ${clearedCount} tasks removed`);
        return clearedCount;
    }

    cleanupNow() {
        this.cleanupCompletedTasks();
        console.log('🧹 Manual cleanup completed');
    }

    /* ========================================================
       EVENT PUBLISHERS
    ======================================================== */
    publishCompleted(item, duration) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:task:completed', {
            task: item.id,
            priority: item.priority,
            duration: parseFloat(duration.toFixed(2)),
            parentTaskId: item.parentTaskId || null,
            pacingDelayed: this.executionDelay > 0 && !item.bypassPacing,
            timestamp: Date.now()
        });
    }

    publishFailed(item, error) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:task:failed', {
            task: item.id,
            priority: item.priority,
            error: error.message,
            retriesUsed: item.retriesUsed,
            parentTaskId: item.parentTaskId || null,
            timestamp: Date.now()
        });
    }

    publishCanceled(item) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:task:canceled', {
            task: item.id,
            priority: item.priority,
            parentTaskId: item.parentTaskId || null,
            timestamp: Date.now()
        });
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:ready', {
            maxConcurrent: this.maxConcurrent,
            maxStoredTasks: this.maxStoredTasks,
            agingEnabled: this.agingEnabled,
            agingFactor: this.agingFactor,
            pacingEnabled: this.pacingEnabled,
            executionDelay: this.executionDelay,
            version: '8.4.0',
            timestamp: Date.now()
        });
    }

    /* ========================================================
       STATUS (مع Pacing Policies Telemetry)
    ======================================================== */
    getStatus() {
        const tasksByState = {
            queued: this.getTasksByState('queued').length,
            running: this.getTasksByState('running').length,
            completed: this.getTasksByState('completed').length,
            failed: this.getTasksByState('failed').length,
            canceled: this.getTasksByState('canceled').length
        };
        
        const waitingTasks = this.queue.map(item => ({
            id: item.id,
            priority: item.priority,
            effectivePriority: this.calculateEffectivePriority(item),
            waitingTimeMs: Date.now() - (item.createdAt || Date.now()),
            bypassPacing: item.bypassPacing
        }));
        
        const pacingManager = this.getPacingManager();
        const pacingPolicies = pacingManager?.getAllPolicies?.() || {};
        
        return {
            queued: this.queue.length,
            active: this.activeTasks,
            maxConcurrent: this.maxConcurrent,
            processing: this.processing,
            tasksByState,
            pacing: {
                enabled: this.pacingEnabled,
                globalDelayMs: this.executionDelay,
                minDelayMs: this.minExecutionDelay,
                maxDelayMs: this.maxExecutionDelay,
                policies: pacingPolicies,
                avgPacingDelayMs: this.telemetry.pacingDelaysCount > 0 
                    ? parseFloat((this.telemetry.totalPacingDelay / this.telemetry.pacingDelaysCount).toFixed(2))
                    : 0,
                totalPacingDelayMs: parseFloat(this.telemetry.totalPacingDelay.toFixed(2)),
                bypassedCount: this.telemetry.pacingBypassed
            },
            aging: {
                enabled: this.agingEnabled,
                factor: this.agingFactor,
                waitingTasks: waitingTasks.slice(0, 5)
            },
            retention: {
                maxStoredTasks: this.maxStoredTasks,
                currentStored: this.tasks.size,
                expiredCount: this.telemetry.tasksExpired
            },
            telemetry: {
                tasksScheduled: this.telemetry.tasksScheduled,
                tasksCompleted: this.telemetry.tasksCompleted,
                tasksFailed: this.telemetry.tasksFailed,
                tasksCanceled: this.telemetry.tasksCanceled,
                averageExecutionTimeMs: parseFloat(this.telemetry.averageExecutionTime.toFixed(2)),
                totalExecutionTimeMs: parseFloat(this.telemetry.totalExecutionTime.toFixed(2)),
                maxQueueSize: this.telemetry.maxQueueSize
            },
            timestamp: Date.now()
        };
    }

    /* ========================================================
       SHUTDOWN
    ======================================================== */
    shutdown() {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }
        console.log('🛑 Execution Scheduler shut down');
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
============================================================ */

const sovereignScheduler = new SovereignRuntimeExecutionScheduler();

window.SOVEREIGN_EXECUTION_SCHEDULER = sovereignScheduler;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('execution-scheduler', sovereignScheduler);
    console.log('✅ Execution Scheduler registered in Unified Registry');
}

window.SOVEREIGN_EVENTS?.emit('scheduler:ready', {
    timestamp: Date.now(),
    status: sovereignScheduler.getStatus()
});
