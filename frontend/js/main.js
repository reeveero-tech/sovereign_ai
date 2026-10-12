/* ============================================================
   Sovereign AI — main.js
   الإصدار: 3.0.0 - العقل التشغيلي للواجهة السيادية
   ============================================================
   
   هذا الملف مسؤول عن:
   - إدارة التبويبات
   - إدارة مجموعات الرسائل (كل 15 رسالة)
   - إرسال أوامر السيد
   - إرسال رسائل الحوار
   - استقبال ردود الذكاء السيادي
   - تحديث لوحة المراقبة
   - تشغيل دورة سيادية
   - عرض السجل
   - التحكم في الطي
   - التحكم في التحديث الحي
   - ربط الواجهة بالـ API و WebSocket
   
   ============================================================ */

// ============================================================
// 1. إعدادات عامة
// ============================================================

const CONFIG = {
    // إعدادات API
    API_BASE_URL: window.location.origin,
    API_ENDPOINTS: {
        CHAT: '/chat',
        SOVEREIGN_COMMAND: '/sovereign/command',
        STATUS: '/status',
        HEALTH: '/health',
        COMPONENTS: '/components',
        HISTORY: '/orchestrator/cycle'
    },
    
    // إعدادات WebSocket
    WS_URL: `ws://${window.location.host}/ws/sovereign`,
    
    // إعدادات الواجهة
    GROUP_SIZE: 15,          // عدد الرسائل في كل مجموعة (تغير من 3 إلى 15)
    AUTO_REFRESH_INTERVAL: 3000,  // 3 ثوانٍ
    MAX_HISTORY: 500,
    
    // مفتاح API (سيتم تحميله من الخادم)
    API_KEY: null,
    
    // الحالة
    isConnected: false,
    ws: null,
    refreshInterval: null
};

// ============================================================
// 2. عناصر DOM
// ============================================================

// التبويبات
const tabs = document.querySelectorAll('.tab');
const tabContents = {
    monitor: document.getElementById('tab-monitor'),
    dialogue: document.getElementById('tab-dialogue'),
    decisions: document.getElementById('tab-decisions'),
    proposals: document.getElementById('tab-proposals'),
    commands: document.getElementById('tab-commands'),
    history: document.getElementById('tab-history')
};

// مناطق العرض
const dialogueContainer = document.getElementById('dialogue-groups');
const decisionsContainer = document.getElementById('decisions-groups');
const proposalsContainer = document.getElementById('proposals-list');
const commandsContainer = document.getElementById('commands-list');
const historyContainer = document.getElementById('history-list');

// المدخلات
const sirInput = document.getElementById('sir-command-input');
const sirCount = document.getElementById('sir-command-count');
const btnSendSir = document.getElementById('btn-send-sir-command');

const chatInput = document.getElementById('chat-input');
const chatCount = document.getElementById('chat-input-count');
const btnSendChat = document.getElementById('btn-send-chat');

// الأزرار
const btnRunCycle = document.getElementById('btn-run-cycle');
const btnViewHistory = document.getElementById('btn-view-history');
const btnResetSystem = document.getElementById('btn-reset-system');
const btnGetStatus = document.getElementById('btn-get-status');
const btnGetComponents = document.getElementById('btn-get-components');
const btnClearCommands = document.getElementById('btn-clear-commands');
const btnClearHistory = document.getElementById('btn-clear-history-btn');
const btnExportData = document.getElementById('btn-export-data');
const btnRefreshProposals = document.getElementById('btn-refresh-proposals');

// التبديلات
const toggleAutoGroup = document.getElementById('toggle-auto-group');
const toggleLiveRefresh = document.getElementById('toggle-live-refresh');
const toggleSound = document.getElementById('toggle-sound');
const toggleHolographic = document.getElementById('toggle-holographic');

// الاتصالات
const btnWsConnect = document.getElementById('btn-ws-connect');
const btnWsDisconnect = document.getElementById('btn-ws-disconnect');
const wsStatusChip = document.getElementById('ws-status-chip');

