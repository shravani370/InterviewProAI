// ========== MONITORING STATE ==========
let multiplePersonWarnings = 0;
let tabSwitchWarnings = 0;
let excessiveMovementWarnings = 0;
let lastFacePosition = null;
let movementThreshold = 50;
let consecutiveMovementFrames = 0;

// ========== 🎥 CAMERA ==========
function startCamera() {
    navigator.mediaDevices.getUserMedia({ 
        video: { width: { ideal: 1280 }, height: { ideal: 720 } } 
    })
        .then(stream => {
            const video = document.getElementById("video");
            video.srcObject = stream;
            updateStatus("✅ Camera started", false);
        })
        .catch(err => {
            updateStatus("❌ Camera access denied", true);
            console.error("Camera error:", err);
        });
}

// ========== 🔊 SPEAK QUESTION ==========
function speak(text) {
    // Cancel any ongoing speech
    speechSynthesis.cancel();
    
    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-US";
    speech.rate = 0.9;          // Slightly slower for clarity
    speech.pitch = 1.0;         // Natural pitch
    speech.volume = 1.0;        // Full volume
    
    // Try to select best available voice
    const voices = speechSynthesis.getVoices();
    let selectedVoice = null;
    
    // Prefer Google voices or professional sounding voices
    const preferredVoices = voices.filter(v => 
        v.name.includes("Google") || 
        v.name.includes("Samantha") ||
        v.name.includes("Victoria") ||
        v.name.includes("Karen") ||
        v.name.includes("Daniel") ||
        v.name.includes("Moira")
    );
    
    if (preferredVoices.length > 0) {
        selectedVoice = preferredVoices[0];
    } else if (voices.length > 0) {
        // Fallback to any available voice
        selectedVoice = voices[0];
    }
    
    if (selectedVoice) {
        speech.voice = selectedVoice;
    }
    
    // Visual feedback
    speech.onstart = () => {
        updateStatus("🔊 Question playing... Listen carefully", false);
    };
    
    speech.onend = () => {
        updateStatus("✅ Ready to answer! Use the mic or type.", false);
    };
    
    speech.onerror = (event) => {
        console.error("Speech error:", event.error);
        updateStatus("⚠️ Could not play question audio", true);
    };
    
    speechSynthesis.speak(speech);
}

// ========== ⏱️ TIMER ==========
let time = 60;
const timerInterval = setInterval(() => {
    time--;
    const timerEl = document.getElementById("timer");
    timerEl.innerText = time + "s";
    
    if (time <= 10) {
        timerEl.classList.add("warning");
    }
    if (time <= 5) {
        timerEl.classList.add("danger");
    }
    if (time === 0) {
        clearInterval(timerInterval);
        document.getElementById("answer").placeholder = "Time's up! Please submit your answer.";
    }
}, 1000);

// ========== 🎤 VOICE INPUT ==========
function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Voice feature requires Chrome, Edge, or Safari");
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.autoRestart = false;

    recognition.start();

    updateStatus("🎤 Listening...", false);

    recognition.onresult = (event) => {
        const text = Array.from(event.results)
            .map(result => result[0].transcript)
            .join("");
        document.getElementById("answer").value = text;
        updateStatus("✅ Voice captured! Check and proceed →", false);
    };

    recognition.onerror = (event) => {
        updateStatus("❌ Speech recognition error", true);
        console.error("Speech error:", event.error);
    };

    recognition.onend = () => {
        // Restart if still needed
    };
}

// ========== 📊 STATUS UPDATE ==========
function updateStatus(message, isWarning = false) {
    const statusBar = document.getElementById("statusBar");
    const statusText = document.getElementById("status");
    
    statusText.textContent = message;
    statusBar.classList.toggle("warning", isWarning);
}

// ========== ⚠️ WARNING SYSTEM ==========
function updateWarnings() {
    const warningContent = document.getElementById("warningsContent");
    const warningsPanel = document.getElementById("warningsPanel");
    
    const warnings = [];
    
    if (multiplePersonWarnings > 0) {
        warnings.push({
            text: "Multiple people detected",
            count: multiplePersonWarnings,
            max: 3
        });
    }
    
    if (tabSwitchWarnings > 0) {
        warnings.push({
            text: "Tab switch detected",
            count: tabSwitchWarnings,
            max: 3
        });
    }
    
    if (excessiveMovementWarnings > 0) {
        warnings.push({
            text: "Excessive movement detected",
            count: excessiveMovementWarnings,
            max: 3
        });
    }
    
    if (warnings.length === 0) {
        warningsPanel.classList.remove("visible");
        return;
    }
    
    warningContent.innerHTML = warnings.map(w => `
        <div class="warning-item">
            <span>⚠️</span>
            <span>${w.text}</span>
            <span class="warning-badge">${w.count}/${w.max}</span>
        </div>
    `).join("");
    
    warningsPanel.classList.add("visible");
    
    // Terminate if any warning reaches 3
    const totalWarnings = warnings.reduce((sum, w) => sum + (w.count >= w.max ? 1 : 0), 0);
    if (totalWarnings > 0) {
        alert("⛔ Interview terminated due to policy violations");
        window.location.href = "/";
    }
}

