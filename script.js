// State Management
let isListening = false;
let state = 'SLEEPING'; // SLEEPING, LISTENING, THINKING, SPEAKING
let phase = 0;
let groqApiKey = localStorage.getItem('GROQ_API_KEY') || '';

// DOM Elements
const canvas = document.getElementById('jarvisCanvas');
const ctx = canvas.getContext('2d');
const micBtn = document.getElementById('micBtn');
const aiStatus = document.getElementById('aiStatus');
const aiDetail = document.getElementById('aiDetail');
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const clockEl = document.getElementById('clock');
const configBtn = document.getElementById('configBtn');
const configModal = document.getElementById('configModal');
const closeModal = document.getElementById('closeModal');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const groqApiKeyInput = document.getElementById('groqApiKey');

// Clock
setInterval(() => {
    const now = new Date();
    clockEl.innerText = now.toLocaleTimeString();
}, 1000);

// Canvas Resizing
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// Visualizer Canvas Animation
function animateCore() {
    phase += 0.05;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;

    ctx.clearRect(0, 0, w, h);

    // Particle field
    for (let i = 0; i < 30; i++) {
        let a = i * 2.4 + phase * (i % 2 === 0 ? 0.05 : -0.03);
        let r = 50 + (i * 12) % 110;
        let x = cx + Math.cos(a) * r;
        let y = cy + Math.sin(a) * r * 0.7;
        ctx.fillStyle = '#173b4a';
        ctx.beginPath();
        ctx.arc(x, y, 1.5, 0, Math.PI * 2);
        ctx.fill();
    }

    let pulse = (Math.sin(phase * 1.5) + 1) / 2;
    let activity = state === 'LISTENING' ? 15 : state === 'SPEAKING' ? 20 : state === 'THINKING' ? 10 : 3;

    // Glowing Rings
    for (let i = 4; i > 0; i--) {
        let r = 40 + i * 18 + activity;
        ctx.strokeStyle = i % 2 === 0 ? '#286b83' : '#5bd8f4';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(cx, cy, r, phase * (i % 2 === 0 ? 1 : -1), phase * (i % 2 === 0 ? 1 : -1) + Math.PI * 1.2);
        ctx.stroke();
    }

    // Core Orb
    ctx.fillStyle = '#081b24';
    ctx.strokeStyle = '#5bd8f4';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 35 + pulse * 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#68ddf5';
    ctx.beginPath();
    ctx.arc(cx, cy, 18 + pulse * 2, 0, Math.PI * 2);
    ctx.fill();

    requestAnimationFrame(animateCore);
}
animateCore();

// Speech Recognition Setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.lang = 'en-IN';

    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.trim();
        console.log("Heard:", transcript);
        handleUserSpeech(transcript);
    };

    recognition.onerror = (err) => {
        console.error("Speech Recognition Error:", err);
    };

    recognition.onend = () => {
        if (isListening) recognition.start();
    };
} else {
    alert("Speech Recognition is not supported on this browser. Try Google Chrome.");
}

// Toggle Mic Listener
micBtn.addEventListener('click', () => {
    if (!recognition) return;
    if (!isListening) {
        recognition.start();
        isListening = true;
        micBtn.classList.add('active');
        updateState('LISTENING', 'Listening for commands...');
    } else {
        recognition.stop();
        isListening = false;
        micBtn.classList.remove('active');
        updateState('SLEEPING', 'Say "Hello Jarvis" or click Mic to start');
    }
});

function updateState(newState, detail) {
    state = newState;
    aiStatus.innerText = state;
    aiDetail.innerText = detail;
}

// Handle User Input Speech
function handleUserSpeech(text) {
    const cleanText = text.toLowerCase();

    // Wake command trigger
    if (state === 'SLEEPING') {
        if (cleanText.includes('hello jarvis') || cleanText.includes('jarvis') || cleanText.includes('wake up')) {
            updateState('READY', 'Jarvis is Awake. How can I help?');
            speak("Hello! Jarvis is awake. How can I help you?");
        }
        return;
    }

    // Process normal query
    appendMessage('YOU', text, 'user');
    processCommand(text);
}

