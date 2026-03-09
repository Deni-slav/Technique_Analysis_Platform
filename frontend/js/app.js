const API_BASE = (window.location.port === "8000" ? "" : "http://localhost:8000") + "/api";
let currentVideoId = null;
let lastAnalysisData = null;
let chatHistory = [];

const uploadZone = document.getElementById("uploadZone");
const refUploadZone = document.getElementById("refUploadZone");
const refFileInput = document.getElementById("refFileInput");
const trainBtn = document.getElementById("trainBtn");
const refreshModelBtn = document.getElementById("refreshModelBtn");
const modelStatus = document.getElementById("modelStatus");
const refVideosList = document.getElementById("refVideosList");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const analyzeSection = document.getElementById("analyzeSection");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeStatus = document.getElementById("analyzeStatus");
const resultsSection = document.getElementById("resultsSection");
const resultsContent = document.getElementById("resultsContent");
const refreshBtn = document.getElementById("refreshBtn");

uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("video/")) uploadVideo(file);
    else showStatus(uploadStatus, "Моля, изберете видео файл.", "error");
});
fileInput.addEventListener("change", (e) => { const file = e.target.files[0]; if (file) uploadVideo(file); });

refUploadZone.addEventListener("click", () => refFileInput.click());
refFileInput.addEventListener("change", (e) => { const file = e.target.files[0]; if (file) uploadReferenceVideo(file); });
trainBtn.addEventListener("click", trainModel);
refreshModelBtn.addEventListener("click", loadModelStatus);

loadModelStatus();
loadRefVideos();

analyzeBtn.addEventListener("click", startAnalysis);
refreshBtn.addEventListener("click", () => { if (currentVideoId) fetchResults(currentVideoId); });

