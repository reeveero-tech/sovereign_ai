/* ============================================================
   Sovereign AI — websocket.js
   الإصدار: 3.0.0 - قناة الاتصال الحي بين الواجهة ومساحة العمل
   ============================================================
   
   هذا الملف مسؤول عن:
   - فتح وإغلاق اتصال WebSocket
   - إعادة الاتصال التلقائي عند الانقطاع
   - إرسال أوامر السيد لحظياً
   - إرسال رسائل الحوار فوراً
   - استقبال ردود مساحة العمل في الوقت الفعلي
   - استقبال القرارات والاقتراحات
   - استقبال تحديثات الحالة (الدورات، المقاييس)
   - تحديث الواجهة مباشرة بدون إعادة تحميل
   - عرض حالة الاتصال بشكل مرئي
   - تسجيل الأحداث في سجل النظام
   - إدارة حالة الاتصال (ping/pong, heartbeat)
   
   ============================================================ */

// ============================================================
// 1. إعدادات WebSocket
// ============================================================

const WS_CONFIG = {
    // عنوان WebSocket (يتكيف تلقائياً مع بيئة التشغيل)
    URL: (() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/sovereign`;
    })(),
    
    // إعدادات إعادة الاتصال
    RECONNECT: {
        enabled: true,
        initialDelay: 1000,      // 1 ثانية
        maxDelay: 30000,         // 30 ثانية كحد أقصى
        maxAttempts: 10,         // الحد الأقصى لمحاولات إعادة الاتصال
        backoffFactor: 1.5       // عامل التضاعف (exponential backoff)
    },
    
    // إعدادات القلب النابض (Heartbeat)
    HEARTBEAT: {
        enabled: true,
        interval: 15000,         // 15 ثانية
        timeout: 5000            // 5 ثواني
    },
    
    // إعدادات إعادة الإرسال (Retry)
    RETRY: {
        enabled: true,
        maxRetries: 3,
        delay: 1000
    },
    
    // المهلة (Timeout)
    connectionTimeout: 10000,    // 10 ثواني
    messageTimeout: 30000        // 30 ثانية للرد
};

// ============================================================
// 2. متغيرات الحالة
// ============================================================

let ws = null;                      // كائن WebSocket
let reconnectTimer = null;          // مؤقت إعادة الاتصال
let reconnectAttempts = 0;          // عدد محاولات إعادة الاتصال
let heartbeatInterval = null;       // مؤقت القلب النابض
let connectionTimeoutTimer = null;  // مؤقت مهلة الاتصال
let pendingMessages = [];            // رسائل معلقة لإعادة الإرسال
let messageCallbacks = new Map();    // ردود نداء للرسائل المرسلة

// حالة الاتصال
let connectionState = {
    isConnected: false,
    isConnecting: false,
    lastConnected: null,
    lastDisconnected: null,
    lastError: null
};

// ============================================================
// 3. عناصر DOM للتحديث
// ============================================================

const websocketStatusChip = document.getElementById('ws-status-chip');
const wsConnectButton = document.getElementById('btn-ws-connect');
const wsDisconnectButton = document.getElementById('btn-ws-disconnect');

// ============================================================
// 4. دوال مساعدة
// ============================================================

function log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    console.log(`[WebSocket ${timestamp}] ${message}`);
    
    // إضافة إلى سجل الأحداث إن أمكن
    if (typeof addHistoryEvent !== 'undefined') {
        addHistoryEvent(level, `[WebSocket] ${message}`);
    }
}

function updateConnectionUI(isConnected) {
    connectionState.isConnected = isConnected;
    
    if (websocketStatusChip) {
        if (isConnected) {
            websocketStatusChip.innerHTML = '<i class="fas fa-circle"></i> متصل';
            websocketStatusChip.classList.add('online');
            websocketStatusChip.classList.remove('offline');
            websocketStatusChip.classList.remove('connecting');
        } else if (connectionState.isConnecting) {
            websocketStatusChip.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> جاري الاتصال...';
            websocketStatusChip.classList.add('connecting');
            websocketStatusChip.classList.remove('online');
            websocketStatusChip.classList.remove('offline');
        } else {
            websocketStatusChip.innerHTML = '<i class="fas fa-circle"></i> غير متصل';
            websocketStatusChip.classList.add('offline');
            websocketStatusChip.classList.remove('online');
            websocketStatusChip.classList.remove('connecting');
        }
    }
    
    // تحديث الأزرار
    if (wsConnectButton) wsConnectButton.disabled = isConnected;
    if (wsDisconnectButton) wsDisconnectButton.disabled = !isConnected;
}

// ============================================================
// 5. إعادة الاتصال التلقائي (Exponential Backoff)
// ============================================================

function scheduleReconnect() {
    if (!WS_CONFIG.RECONNECT.enabled) return;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    
    if (reconnectAttempts >= WS_CONFIG.RECONNECT.maxAttempts) {
        log('تم الوصول إلى الحد الأقصى لمحاولات إعادة الاتصال', 'warning');
        updateConnectionUI(false);
        return;
    }
    
    let delay = WS_CONFIG.RECONNECT.initialDelay * Math.pow(WS_CONFIG.RECONNECT.backoffFactor, reconnectAttempts);
    delay = Math.min(delay, WS_CONFIG.RECONNECT.maxDelay);
    
    reconnectAttempts++;
    
    log(`محاولة إعادة الاتصال ${reconnectAttempts}/${WS_CONFIG.RECONNECT.maxAttempts} بعد ${delay}ms`, 'info');
    
    reconnectTimer = setTimeout(() => {
        log('جاري إعادة الاتصال...', 'info');
        connectWebSocket(true);
    }, delay);
}

function cancelReconnect() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
}

// ============================================================
// 6. نظام القلب النابض (Heartbeat - Keep Alive)
// ============================================================

function startHeartbeat() {
    if (!WS_CONFIG.HEARTBEAT.enabled) return;
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    
    let lastPong = Date.now();
    let missedPongs = 0;
    
    // استقبال pong من الخادم
    const handlePong = () => {
        lastPong = Date.now();
        missedPongs = 0;
    };
    
    window.addEventListener('beforeunload', () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'goodbye', timestamp: Date.now() }));
        }
    });
    
    heartbeatInterval = setInterval(() => {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const now = Date.now();
        
        // التحقق من عدم استلام pong لفترة طويلة
        if (now - lastPong > WS_CONFIG.HEARTBEAT.interval * 2) {
            missedPongs++;
            log(`فقدان pong (${missedPongs})`, 'warning');
            
            if (missedPongs >= 3) {
                log('فقدان الاتصال بسبب انقطاع القلب النابض', 'error');
                ws.close();
                return;
            }
        }
        
        // إرسال ping
        try {
            ws.send(JSON.stringify({
                type: 'ping',
                timestamp: now
            }));
        } catch (e) {
            log(`فشل إرسال ping: ${e.message}`, 'error');
        }
    }, WS_CONFIG.HEARTBEAT.interval);
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

// ============================================================
// 7. إعادة إرسال الرسائل المعلقة (Retry Mechanism)
// ============================================================

function queueMessage(type, payload, callback = null) {
    const message = {
        id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`,
        type: type,
        payload: payload,
        timestamp: Date.now(),
        retries: 0,
        callback: callback
    };
    
    pendingMessages.push(message);
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        flushPendingMessages();
    }
}

