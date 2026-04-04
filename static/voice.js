// ===============================
// 🎙 Voice Dictation
// ===============================

let recognition;
let isRecording = false;
let _voiceBtn = null; // Track which button started recording

function initVoiceDictation(textareaId, statusElId) {
  const textarea = document.getElementById(textareaId);
  const statusEl = document.getElementById(statusElId);

  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    if (statusEl) statusEl.textContent = "Voice not supported in this browser";
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.continuous = true;
  recognition.interimResults = false;

  recognition.onstart = () => {
    isRecording = true;
    if (statusEl) statusEl.innerHTML = '<span style="color:#dc2626;">● REC</span> Listening… tap mic to stop';
    // Pulse the button that triggered it
    if (_voiceBtn) {
      _voiceBtn.classList.add("voice-recording");
      _voiceBtn.title = "Stop recording";
    }
  };

  recognition.onend = () => {
    isRecording = false;
    if (statusEl) statusEl.textContent = "Stopped";
    if (_voiceBtn) {
      _voiceBtn.classList.remove("voice-recording");
      _voiceBtn.title = "Start voice";
    }
    // Clear status after 2s
    setTimeout(() => { if (statusEl && statusEl.textContent === "Stopped") statusEl.textContent = ""; }, 2000);
  };

  recognition.onerror = (e) => {
    console.error("Voice error:", e);
    isRecording = false;
    if (statusEl) statusEl.textContent = "Voice error. Try again.";
    if (_voiceBtn) _voiceBtn.classList.remove("voice-recording");
  };

  recognition.onresult = (event) => {
    for (let i = event.resultIndex; i < event.results.length; i++) {
      let text = event.results[i][0].transcript.trim();
      text = normalizeNaturalDates(text);

      // Append as new line
      if (textarea) {
        textarea.value += (textarea.value ? "\n" : "") + text;
        // Scroll to bottom
        textarea.scrollTop = textarea.scrollHeight;
      }
    }
  };
}

function toggleVoice(textareaId, statusElId) {
  // Find the button that was clicked (for visual feedback)
  _voiceBtn = document.activeElement?.closest("button") || null;

  if (isRecording) {
    stopVoice();
    return;
  }

  initVoiceDictation(textareaId, statusElId);

  try {
    recognition.start();
  } catch (e) {
    console.error("Failed to start recognition:", e);
    const statusEl = document.getElementById(statusElId);
    if (statusEl) statusEl.textContent = "Failed to start. Try again.";
  }
}

function stopVoice() {
  if (recognition && isRecording) {
    recognition.stop();
  }
  isRecording = false;
}

// Natural date parsing
function normalizeNaturalDates(text) {
  const addDays = (n) => {
    const d = new Date();
    d.setDate(d.getDate() + n);
    return d.toISOString().slice(0, 10);
  };

  return text
    .replace(/\btomorrow\b/i, `(due ${addDays(1)})`)
    .replace(/\bnext week\b/i, `(due ${addDays(7)})`);
}