async function uploadVideo(file) {
    showStatus(uploadStatus, "Качване...", "info");
    const formData = new FormData();
    formData.append("file", file);
    try {
        const res = await fetch(`${API_BASE}/upload/`, { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Грешка при качване");
        currentVideoId = data.video_id;
        showStatus(uploadStatus, `Качено: ${data.filename}`, "success");
        analyzeSection.style.display = "block";
        resultsSection.style.display = "none";
    } catch (err) { showStatus(uploadStatus, err.message, "error"); }
}

async function startAnalysis() {
    if (!currentVideoId) return;
    analyzeBtn.disabled = true;
    showStatus(analyzeStatus, "Стартиране на анализа...", "info");
    try {
        const res = await fetch(`${API_BASE}/analyze/${currentVideoId}`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Грешка");
        showStatus(analyzeStatus, "Анализът е стартиран. Изчакайте 30–60 сек...", "info");
        resultsSection.style.display = "block";
        setTimeout(() => fetchResults(currentVideoId), 5000);
    } catch (err) { showStatus(analyzeStatus, err.message, "error"); }
    finally { analyzeBtn.disabled = false; }
}

async function fetchResults(videoId) {
    try {
        const res = await fetch(`${API_BASE}/results/${videoId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Резултатите не са готови");
        if (data.error) {
            resultsContent.innerHTML = `<div class="status error">Грешка при анализа: ${data.error}</div>`;
            return;
        }
        lastAnalysisData = data;
        renderResults(data);
    } catch (err) {
        resultsContent.innerHTML = `<div class="status info">${err.message} Натиснете "Обнови резултати" след минута.</div>`;
    }
}

function renderResults(data) {
    const m = data.metrics || {};
    const comp = data.comparison || {};
    const recs = data.recommendations || [];
    let html = "";
    const metrics = [
        { key: "torso_rotation", title: "Ротация на торса", value: `${m.torso_rotation?.range_deg?.toFixed(1) || 0}°`, desc: "Амплитуда на ротация" },
        { key: "drive_recovery_ratio", title: "Drive/Recovery", value: `1:${(1 / (m.drive_recovery_ratio?.ratio || 0.5)).toFixed(1)}`, desc: "Съотношение drive:recovery" },
        { key: "stroke_rate", title: "Честота (SPM)", value: `${m.stroke_rate?.spm || 0}`, desc: "Загребвания в минута" },
        { key: "symmetry", title: "Симетрия", value: `${m.symmetry?.symmetry_score?.toFixed(0) || 0}%`, desc: "Баланс ляво/дясно" }
    ];
    metrics.forEach(({ key, title, value, desc }) => {
        const c = comp[key];
        const score = c?.score ?? 50;
        const barClass = score >= 70 ? "good" : score >= 50 ? "warning" : "poor";
        html += `<div class="metric-card"><h3>${title}</h3><div class="metric-value">${value}</div><div class="metric-desc">${desc}</div><div class="score-bar"><div class="score-bar-fill ${barClass}" style="width: ${score}%"></div></div></div>`;
    });
    if (data.comparison_source === "learned") {
        html += `<p class="comparison-badge">Сравнено с научения модел</p>`;
    }
    if (recs.length) {
        html += `<div class="recommendations"><h3>Препоръки</h3><ul>${recs.map(r => `<li>${r}</li>`).join("")}</ul></div>`;
    }
    resultsContent.innerHTML = html;
}

async function uploadReferenceVideo(file) {
    showStatus(modelStatus, "Качване...", "info");
    const formData = new FormData();
    formData.append("file", file);
    try {
        const res = await fetch(`${API_BASE}/reference/videos`, { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Грешка");
        showStatus(modelStatus, `Качено: ${data.filename}`, "success");
        loadRefVideos();
    } catch (err) { showStatus(modelStatus, err.message, "error"); }
}

async function trainModel() {
    showStatus(modelStatus, "Обучение на модела... (1-5 мин)", "info");
    trainBtn.disabled = true;
    try {
        const res = await fetch(`${API_BASE}/reference/train`, { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Грешка");
        showStatus(modelStatus, data.message, "info");
        setTimeout(loadModelStatus, 3000);
    } catch (err) { showStatus(modelStatus, err.message, "error"); }
    finally { trainBtn.disabled = false; }
}

async function loadModelStatus() {
    if (!modelStatus) return;
    try {
        const res = await fetch(`${API_BASE}/reference/model`);
        const data = await res.json();
        modelStatus.textContent = data.message;
        modelStatus.className = data.trained ? "status success" : "status info";
        modelStatus.style.display = "block";
    } catch { modelStatus.textContent = ""; modelStatus.style.display = "none"; }
}

async function loadRefVideos() {
    if (!refVideosList) return;
    try {
        const res = await fetch(`${API_BASE}/reference/videos`);
        const data = await res.json();
        if (data.videos && data.videos.length) {
            refVideosList.innerHTML = `<p><strong>${data.count} референтни видеа:</strong> ${data.videos.map(v => v.filename).join(", ")}</p>`;
        } else {
            refVideosList.innerHTML = "<p>Няма качени референтни видеа.</p>";
        }
    } catch { refVideosList.innerHTML = ""; }
}

function showStatus(el, msg, type) {
    el.textContent = msg;
    el.className = `status ${type}`;
    el.style.display = msg ? "block" : "none";
}

// ========== Chatbot ==========
const chatWidget = document.getElementById("chatWidget");
const chatToggle = document.getElementById("chatToggle");
const chatPanel = document.getElementById("chatPanel");
const chatClose = document.getElementById("chatClose");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");

if (chatToggle) chatToggle.addEventListener("click", () => { chatWidget?.classList.add("open"); addWelcomeMessage(); });
if (chatClose) chatClose.addEventListener("click", () => chatWidget?.classList.remove("open"));
if (chatSend) chatSend.addEventListener("click", sendChatMessage);
if (chatInput) chatInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendChatMessage(); });

function addWelcomeMessage() {
    if (chatMessages.children.length === 0) {
        appendChatMessage("assistant", "Здравейте! Аз съм съветник за гребане. Мога да помагам с:\n• Техника и анализ\n• Тренировъчни планове\n• Спортна подготовка\n\nПитайте каквото искате!");
    }
}

function appendChatMessage(role, content) {
    if (!chatMessages) return;
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = content;
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChatMessage() {
    const text = chatInput?.value?.trim();
    if (!text) return;

    chatInput.value = "";
    appendChatMessage("user", text);
    chatHistory.push({ role: "user", content: text });

    chatSend.disabled = true;
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "chat-msg assistant";
    loadingDiv.innerHTML = '<div class="chat-bubble">Мисля...</div>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/chat/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: chatHistory,
                analysis_context: lastAnalysisData?.metrics ? { metrics: lastAnalysisData.metrics } : null
            })
        });
        const data = await res.json();
        loadingDiv.remove();
        const reply = data.message || "Не успях да отговоря.";
        appendChatMessage("assistant", reply);
        chatHistory.push({ role: "assistant", content: reply });
    } catch (err) {
        loadingDiv.remove();
        appendChatMessage("assistant", "Грешка при свързване. Опитайте отново.");
    } finally {
        chatSend.disabled = false;
    }
}