function flushPendingMessages() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    const toSend = [...pendingMessages];
    pendingMessages = [];
    
    for (const msg of toSend) {
        try {
            ws.send(JSON.stringify({
                id: msg.id,
                type: msg.type,
                payload: msg.payload,
                timestamp: msg.timestamp
            }));
            
            if (msg.callback) {
                messageCallbacks.set(msg.id, msg.callback);
            }
            
            log(`إرسال رسالة معلقة: ${msg.type}`, 'debug');
        } catch (e) {
            log(`فشل إرسال رسالة معلقة: ${e.message}`, 'error');
            
            if (WS_CONFIG.RETRY.enabled && msg.retries < WS_CONFIG.RETRY.maxRetries) {
                msg.retries++;
                setTimeout(() => {
                    pendingMessages.push(msg);
                    flushPendingMessages();
                }, WS_CONFIG.RETRY.delay * Math.pow(2, msg.retries));
            } else {
                if (msg.callback) {
                    msg.callback(null, new Error('فشل إرسال الرسالة بعد عدة محاولات'));
                }
            }
        }
    }
}

// ============================================================
// 8. معالجة الرسائل الواردة
// ============================================================

function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        const { id, type, payload, timestamp } = data;
        
        log(`استلام رسالة: ${type}`, 'debug');
        
        // معالجة ردود النداء (Callbacks)
        if (id && messageCallbacks.has(id)) {
            const callback = messageCallbacks.get(id);
            messageCallbacks.delete(id);
            callback(payload, null);
            return;
        }
        
        // معالجة أنواع الرسائل المختلفة
        switch (type) {
            case 'pong':
                // استجابة القلب النابض
                log('استلام pong', 'debug');
                break;
                
            case 'ai_message':
            case 'chat_reply':
                if (typeof addDialogueMessage !== 'undefined') {
                    addDialogueMessage(payload.text || payload.message, 'المساعد', false);
                }
                break;
                
            case 'decision':
            case 'proposal':
                if (typeof addDecisionMessage !== 'undefined') {
                    addDecisionMessage(payload.text || payload.message, 'ai', payload);
                }
                if (typeof addProposal !== 'undefined' && payload.proposal) {
                    addProposal(payload.proposal);
                }
                break;
                
            case 'state_update':
            case 'metrics_update':
                updateInterfaceFromPayload(payload);
                break;
                
            case 'command_response':
                if (typeof addCommand !== 'undefined') {
                    addCommand(payload.command, payload.result, payload.success);
                }
                break;
                
            case 'notification':
                if (typeof addHistoryEvent !== 'undefined') {
                    addHistoryEvent(payload.level || 'info', payload.message);
                }
                break;
                
            case 'error':
                log(`خطأ من الخادم: ${payload.message}`, 'error');
                if (typeof addHistoryEvent !== 'undefined') {
                    addHistoryEvent('error', `خطأ من الخادم: ${payload.message}`);
                }
                break;
                
            default:
                log(`نوع رسالة غير معروف: ${type}`, 'warning');
        }
        
    } catch (e) {
        log(`خطأ في معالجة الرسالة: ${e.message}`, 'error');
    }
}