// المقاييس
const metricCycles = document.getElementById('metric-cycles');
const metricCyclesBar = document.getElementById('metric-cycles-bar');
const metricError = document.getElementById('metric-error');
const metricMemory = document.getElementById('metric-memory');
const metricPredictive = document.getElementById('metric-predictive');
const metricSimulation = document.getElementById('metric-simulation');
const metricSovereign = document.getElementById('metric-sovereign');
const metricFieldEnergy = document.getElementById('metric-field-energy');
const metricCoherence = document.getElementById('metric-coherence');

// مؤشرات الحالة
const statusConnection = document.getElementById('status-connection');
const runtimeMode = document.getElementById('runtime-mode');
const systemHealth = document.getElementById('systemHealth');
const sessionId = document.getElementById('sessionId');
const uptime = document.getElementById('uptime');
const totalCycles = document.getElementById('totalCycles');
const lastUpdateTime = document.getElementById('last-update-time');

// ============================================================
// 3. هياكل البيانات
// ============================================================

let dialogueMessages = [];      // رسائل المحادثة
let decisionsMessages = [];     // القرارات
let proposalsList = [];         // اقتراحات الذكاء
let commandsList = [];          // أوامر السيد
let historyEvents = [];         // سجل الأحداث
let currentMetrics = {          // المقاييس الحالية
    cycles: 0,
    health: 0,
    fieldEnergy: 0,
    coherence: 0
};

let systemState = {
    mode: 'normal',
    sessionId: null,
    uptime: 0,
    components: {}
};

// ============================================================
// 4. دوال مساعدة
// ============================================================

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('ar-SA');
}

function updateLastUpdateTime() {
    if (lastUpdateTime) {
        lastUpdateTime.textContent = `آخر تحديث: ${formatTime(Date.now())}`;
    }
}

// ============================================================
// 5. إدارة المجموعات (كل 15 رسالة)
// ============================================================

function createGroupElement(title, messages, type = 'dialogue') {
    const group = document.createElement('div');
    group.className = 'group open';
    group.dataset.groupId = `group_${Date.now()}_${Math.random()}`;
    
    // رأس المجموعة
    const header = document.createElement('div');
    header.className = 'group-header glass';
    
    const titleSpan = document.createElement('div');
    titleSpan.className = 'group-title';
    titleSpan.innerHTML = `<i class="fas fa-comments"></i> ${title} <span class="group-count">(${messages.length})</span>`;
    
    const toggleIcon = document.createElement('div');
    toggleIcon.className = 'group-toggle';
    toggleIcon.innerHTML = '<i class="fas fa-chevron-up"></i>';
    
    header.appendChild(titleSpan);
    header.appendChild(toggleIcon);
    
    // جسم المجموعة
    const body = document.createElement('div');
    body.className = 'group-body';
    
    messages.forEach(msg => {
        const messageEl = createMessageElement(msg, type);
        body.appendChild(messageEl);
    });
    
    group.appendChild(header);
    group.appendChild(body);
    
    // حدث الطي
    header.addEventListener('click', () => {
        group.classList.toggle('open');
        toggleIcon.innerHTML = group.classList.contains('open') 
            ? '<i class="fas fa-chevron-up"></i>' 
            : '<i class="fas fa-chevron-down"></i>';
    });
    
    return group;
}