// ========== 👁️ TAB VISIBILITY ==========
document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
        tabSwitchWarnings++;
        updateStatus(`⚠️ Tab switch detected! (${tabSwitchWarnings}/3)`, true);
        updateWarnings();
    } else {
        updateStatus("✅ Welcome back! Please focus on the interview.", false);
    }
});

// ========== 🧠 LOAD FACE API ==========
async function loadFaceAPI() {
    try {
        // Use CDN instead of local models
        console.log("✅ FaceAPI ready");
    } catch (err) {
        console.error("❌ FaceAPI load error:", err);
    }
}

// ========== 👀 DETECT & MONITOR FACES ==========
function detectFaces() {
    const video = document.getElementById("video");
    
    const detectionInterval = setInterval(async () => {
        if (!video.srcObject) return;
        
        try {
            const detections = await faceapi.detectAllFaces(
                video,
                new faceapi.TinyFaceDetectorOptions()
            );

            // ====== CHECK FOR MULTIPLE PEOPLE ======
            if (detections.length > 1) {
                multiplePersonWarnings++;
                updateStatus(`⚠️ Multiple people! (${multiplePersonWarnings}/3)`, true);
                updateWarnings();
            } 
            else if (detections.length === 1) {
                const faceBox = detections[0].detection.box;
                
                // ====== CHECK FOR EXCESSIVE MOVEMENT ======
                if (lastFacePosition !== null) {
                    const movement = Math.sqrt(
                        Math.pow(faceBox.x - lastFacePosition.x, 2) +
                        Math.pow(faceBox.y - lastFacePosition.y, 2)
                    );
                    
                    if (movement > movementThreshold) {
                        consecutiveMovementFrames++;
                        
                        if (consecutiveMovementFrames >= 4) {
                            excessiveMovementWarnings++;
                            updateStatus(`⚠️ Excessive movement! (${excessiveMovementWarnings}/3)`, true);
                            updateWarnings();
                            consecutiveMovementFrames = 0;
                        }
                    } else {
                        consecutiveMovementFrames = Math.max(0, consecutiveMovementFrames - 1);
                    }
                }
                
                lastFacePosition = { x: faceBox.x, y: faceBox.y };
                updateStatus("✅ Face detected - Ready to answer", false);
            } 
            else {
                updateStatus("⚠️ No face detected - Adjust camera", true);
            }

        } catch (err) {
            console.error("Detection error:", err);
        }

    }, 1500);
}

// ========== ✅ VALIDATE ANSWER BEFORE SUBMIT ==========
function validateAnswer(event) {
    const answerField = document.getElementById("answer");
    const answer = answerField.value.trim();
    
    if (!answer) {
        event.preventDefault();
        updateStatus("❌ Please provide an answer before continuing", true);
        answerField.focus();
        answerField.style.borderColor = "red";
        setTimeout(() => {
            answerField.style.borderColor = "";
        }, 3000);
        return false;
    }
    
    // Copy answer to hidden field and allow submission
    document.getElementById("hiddenAnswer").value = answer;
    return true;
}

// ========== 🚀 INITIALIZE ==========
window.onload = async () => {
    console.log("Video interview started");
    
    startCamera();
    
    // Ensure voices are loaded before speaking
    return new Promise((resolve) => {
        const loadVoices = () => {
            const voices = speechSynthesis.getVoices();
            if (voices.length > 0) {
                console.log(`✅ ${voices.length} voices available`);
                speakQuestion();
                resolve();
            } else {
                console.log("Waiting for voices to load...");
                setTimeout(loadVoices, 500);
            }
        };
        
        speechSynthesis.onvoiceschanged = loadVoices;
        loadVoices();
        
        async function speakQuestion() {
            // Wait for faceapi to be available
            let attempts = 0;
            while (typeof faceapi === "undefined" && attempts < 15) {
                await new Promise(r => setTimeout(r, 200));
                attempts++;
            }

            if (typeof faceapi !== "undefined") {
                await loadFaceAPI();
                detectFaces();
                updateStatus("✅ Ready! Listen to the question and respond.", false);
            } else {
                updateStatus("⚠️ Face detection unavailable", true);
            }

            // Read and speak the question
            const questionText = document.getElementById("question").innerText;
            if (questionText) {
                setTimeout(() => speak(questionText), 800);
            }
        }
    });
};