// Process Commands or Call Groq AI
async function processCommand(text) {
    updateState('THINKING', 'Processing input...');

    const lower = text.toLowerCase();

    // Local Basic Handlers
    if (lower.includes('time')) {
        const timeStr = new Date().toLocaleTimeString();
        respond(`The current time is ${timeStr}`);
        return;
    }
    if (lower.includes('date')) {
        const dateStr = new Date().toLocaleDateString();
        respond(`Today's date is ${dateStr}`);
        return;
    }
    if (lower.includes('who created you') || lower.includes('who made you')) {
        respond("I was created by Pratiksha Naik as an AI voice assistant.");
        return;
    }

    // Fallback to Groq AI API or Default offline reply
    if (groqApiKey) {
        try {
            const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${groqApiKey}`
                },
                body: JSON.stringify({
                    model: 'openai/gpt-oss-120b',
                    messages: [
                        { role: 'system', content: 'You are Jarvis, a calm and smart natural AI voice assistant. Keep answers brief (2-3 sentences) for speech.' },
                        { role: 'user', content: text }
                    ],
                    max_tokens: 150
                })
            });
            const data = await res.json();
            const reply = data.choices[0]?.message?.content || "I didn't get that.";
            respond(reply);
        } catch (e) {
            respond("I couldn't connect to the AI server. Check your API key.");
        }
    } else {
        respond("I heard you, but my Groq API key is not configured. Please add it in settings for complete smart answers.");
    }
}

// Respond with Voice & Text UI
function respond(replyText) {
    appendMessage('JARVIS', replyText, 'jarvis');
    speak(replyText);
}

// Text To Speech Output
function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => updateState('SPEAKING', 'Speaking...');
        utterance.onend = () => updateState(isListening ? 'LISTENING' : 'SLEEPING', isListening ? 'Listening...' : 'Standing by');

        window.speechSynthesis.speak(utterance);
    }
}

// Helper: Append Message to UI
function appendMessage(sender, text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${type}`;
    msgDiv.innerHTML = `<span class="sender">${sender}</span><p class="text">${text}</p>`;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Send via Text Input
sendBtn.addEventListener('click', () => {
    const val = userInput.value.trim();
    if (val) {
        if (state === 'SLEEPING') updateState('READY', 'Processing command...');
        appendMessage('YOU', val, 'user');
        processCommand(val);
        userInput.value = '';
    }
});

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});

// Settings Modal
configBtn.addEventListener('click', () => {
    groqApiKeyInput.value = groqApiKey;
    configModal.style.display = 'flex';
});
closeModal.addEventListener('click', () => configModal.style.display = 'none');
saveApiKeyBtn.addEventListener('click', () => {
    groqApiKey = groqApiKeyInput.value.trim();
    localStorage.setItem('GROQ_API_KEY', groqApiKey);
    configModal.style.display = 'none';
    alert('API Key Saved locally!');
});

// Dashboard Tabs Switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

// Tools Tab Logic
function getWeather() {
    const city = document.getElementById('weatherInput').value.trim();
    if (!city) return;
    fetch(`https://wttr.in/${encodeURIComponent(city)}?format=j1`)
        .then(res => res.json())
        .then(data => {
            const current = data.current_condition[0];
            document.getElementById('weatherResult').innerText = `Temperature in ${city}: ${current.temp_C}°C, ${current.weatherDesc[0].value}`;
        })
        .catch(() => {
            document.getElementById('weatherResult').innerText = "Unable to fetch weather.";
        });
}

function calculateMath() {
    const expr = document.getElementById('calcInput').value;
    try {
        const result = eval(expr);
        document.getElementById('calcResult').innerText = `Result: ${result}`;
    } catch {
        document.getElementById('calcResult').innerText = "Invalid Expression";
    }
}

function startTimer() {
    let secs = parseInt(document.getElementById('timerSeconds').value);
    if (isNaN(secs) || secs <= 0) return;
    const disp = document.getElementById('timerDisplay');
    const interval = setInterval(() => {
        disp.innerText = `Timer: ${secs}s`;
        if (secs <= 0) {
            clearInterval(interval);
            disp.innerText = "Time is up!";
            speak("Timer complete!");
        }
        secs--;
    }, 1000);
}

// Notes & Todo Logic
function addTodo() {
    const inp = document.getElementById('todoInput');
    if (!inp.value.trim()) return;
    const ul = document.getElementById('todoList');
    const li = document.createElement('li');
    li.innerHTML = `${inp.value} <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
    ul.appendChild(li);
    inp.value = '';
}

function saveNote() {
    const inp = document.getElementById('noteInput');
    if (!inp.value.trim()) return;
    const ul = document.getElementById('notesList');
    const li = document.createElement('li');
    li.innerHTML = `${inp.value} <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>`;
    ul.appendChild(li);
    inp.value = '';
}