function createMessageElement(msg, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${msg.className || ''}`;
    
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.innerHTML = `
        <span class="message-type">${msg.label || msg.type || 'نظام'}</span>
        <span class="message-time">${msg.time || formatTime(Date.now())}</span>
    `;
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = msg.text || msg.content || msg.message || '';
    
    messageDiv.appendChild(meta);
    messageDiv.appendChild(content);
    
    return messageDiv;
}

function renderGrouped(messages, container, baseTitle, groupSize = CONFIG.GROUP_SIZE, type = 'dialogue') {
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!messages.length) {
        container.innerHTML = '<div class="empty-state"><i class="fas fa-comment-dots"></i><p>لا توجد رسائل بعد</p></div>';
        return;
    }
    
    const shouldGroup = toggleAutoGroup ? toggleAutoGroup.checked : true;
    
    if (!shouldGroup || messages.length <= groupSize) {
        const group = createGroupElement(baseTitle, messages, type);
        container.appendChild(group);
        return;
    }
    
    let index = 0;
    let groupIndex = 1;
    
    while (index < messages.length) {
        const slice = messages.slice(index, index + groupSize);
        const title = `${baseTitle} · المجموعة ${groupIndex}`;
        const group = createGroupElement(title, slice, type);
        container.appendChild(group);
        index += groupSize;
        groupIndex++;
    }
}

// ============================================================
// 6. إدارة الرسائل
// ============================================================

function addDialogueMessage(text, sender, isUser = true) {
    const now = Date.now();
    const message = {
        id: `msg_${now}_${Math.random()}`,
        text: text,
        time: formatTime(now),
        timestamp: now,
        label: isUser ? 'السيد' : 'الذكاء السيادي',
        className: isUser ? 'message-type-user' : 'message-type-ai',
        type: isUser ? 'user' : 'ai'
    };
    
    dialogueMessages.push(message);
    
    // الحفاظ على الحد الأقصى
    if (dialogueMessages.length > CONFIG.MAX_HISTORY) {
        dialogueMessages = dialogueMessages.slice(-CONFIG.MAX_HISTORY);
    }
    
    renderGrouped(dialogueMessages, dialogueContainer, 'المحادثة', CONFIG.GROUP_SIZE, 'dialogue');
    
    // تمرير إلى الأسفل
    if (dialogueContainer) {
        dialogueContainer.scrollTop = dialogueContainer.scrollHeight;
    }
}

function addDecisionMessage(text, type, details = {}) {
    const now = Date.now();
    const typeMap = {
        'approved': { label: 'قرار مقبول', className: 'message-type-approved', icon: '✅' },
        'rejected': { label: 'قرار مرفوض', className: 'message-type-rejected', icon: '❌' },
        'pending': { label: 'قرار معلق', className: 'message-type-pending', icon: '⏳' },
        'ai': { label: 'اقتراح الذكاء', className: 'message-type-ai', icon: '🤖' },
        'system': { label: 'نظام', className: 'message-type-system', icon: '⚙️' }
    };
    
    const meta = typeMap[type] || typeMap['system'];
    
    const message = {
        id: `dec_${now}_${Math.random()}`,
        text: `${meta.icon} ${text}`,
        time: formatTime(now),
        timestamp: now,
        label: meta.label,
        className: meta.className,
        details: details
    };
    
    decisionsMessages.push(message);
    
    if (decisionsMessages.length > CONFIG.MAX_HISTORY) {
        decisionsMessages = decisionsMessages.slice(-CONFIG.MAX_HISTORY);
    }
    
    renderGrouped(decisionsMessages, decisionsContainer, 'القرارات', CONFIG.GROUP_SIZE, 'decisions');
}

function addProposal(proposal) {
    const now = Date.now();
    const proposalItem = {
        id: proposal.id || `prop_${now}_${Math.random()}`,
        title: proposal.title,
        description: proposal.description,
        status: proposal.status || 'pending', // pending, approved, rejected
        confidence: proposal.confidence || 0,
        timestamp: now,
        time: formatTime(now)
    };
    
    proposalsList.unshift(proposalItem);
    
    if (proposalsList.length > 100) {
        proposalsList = proposalsList.slice(0, 100);
    }
    
    renderProposals();
}

function renderProposals() {
    if (!proposalsContainer) return;
    
    if (!proposalsList.length) {
        proposalsContainer.innerHTML = '<div class="empty-state"><i class="fas fa-lightbulb"></i><p>لا توجد اقتراحات حالياً</p></div>';
        return;
    }
    
    proposalsContainer.innerHTML = proposalsList.map(prop => `
        <div class="proposal-card glass" data-proposal-id="${prop.id}">
            <div class="proposal-header">
                <div class="proposal-status ${prop.status}">${getStatusText(prop.status)}</div>
                <div class="proposal-time">${prop.time}</div>
            </div>
            <div class="proposal-title">${escapeHtml(prop.title)}</div>
            <div class="proposal-description">${escapeHtml(prop.description)}</div>
            <div class="proposal-footer">
                <div class="proposal-confidence">الثقة: ${(prop.confidence * 100).toFixed(0)}%</div>
                ${prop.status === 'pending' ? `
                    <div class="proposal-actions">
                        <button class="approve-btn" data-id="${prop.id}"><i class="fas fa-check"></i> قبول</button>
                        <button class="reject-btn" data-id="${prop.id}"><i class="fas fa-times"></i> رفض</button>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // ربط أحداث القبول والرفض
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', () => handleProposalAction(btn.dataset.id, 'approve'));
    });
    document.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', () => handleProposalAction(btn.dataset.id, 'reject'));
    });
}

function getStatusText(status) {
    const statusMap = {
        'pending': '⏳ قيد الانتظار',
        'approved': '✅ مقبول',
        'rejected': '❌ مرفوض'
    };
    return statusMap[status] || status;
}

function handleProposalAction(proposalId, action) {
    const proposal = proposalsList.find(p => p.id === proposalId);
    if (proposal) {
        proposal.status = action === 'approve' ? 'approved' : 'rejected';
        renderProposals();
        addDecisionMessage(`${action === 'approve' ? 'تم قبول' : 'تم رفض'} الاقتراح: ${proposal.title}`, action === 'approve' ? 'approved' : 'rejected');
        
        // إرسال إلى API
        if (CONFIG.API_KEY) {
            sendSovereignCommand('proposal_response', { proposal_id: proposalId, action: action });
        }
    }
}

function addCommand(cmd, result, success = true) {
    const now = Date.now();
    const commandItem = {
        id: `cmd_${now}_${Math.random()}`,
        command: cmd,
        result: result,
        success: success,
        time: formatTime(now),
        timestamp: now
    };
    
    commandsList.unshift(commandItem);
    
    if (commandsList.length > 100) {
        commandsList = commandsList.slice(0, 100);
    }
    
    renderCommands();
}

function renderCommands() {
    if (!commandsContainer) return;
    
    if (!commandsList.length) {
        commandsContainer.innerHTML = '<div class="empty-state"><i class="fas fa-terminal"></i><p>لا توجد أوامر بعد. أرسل أمراً من اللوحة اليمنى.</p></div>';
        return;
    }
    
    commandsContainer.innerHTML = commandsList.map(cmd => `
        <div class="command-item glass">
            <div class="command-header">
                <div class="command-name"><i class="fas fa-terminal"></i> ${escapeHtml(cmd.command)}</div>
                <div class="command-time">${cmd.time}</div>
            </div>
            <div class="command-status ${cmd.success ? 'success' : 'failed'}">${cmd.success ? '✓ تم التنفيذ' : '✗ فشل'}</div>
            <div class="command-details">${escapeHtml(cmd.result)}</div>
        </div>
    `).join('');
}

function addHistoryEvent(level, message, details = {}) {
    const now = Date.now();
    const eventItem = {
        id: `hist_${now}_${Math.random()}`,
        level: level, // info, warning, error
        message: message,
        details: details,
        time: formatTime(now),
        timestamp: now
    };
    
    historyEvents.unshift(eventItem);
    
    if (historyEvents.length > 500) {
        historyEvents = historyEvents.slice(0, 500);
    }
    
    renderHistory();
}

function renderHistory() {
    if (!historyContainer) return;
    
    const searchTerm = document.getElementById('historySearch')?.value.toLowerCase() || '';
    
    let filtered = historyEvents;
    if (searchTerm) {
        filtered = historyEvents.filter(e => e.message.toLowerCase().includes(searchTerm));
    }
    
    if (!filtered.length) {
        historyContainer.innerHTML = '<div class="empty-state"><i class="fas fa-history"></i><p>لا توجد أحداث في السجل</p></div>';
        return;
    }
    
    historyContainer.innerHTML = filtered.map(event => `
        <div class="history-item ${event.level}">
            <div class="history-time">${event.time}</div>
            <div class="history-message">${escapeHtml(event.message)}</div>
            <div class="history-level ${event.level}">${getLevelText(event.level)}</div>
        </div>
    `).join('');
}

function getLevelText(level) {
    const levelMap = {
        'info': 'ℹ️ معلومات',
        'warning': '⚠️ تحذير',
        'error': '❌ خطأ'
    };
    return levelMap[level] || level;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================
// 7. إدارة التبويبات
// ============================================================

function switchTab(tabId) {
    // تحديث التبويبات النشطة
    tabs.forEach(tab => {
        const tabTarget = tab.dataset.tab;
        if (tabTarget === tabId) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    
    // إظهار/إخفاء المحتوى
    Object.keys(tabContents).forEach(key => {
        if (tabContents[key]) {
            tabContents[key].style.display = key === tabId ? 'block' : 'none';
        }
    });
}

tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        if (target) {
            switchTab(target);
        }
    });
});

// ============================================================
// 8. عدادات الحروف
// ============================================================

if (sirInput) {
    sirInput.addEventListener('input', () => {
        if (sirCount) sirCount.textContent = `${sirInput.value.length} حرف`;
    });
}

if (chatInput) {
    chatInput.addEventListener('input', () => {
        if (chatCount) chatCount.textContent = `${chatInput.value.length} حرف`;
    });
}

// ============================================================
// 9. إرسال أوامر السيد (API حقيقي)
// ============================================================

async function sendSovereignCommand(command, params = {}) {
    addHistoryEvent('info', `إرسال أمر سيادي: ${command}`);
    
    if (!CONFIG.API_KEY) {
        addHistoryEvent('warning', 'مفتاح API غير متوفر، تم تنفيذ الأمر محلياً');
        handleLocalCommand(command, params);
        return;
    }
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.SOVEREIGN_COMMAND}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                command: command,
                parameters: params,
                api_key: CONFIG.API_KEY
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addHistoryEvent('info', `تم تنفيذ الأمر ${command} بنجاح`);
            addCommand(command, data.message, true);
            addDecisionMessage(`تم تنفيذ الأمر: ${command}`, 'approved');
            return data;
        } else {
            addHistoryEvent('error', `فشل تنفيذ الأمر ${command}: ${data.message}`);
            addCommand(command, data.message, false);
            return null;
        }
    } catch (error) {
        addHistoryEvent('error', `خطأ في إرسال الأمر: ${error.message}`);
        addCommand(command, error.message, false);
        return null;
    }
}

function handleLocalCommand(command, params) {
    const cmdLower = command.toLowerCase();
    
    switch(cmdLower) {
        case 'status':
            updateMetricsFromSystem();
            addDecisionMessage('تم تحديث حالة النظام', 'approved');
            break;
        case 'reset':
            resetLocalState();
            addDecisionMessage('تم إعادة تهيئة النظام محلياً', 'approved');
            break;
        case 'mode':
            const mode = params.mode || params;
            if (mode) {
                systemState.mode = mode;
                if (runtimeMode) runtimeMode.textContent = `وضع التشغيل: ${mode}`;
                addDecisionMessage(`تم تغيير الوضع إلى ${mode}`, 'approved');
            }
            break;
        default:
            addDecisionMessage(`تم استلام الأمر: ${command}`, 'pending');
            break;
    }
}

function resetLocalState() {
    dialogueMessages = [];
    decisionsMessages = [];
    proposalsList = [];
    commandsList = [];
    historyEvents = [];
    currentMetrics = {
        cycles: 0,
        health: 0,
        fieldEnergy: 0,
        coherence: 0
    };
    
    if (metricCycles) metricCycles.textContent = '0';
    if (metricCyclesBar) metricCyclesBar.style.width = '0%';
    
    renderGrouped(dialogueMessages, dialogueContainer, 'المحادثة', CONFIG.GROUP_SIZE, 'dialogue');
    renderGrouped(decisionsMessages, decisionsContainer, 'القرارات', CONFIG.GROUP_SIZE, 'decisions');
    renderProposals();
    renderCommands();
    renderHistory();
    
    addHistoryEvent('info', 'تم إعادة تهيئة الواجهة محلياً');
}

// ============================================================
// 10. إرسال رسائل الحوار (API حقيقي)
// ============================================================

async function sendChatMessage(text) {
    addDialogueMessage(text, 'السيد', true);
    addHistoryEvent('info', `إرسال رسالة: ${text.substring(0, 50)}...`);
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.CHAT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                user_id: 'sovereign',
                is_sovereign: true
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            addDialogueMessage(data.reply, 'الذكاء السيادي', false);
            addHistoryEvent('info', `رد الذكاء: ${data.reply.substring(0, 50)}...`);
            
            // تحديث المقاييس
            if (data.processing_time_ms) {
                // يمكن استخدام وقت المعالجة في المقاييس
            }
        } else {
            addDialogueMessage('عذراً، حدث خطأ في معالجة رسالتك. يرجى المحاولة مرة أخرى.', 'الذكاء السيادي', false);
            addHistoryEvent('error', `خطأ في معالجة الرسالة: ${data.reply || 'غير معروف'}`);
        }
    } catch (error) {
        addDialogueMessage('عذراً، لا يمكن الاتصال بالخادم. يرجى التحقق من الاتصال.', 'الذكاء السيادي', false);
        addHistoryEvent('error', `فشل الاتصال: ${error.message}`);
    }
}

// ============================================================
// 11. تحديث لوحة المراقبة (API حقيقي)
// ============================================================

async function updateMetrics() {
    if (!toggleLiveRefresh || (toggleLiveRefresh.checked !== false)) {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.STATUS}`);
            const data = await response.json();
            
            if (data.orchestrator) {
                // تحديث المقاييس
                currentMetrics.cycles = data.orchestrator.stats?.total_cycles || 0;
                currentMetrics.health = data.orchestrator.system_health || 0.75;
                
                if (metricCycles) metricCycles.textContent = currentMetrics.cycles;
                if (metricCyclesBar) metricCyclesBar.style.width = `${Math.min(100, currentMetrics.cycles % 100)}%`;
                if (systemHealth) systemHealth.textContent = `${(currentMetrics.health * 100).toFixed(0)}%`;
                
                // تحديث حالة النظام
                systemState.mode = data.orchestrator.mode || 'normal';
                systemState.sessionId = data.orchestrator.session_id;
                systemState.uptime = data.orchestrator.uptime_seconds || 0;
                
                if (runtimeMode) runtimeMode.textContent = `وضع التشغيل: ${systemState.mode}`;
                if (sessionId) sessionId.textContent = systemState.sessionId || '---';
                if (uptime) {
                    const hours = Math.floor(systemState.uptime / 3600);
                    const minutes = Math.floor((systemState.uptime % 3600) / 60);
                    uptime.textContent = `${hours}h ${minutes}m`;
                }
                if (totalCycles) totalCycles.textContent = currentMetrics.cycles;
                
                // تحديث حالة المكونات
                if (data.components) {
                    const components = data.components;
                    let healthy = 0;
                    let degraded = 0;
                    let unhealthy = 0;
                    
                    Object.values(components).forEach(h => {
                        if (h === 'healthy') healthy++;
                        else if (h === 'degraded') degraded++;
                        else unhealthy++;
                    });
                    
                    if (metricMemory) metricMemory.textContent = degraded > 0 ? 'متدهورة' : healthy > 0 ? 'مستقرة' : 'غير معروفة';
                    if (metricPredictive) metricPredictive.textContent = components.predictive_engine === 'healthy' ? 'نشط' : 'متدهور';
                    if (metricSimulation) metricSimulation.textContent = components.simulation_controller === 'healthy' ? 'جاهز' : 'متدهور';
                    if (metricSovereign) metricSovereign.textContent = components.sovereign_controller === 'healthy' ? 'مستقر' : 'متدهور';
                }
            }
            
            updateLastUpdateTime();
        } catch (error) {
            // في حال عدم وجود خادم، نستخدم بيانات محاكاة
            simulateMetricsUpdate();
        }
    }
}