function updateInterfaceFromPayload(payload) {
    // تحديث عدد الدورات
    if (payload.cycles !== undefined && typeof metricCycles !== 'undefined') {
        metricCycles.textContent = payload.cycles;
        if (metricCyclesBar) {
            metricCyclesBar.style.width = `${Math.min(100, payload.cycles % 100)}%`;
        }
    }
    
    // تحديث حالة المكونات
    if (payload.components) {
        if (payload.components.memory && typeof metricMemory !== 'undefined') {
            metricMemory.textContent = payload.components.memory === 'healthy' ? 'مستقرة' : 'متدهورة';
        }
        if (payload.components.predictive && typeof metricPredictive !== 'undefined') {
            metricPredictive.textContent = payload.components.predictive === 'healthy' ? 'نشط' : 'متدهور';
        }
        if (payload.components.simulation && typeof metricSimulation !== 'undefined') {
            metricSimulation.textContent = payload.components.simulation === 'healthy' ? 'جاهز' : 'متدهور';
        }
        if (payload.components.sovereign && typeof metricSovereign !== 'undefined') {
            metricSovereign.textContent = payload.components.sovereign === 'healthy' ? 'مستقر' : 'متدهور';
        }
    }
    
    // تحديث طاقة الحقل
    if (payload.field_energy !== undefined && typeof metricFieldEnergy !== 'undefined') {
        metricFieldEnergy.textContent = payload.field_energy.toFixed(2);
    }
    
    // تحديث التماسك
    if (payload.coherence !== undefined && typeof metricCoherence !== 'undefined') {
        metricCoherence.textContent = `${(payload.coherence * 100).toFixed(0)}%`;
    }
    
    // تحديث وضع التشغيل
    if (payload.mode && typeof runtimeMode !== 'undefined') {
        runtimeMode.textContent = `وضع التشغيل: ${payload.mode}`;
    }
    
    // تحديث آخر تحديث
    if (typeof updateLastUpdateTime !== 'undefined') {
        updateLastUpdateTime();
    }
}

