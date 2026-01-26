/**
 * Голосовой AI Чат
 * WebSocket + Микрофон + Whisper
 */

// Глобальные переменные
let ws = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// DOM элементы
const chatContainer = document.getElementById('chat');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const micButton = document.getElementById('mic-button');
const statusElement = document.getElementById('status');
const statusText = statusElement.querySelector('.status-text');

// ========================== WebSocket ==========================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('✅ WebSocket подключен');
        statusElement.className = 'status connected';
        statusText.textContent = 'Подключено';
    };

    ws.onclose = () => {
        console.log('❌ WebSocket отключен');
        statusElement.className = 'status disconnected';
        statusText.textContent = 'Отключено';

        // Переподключение через 3 секунды
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('❌ WebSocket ошибка:', error);
        showNotification('Ошибка подключения', 'error');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
}

function handleWebSocketMessage(data) {
    const { type, content } = data;

    if (type === 'system') {
        addMessage(content, 'system');
    } else if (type === 'response') {
        removeTypingIndicator();
        addMessage(content, 'assistant');
    } else if (type === 'pong') {
        // Ответ на ping, ничего не делаем
    }
}

function sendMessage(content) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showNotification('Нет подключения к серверу', 'error');
        return;
    }

    ws.send(JSON.stringify({
        type: 'message',
        content: content
    }));

    addMessage(content, 'user');
    addTypingIndicator();
    messageInput.value = '';
    messageInput.style.height = 'auto';
}

// ========================== UI ==========================

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = content;
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    chatContainer.appendChild(typingDiv);
    scrollToBottom();
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    container.appendChild(notification);

    setTimeout(() => {
        notification.style.transition = 'opacity 0.3s';
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ========================== Микрофон ==========================

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm'
        });

        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            await sendAudioToServer(blob);
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;

        micButton.classList.add('recording');
        micButton.textContent = '⏹️';
        showNotification('🎤 Запись началась', 'info');

    } catch (error) {
        console.error('❌ Ошибка доступа к микрофону:', error);
        showNotification('Не удалось получить доступ к микрофону', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        isRecording = false;

        micButton.classList.remove('recording');
        micButton.textContent = '🎤';
        showNotification('⏹️ Запись остановлена', 'info');
    }
}

async function sendAudioToServer(blob) {
    showNotification('🎤 Распознаю речь...', 'info');

    const formData = new FormData();
    formData.append('file', blob, 'voice.webm');

    try {
        const response = await fetch('/api/voice', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('✅ Речь распознана', 'success');

            // Показываем распознанный текст
            addMessage(data.transcribed, 'transcribed');

            // Показываем ответ
            addMessage(data.response, 'assistant');

        } else {
            showNotification('❌ ' + (data.error || 'Ошибка распознавания'), 'error');
        }
    } catch (error) {
        console.error('❌ Ошибка отправки:', error);
        showNotification('Ошибка отправки аудио', 'error');
    }
}

// ========================== События ==========================

sendButton.addEventListener('click', () => {
    const message = messageInput.value.trim();
    if (message) {
        sendMessage(message);
    }
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
        }
    }
});

messageInput.addEventListener('input', () => {
    // Автоматическая высота textarea
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
});

micButton.addEventListener('click', toggleRecording);

// Ping для поддержания соединения
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);

// ========================== Инициализация ==========================

// Подключаемся к WebSocket при загрузке
connectWebSocket();

// Фокус на поле ввода
messageInput.focus();

console.log('✅ Голосовой AI чат готов!');