function simulateMetricsUpdate() {
    currentMetrics.cycles += 1;
    currentMetrics.health = Math.min(1, currentMetrics.health + 0.01);
    currentMetrics.fieldEnergy = Math.random() * 100;
    currentMetrics.coherence = 0.5 + Math.random() * 0.4;
    
    if (metricCycles) metricCycles.textContent = currentMetrics.cycles;
    if (metricCyclesBar) metricCyclesBar.style.width = `${Math.min(100, currentMetrics.cycles % 100)}%`;
    if (systemHealth) systemHealth.textContent = `${(currentMetrics.health * 100).toFixed(0)}%`;
    if (metricFieldEnergy) metricFieldEnergy.textContent = currentMetrics.fieldEnergy.toFixed(2);
    if (metricCoherence) metricCoherence.textContent = `${(currentMetrics.coherence * 100).toFixed(0)}%`;
    
    updateLastUpdateTime();
}

// ============================================================
// 12. تشغيل دورة سيادية
// ============================================================

async function runSovereignCycle() {
    addHistoryEvent('info', 'تشغيل دورة سيادية');
    addDecisionMessage('تشغيل دورة سيادية جديدة', 'pending');
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.HISTORY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ type: 'manual_cycle', timestamp: Date.now() })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addDecisionMessage(`اكتملت الدورة السيادية: ${data.cycle_id || 'غير معروف'}`, 'approved');
            addHistoryEvent('info', `الدورة ${data.cycle_id} اكتملت في ${data.duration?.toFixed(2) || 0}ms`);
            updateMetrics();
        } else {
            addDecisionMessage('فشلت الدورة السيادية', 'rejected');
            addHistoryEvent('error', 'فشل تشغيل الدورة السيادية');
        }
    } catch (error) {
        // محاكاة محلية
        addDecisionMessage('تم تشغيل دورة سيادية (محاكاة محلية)', 'approved');
        addHistoryEvent('info', 'تم تشغيل دورة سيادية محلياً');
        updateMetrics();
    }
}