// ============================================================
// 9. إرسال الرسائل
// ============================================================

function sendWebSocketMessage(type, payload, callback = null) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        log(`غير متصل، إضافة رسالة ${type} إلى قائمة الانتظار`, 'warning');
        queueMessage(type, payload, callback);
        return false;
    }
    
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
    
    try {
        ws.send(JSON.stringify({
            id: messageId,
            type: type,
            payload: payload,
            timestamp: Date.now()
        }));
        
        if (callback) {
            messageCallbacks.set(messageId, callback);
        }
        
        log(`إرسال رسالة: ${type}`, 'debug');
        return true;
        
    } catch (e) {
        log(`فشل إرسال رسالة: ${e.message}`, 'error');
        
        if (WS_CONFIG.RETRY.enabled) {
            queueMessage(type, payload, callback);
        }
        
        return false;
    }
}

// ============================================================
// 10. دوال مخصصة لإرسال أنواع مختلفة من الرسائل
// ============================================================

function sendSovereignCommandWS(command, parameters = {}, callback = null) {
    return sendWebSocketMessage('sovereign_command', {
        command: command,
        parameters: parameters
    }, callback);
}

function sendChatMessageWS(text, callback = null) {
    return sendWebSocketMessage('chat_message', {
        text: text,
        user_id: 'sovereign',
        is_sovereign: true
    }, callback);
}

function sendRunCycleWS(callback = null) {
    return sendWebSocketMessage('run_cycle', {}, callback);
}

function sendGetStatusWS(callback = null) {
    return sendWebSocketMessage('get_status', {}, callback);
}

function sendGetComponentsWS(callback = null) {
    return sendWebSocketMessage('get_components', {}, callback);
}

function sendResetSystemWS(preserveData = false, callback = null) {
    return sendWebSocketMessage('reset_system', {
        preserve_data: preserveData
    }, callback);
}

// ============================================================
// 11. الاتصال بـ WebSocket
// ============================================================

function connectWebSocket(isReconnect = false) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        log('WebSocket متصل بالفعل', 'info');
        return;
    }
    
    if (ws && ws.readyState === WebSocket.CONNECTING) {
        log('جاري الاتصال بالفعل...', 'info');
        return;
    }
    
    connectionState.isConnecting = true;
    updateConnectionUI(false);
    
    log(`الاتصال بـ ${WS_CONFIG.URL}`, 'info');
    
    // مهلة الاتصال
    if (connectionTimeoutTimer) clearTimeout(connectionTimeoutTimer);
    connectionTimeoutTimer = setTimeout(() => {
        if (ws && ws.readyState === WebSocket.CONNECTING) {
            log('انتهت مهلة الاتصال', 'error');
            ws.close();
        }
    }, WS_CONFIG.connectionTimeout);
    
    try {
        ws = new WebSocket(WS_CONFIG.URL);
        
        ws.onopen = () => {
            log('تم فتح الاتصال بنجاح', 'info');
            connectionState.isConnecting = false;
            connectionState.lastConnected = Date.now();
            
            if (connectionTimeoutTimer) clearTimeout(connectionTimeoutTimer);
            
            updateConnectionUI(true);
            cancelReconnect();
            startHeartbeat();
            flushPendingMessages();
            
            // إرسال رسالة ترحيب
            sendWebSocketMessage('hello', {
                source: 'sovereign_ui',
                version: '3.0.0',
                timestamp: Date.now()
            });
        };
        
        ws.onmessage = handleWebSocketMessage;
        
        ws.onclose = (event) => {
            log(`تم إغلاق الاتصال: كود ${event.code} - ${event.reason}`, 'warning');
            connectionState.isConnecting = false;
            connectionState.lastDisconnected = Date.now();
            connectionState.lastError = event.reason;
            
            updateConnectionUI(false);
            stopHeartbeat();
            
            if (!isReconnect && WS_CONFIG.RECONNECT.enabled) {
                scheduleReconnect();
            }
        };
        
        ws.onerror = (error) => {
            log(`خطأ في WebSocket: ${error}`, 'error');
            connectionState.lastError = 'خطأ في الاتصال';
        };
        
    } catch (e) {
        log(`فشل إنشاء WebSocket: ${e.message}`, 'error');
        connectionState.isConnecting = false;
        updateConnectionUI(false);
        
        if (!isReconnect && WS_CONFIG.RECONNECT.enabled) {
            scheduleReconnect();
        }
    }
}

// ============================================================
// 12. إغلاق الاتصال
// ============================================================

function disconnectWebSocket() {
    if (ws) {
        log('جاري إغلاق الاتصال...', 'info');
        ws.close(1000, 'إغلاق طوعي');
        ws = null;
    }
    
    cancelReconnect();
    stopHeartbeat();
    updateConnectionUI(false);
    connectionState.isConnecting = false;
    
    if (connectionTimeoutTimer) clearTimeout(connectionTimeoutTimer);
}

// ============================================================
// 13. إعادة تعيين WebSocket
// ============================================================

function resetWebSocket() {
    disconnectWebSocket();
    pendingMessages = [];
    messageCallbacks.clear();
    reconnectAttempts = 0;
    setTimeout(() => {
        connectWebSocket();
    }, 500);
}

// ============================================================
// 14. الحصول على حالة الاتصال
// ============================================================

function getConnectionState() {
    return {
        ...connectionState,
        readyState: ws ? ws.readyState : -1,
        readyStateText: ws ? ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][ws.readyState] || 'UNKNOWN' : 'NO_CONNECTION'
    };
}

// ============================================================
// 15. ربط الأزرار بوظائف WebSocket
// ============================================================

if (wsConnectButton) {
    wsConnectButton.addEventListener('click', () => {
        if (!connectionState.isConnected && !connectionState.isConnecting) {
            connectWebSocket();
        }
    });
}

if (wsDisconnectButton) {
    wsDisconnectButton.addEventListener('click', () => {
        if (connectionState.isConnected) {
            disconnectWebSocket();
        }
    });
}

// ربط أزرار الواجهة الموجودة (إن وجدت)
setTimeout(() => {
    if (typeof btnSendSir !== 'undefined' && btnSendSir) {
        const originalClick = btnSendSir.onclick;
        btnSendSir.addEventListener('click', () => {
            const text = document.getElementById('sir-command-input')?.value.trim();
            if (text && connectionState.isConnected) {
                sendSovereignCommandWS(text);
            }
        });
    }
    
    if (typeof btnSendChat !== 'undefined' && btnSendChat) {
        btnSendChat.addEventListener('click', () => {
            const text = document.getElementById('chat-input')?.value.trim();
            if (text && connectionState.isConnected) {
                sendChatMessageWS(text);
            }
        });
    }
    
    if (typeof btnRunCycle !== 'undefined' && btnRunCycle) {
        btnRunCycle.addEventListener('click', () => {
            if (connectionState.isConnected) {
                sendRunCycleWS();
            }
        });
    }
}, 500);

// ============================================================
// 16. الاتصال التلقائي عند تحميل الصفحة
// ============================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            if (!connectionState.isConnected && !connectionState.isConnecting) {
                connectWebSocket();
            }
        }, 1000);
    });
} else {
    setTimeout(() => {
        if (!connectionState.isConnected && !connectionState.isConnecting) {
            connectWebSocket();
        }
    }, 1000);
}

// ============================================================
// 17. دوال عامة للاستخدام من وحدات أخرى
// ============================================================

window.SovereignWebSocket = {
    connect: connectWebSocket,
    disconnect: disconnectWebSocket,
    reset: resetWebSocket,
    send: sendWebSocketMessage,
    sendCommand: sendSovereignCommandWS,
    sendChat: sendChatMessageWS,
    sendRunCycle: sendRunCycleWS,
    getState: getConnectionState,
    isConnected: () => connectionState.isConnected
};

// ============================================================
// 18. تصدير للاستخدام في وحدات أخرى (CommonJS/ES6)
// ============================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        connectWebSocket,
        disconnectWebSocket,
        resetWebSocket,
        sendWebSocketMessage,
        sendSovereignCommandWS,
        sendChatMessageWS,
        sendRunCycleWS,
        getConnectionState
    };
}