// ============================================================
// 13. عرض السجل
// ============================================================

async function fetchHistory() {
    addHistoryEvent('info', 'جلب سجل الأحداث');
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.API_ENDPOINTS.HISTORY}?limit=50`);
        const data = await response.json();
        
        if (data.history) {
            data.history.forEach(event => {
                addHistoryEvent(event.level || 'info', event.message, event.details);
            });
        }
    } catch (error) {
        // إضافة أحداث محاكاة
        addHistoryEvent('info', 'تم عرض سجل الأحداث (محاكاة محلية)');
    }
    
    switchTab('history');
}

// ============================================================
// 14. WebSocket للتواصل المباشر
// ============================================================

function initWebSocket() {
    if (CONFIG.ws && CONFIG.ws.readyState === WebSocket.OPEN) {
        CONFIG.ws.close();
    }
    
    CONFIG.ws = new WebSocket(CONFIG.WS_URL);
    
    CONFIG.ws.onopen = () => {
        CONFIG.isConnected = true;
        if (wsStatusChip) {
            wsStatusChip.innerHTML = '<i class="fas fa-circle"></i> متصل';
            wsStatusChip.classList.add('online');
            wsStatusChip.classList.remove('offline');
        }
        addHistoryEvent('info', 'WebSocket متصل');
    };
    
    CONFIG.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'reply') {
                addDialogueMessage(data.message, 'الذكاء السيادي', false);
            } else if (data.type === 'notification') {
                addHistoryEvent('info', data.message);
            } else if (data.type === 'proposal') {
                addProposal({
                    title: data.title,
                    description: data.description,
                    confidence: data.confidence
                });
            }
        } catch (e) {
            addDialogueMessage(event.data, 'الذكاء السيادي', false);
        }
    };
    
    CONFIG.ws.onerror = (error) => {
        addHistoryEvent('error', 'خطأ في WebSocket');
        if (wsStatusChip) {
            wsStatusChip.innerHTML = '<i class="fas fa-circle"></i> خطأ';
            wsStatusChip.classList.add('offline');
            wsStatusChip.classList.remove('online');
        }
    };
    
    CONFIG.ws.onclose = () => {
        CONFIG.isConnected = false;
        if (wsStatusChip) {
            wsStatusChip.innerHTML = '<i class="fas fa-circle"></i> غير متصل';
            wsStatusChip.classList.add('offline');
            wsStatusChip.classList.remove('online');
        }
        addHistoryEvent('warning', 'WebSocket مغلق');
    };
}

// ============================================================
// 15. ربط الأزرار
// ============================================================

if (btnSendSir) {
    btnSendSir.addEventListener('click', () => {
        const text = sirInput?.value.trim();
        if (!text) return;
        
        sendSovereignCommand(text);
        
        if (sirInput) sirInput.value = '';
        if (sirCount) sirCount.textContent = '0 حرف';
    });
}

if (btnSendChat) {
    btnSendChat.addEventListener('click', () => {
        const text = chatInput?.value.trim();
        if (!text) return;
        
        sendChatMessage(text);
        
        if (chatInput) chatInput.value = '';
        if (chatCount) chatCount.textContent = '0 حرف';
    });
}

// إرسال بالضغط على Enter (Shift+Enter للسطر الجديد)
if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            btnSendChat?.click();
        }
    });
}

if (sirInput) {
    sirInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            btnSendSir?.click();
        }
    });
}

if (btnRunCycle) btnRunCycle.addEventListener('click', runSovereignCycle);
if (btnViewHistory) btnViewHistory.addEventListener('click', fetchHistory);
if (btnGetStatus) btnGetStatus.addEventListener('click', updateMetrics);
if (btnGetComponents) btnGetComponents.addEventListener('click', updateMetrics);

if (btnResetSystem) {
    btnResetSystem.addEventListener('click', () => {
        sendSovereignCommand('reset');
    });
}

if (btnClearCommands) {
    btnClearCommands.addEventListener('click', () => {
        commandsList = [];
        renderCommands();
        addHistoryEvent('info', 'تم مسح سجل الأوامر');
    });
}

if (btnClearHistory) {
    btnClearHistory.addEventListener('click', () => {
        historyEvents = [];
        renderHistory();
        addHistoryEvent('info', 'تم مسح سجل الأحداث');
    });
}

if (btnRefreshProposals) {
    btnRefreshProposals.addEventListener('click', () => {
        addHistoryEvent('info', 'تحديث الاقتراحات');
        // يمكن إضافة جلب من API هنا
    });
}

// أزرار WebSocket
if (btnWsConnect) btnWsConnect.addEventListener('click', initWebSocket);
if (btnWsDisconnect) btnWsDisconnect.addEventListener('click', () => {
    if (CONFIG.ws) CONFIG.ws.close();
});

// ============================================================
// 16. التحديث الحي
// ============================================================

function startLiveRefresh() {
    if (CONFIG.refreshInterval) {
        clearInterval(CONFIG.refreshInterval);
    }
    
    if (toggleLiveRefresh && toggleLiveRefresh.checked) {
        CONFIG.refreshInterval = setInterval(() => {
            updateMetrics();
        }, CONFIG.AUTO_REFRESH_INTERVAL);
    }
}

if (toggleLiveRefresh) {
    toggleLiveRefresh.addEventListener('change', startLiveRefresh);
}

// ============================================================
// 17. مفاتيح API
// ============================================================

// لا تُطلب المفاتيح تلقائياً من المتصفح؛ /api-key محمي بمفتاح السيد.

// ============================================================
// 18. تحسينات التأثيرات الهولوغرافية
// ============================================================

function initHolographicEffects() {
    if (toggleHolographic) {
        toggleHolographic.addEventListener('change', (e) => {
            if (e.target.checked) {
                document.body.classList.add('holo-active');
            } else {
                document.body.classList.remove('holo-active');
            }
        });
        
        if (toggleHolographic.checked) {
            document.body.classList.add('holo-active');
        }
    }
    
    // تأثير الجسيمات المتطايرة
    const particles = document.querySelector('.particles');
    if (particles) {
        setInterval(() => {
            if (document.body.classList.contains('holo-active')) {
                // تحديث مواقع الجسيمات
            }
        }, 100);
    }
}

// ============================================================
// 19. التهيئة
// ============================================================

function init() {
    addHistoryEvent('info', 'تم تهيئة الواجهة السيادية');
    
    startLiveRefresh();
    initHolographicEffects();
    
    // تحديث المقاييس الأولي
    setTimeout(() => {
        updateMetrics();
    }, 500);
    
    // رسالة ترحيب
    addDialogueMessage('مرحباً أيها السيد. أنا الذكاء السيادي، جاهز لأوامرك.', 'الذكاء السيادي', false);
}

// بدء التشغيل
init();
