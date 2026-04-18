// ===============================
// 🎙 Voice Dictation
// ===============================

let recognition;
let isRecording = false;
let _voiceBtn = null; // Track which button started recording
let _voiceSubmitFn = null; // Optional "add tasks" callback per session

function initVoiceDictation(textareaId, statusElId, onSubmit) {
  const textarea = document.getElementById(textareaId);
  const statusEl = document.getElementById(statusElId);
  _voiceSubmitFn = (typeof onSubmit === "function") ? onSubmit : null;

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

      // Intercept meta voice commands (erase/submit) before appending.
      const cmd = _interpretVoiceCommand(text);
      if (cmd) {
        _executeVoiceCommand(cmd, textarea, statusEl);
        continue;
      }

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

function toggleVoice(textareaId, statusElId, onSubmit) {
  // Find the button that was clicked (for visual feedback)
  _voiceBtn = document.activeElement?.closest("button") || null;

  if (isRecording) {
    stopVoice();
    return;
  }

  initVoiceDictation(textareaId, statusElId, onSubmit);

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

// Light cleanup applied during dictation — strip trailing punctuation
// and collapse whitespace so each spoken phrase lands as a tidy line.
// Actual date/recurrence/quadrant parsing happens at submit time in
// parseTaskLine() so the textarea stays human-readable.
function normalizeNaturalDates(text) {
  return text.replace(/[.!?]+$/g, "").replace(/\s{2,}/g, " ").trim();
}

// ===============================
// 🎙 Voice meta-commands
// ===============================
// Spoken phrases that control the text area or submit it, rather than
// landing as a dictated task. Recognized (case-insensitive):
//   "erase all" / "clear all" / "delete everything"        → clear textarea
//   "erase first line" / "erase last line"                 → drop one line
//   "erase line <n>"  (digits or words one..twenty)        → drop that line
//   "add tasks" / "add all" / "submit" / "done"            → fire onSubmit

const _VOICE_NUM_WORDS = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8,
  nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14,
  fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
  twenty: 20,
};

function _interpretVoiceCommand(raw) {
  const t = (raw || "").toLowerCase().replace(/[.,!?;:]/g, "").replace(/\s{2,}/g, " ").trim();
  if (!t) return null;

  if (/^(erase|clear|delete|remove)\s+(all|everything)$/.test(t)) {
    return { type: "clear" };
  }

  const firstLast = t.match(/^(?:erase|clear|delete|remove)\s+(?:the\s+)?(first|last)\s+line$/);
  if (firstLast) return { type: "eraseLine", which: firstLast[1] };

  const numWordAlt = Object.keys(_VOICE_NUM_WORDS).join("|");
  const lineNum = t.match(new RegExp(`^(?:erase|clear|delete|remove)\\s+(?:the\\s+)?line\\s+(\\d+|${numWordAlt})$`));
  if (lineNum) {
    const tok = lineNum[1];
    const n = /^\d+$/.test(tok) ? parseInt(tok, 10) : _VOICE_NUM_WORDS[tok];
    if (n && n >= 1) return { type: "eraseLine", index: n - 1 };
  }

  if (/^(?:add|submit|save)(?:\s+(?:all|the))?(?:\s+tasks?|\s+everything|\s+items?)?$/.test(t)
      || /^done$/.test(t)) {
    return { type: "submit" };
  }

  return null;
}

function _voiceFlash(statusEl, msg, color) {
  if (!statusEl) return;
  statusEl.innerHTML = `<span style="color:${color || "#0ea5e9"};">✓ ${msg}</span>`;
}

function _executeVoiceCommand(cmd, textarea, statusEl) {
  if (!textarea) return;

  if (cmd.type === "clear") {
    textarea.value = "";
    _voiceFlash(statusEl, "Cleared");
    return;
  }

  if (cmd.type === "eraseLine") {
    const lines = textarea.value.split("\n");
    if (!lines.length || (lines.length === 1 && !lines[0])) {
      _voiceFlash(statusEl, "Nothing to erase", "#dc2626");
      return;
    }
    let idx;
    if (cmd.which === "first") {
      idx = 0;
      while (idx < lines.length - 1 && !lines[idx].trim()) idx++;
    } else if (cmd.which === "last") {
      idx = lines.length - 1;
      while (idx > 0 && !lines[idx].trim()) idx--;
    } else {
      idx = cmd.index;
    }
    if (idx < 0 || idx >= lines.length) {
      _voiceFlash(statusEl, `No line ${idx + 1}`, "#dc2626");
      return;
    }
    lines.splice(idx, 1);
    textarea.value = lines.join("\n");
    textarea.scrollTop = textarea.scrollHeight;
    _voiceFlash(statusEl, `Erased line ${idx + 1}`);
    return;
  }

  if (cmd.type === "submit") {
    const submit = _voiceSubmitFn;
    if (typeof submit !== "function") {
      _voiceFlash(statusEl, "Submit not available here", "#dc2626");
      return;
    }
    _voiceFlash(statusEl, "Adding tasks…");
    // Stop listening so the "add tasks" utterance doesn't race further input.
    stopVoice();
    try { submit(); } catch (e) { console.error("Voice submit failed:", e); }
    return;
  }
}

// ===============================
// 🎙 Voice command parser
// ===============================
// Turns a single spoken line (e.g. "schedule call vendor next monday repeat weekly")
// into structured fields for /todo/autosave.
//
// Returns: { task_text, quadrant, due_date, recurrence }
// - quadrant: "do" | "schedule" | "delegate" | "eliminate" | null
// - due_date: "YYYY-MM-DD" | null
// - recurrence: "daily" | "weekly" | "monthly" | null

const _VOICE_WEEKDAYS = {
  sunday: 0, sun: 0,
  monday: 1, mon: 1,
  tuesday: 2, tue: 2, tues: 2,
  wednesday: 3, wed: 3,
  thursday: 4, thu: 4, thur: 4, thurs: 4,
  friday: 5, fri: 5,
  saturday: 6, sat: 6,
};

function _voiceIsoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${da}`;
}

function _voiceBaseDate(planDate) {
  // Use planDate (the matrix date) as "today" so dictation respects the
  // date the user is planning for, not the wall clock.
  if (planDate && /^\d{4}-\d{2}-\d{2}$/.test(planDate)) {
    return new Date(planDate + "T00:00:00");
  }
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function _voiceNextWeekday(targetDow, fromDate, forceNextWeek) {
  const d = new Date(fromDate);
  let diff = (targetDow - d.getDay() + 7) % 7;
  if (forceNextWeek) diff += 7;
  d.setDate(d.getDate() + diff);
  return d;
}

function parseTaskLine(line, planDate) {
  const out = { task_text: "", quadrant: null, due_date: null, recurrence: null };
  let text = (line || "").trim();
  // Strip common leading bullet markers and trailing punctuation.
  text = text.replace(/^[-•*]\s*/, "").replace(/[.!?,;]+$/g, "").trim();
  if (!text) return out;

  const base = _voiceBaseDate(planDate);
  const weekdayAlt = Object.keys(_VOICE_WEEKDAYS).join("|");

  // --- Quadrant prefix (optional): "do: ...", "schedule ...", etc. ---
  const quadRe = /^(do|schedule|delegate|eliminate|delete|drop)\s*[:\-,]?\s+/i;
  const quadMatch = text.match(quadRe);
  if (quadMatch) {
    const q = quadMatch[1].toLowerCase();
    out.quadrant = (q === "delete" || q === "drop") ? "eliminate" : q;
    text = text.slice(quadMatch[0].length).trim();
  }

  // --- Recurrence (try longest/most-specific first) ---
  const recurrencePatterns = [
    { re: /\b(?:repeat(?:\s+it)?\s+)?every\s*day\b/i, val: "daily" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?everyday\b/i, val: "daily" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?daily\b/i, val: "daily" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?every\s*week\b/i, val: "weekly" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?weekly\b/i, val: "weekly" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?every\s*month\b/i, val: "monthly" },
    { re: /\b(?:repeat(?:\s+it)?\s+)?monthly\b/i, val: "monthly" },
    // Bare "repeat" / "repeat it" with no qualifier — default to daily.
    { re: /\brepeat(?:\s+it)?\b/i, val: "daily" },
  ];
  for (const { re, val } of recurrencePatterns) {
    if (re.test(text)) {
      out.recurrence = val;
      text = text.replace(re, " ");
      break;
    }
  }

  // --- Due date (try most specific first) ---
  const datePatterns = [
    // "next week"
    {
      re: /\bnext\s+week\b/i,
      fn: () => {
        const d = new Date(base); d.setDate(d.getDate() + 7);
        return d;
      },
    },
    // "this week" — treat as today
    { re: /\bthis\s+week\b/i, fn: () => new Date(base) },
    // "next month"
    {
      re: /\bnext\s+month\b/i,
      fn: () => {
        const d = new Date(base); d.setMonth(d.getMonth() + 1);
        return d;
      },
    },
    // "this month" — treat as today
    { re: /\bthis\s+month\b/i, fn: () => new Date(base) },
    // "next <weekday>" → 7-13 days ahead
    {
      re: new RegExp(`\\bnext\\s+(${weekdayAlt})\\b`, "i"),
      fn: (m) => _voiceNextWeekday(_VOICE_WEEKDAYS[m[1].toLowerCase()], base, true),
    },
    // "this <weekday>" / "on <weekday>" / bare weekday → next upcoming occurrence
    {
      re: new RegExp(`\\bthis\\s+(${weekdayAlt})\\b`, "i"),
      fn: (m) => _voiceNextWeekday(_VOICE_WEEKDAYS[m[1].toLowerCase()], base, false),
    },
    {
      re: new RegExp(`\\bon\\s+(${weekdayAlt})\\b`, "i"),
      fn: (m) => _voiceNextWeekday(_VOICE_WEEKDAYS[m[1].toLowerCase()], base, false),
    },
    // "tomorrow"
    {
      re: /\btomorrow\b/i,
      fn: () => {
        const d = new Date(base); d.setDate(d.getDate() + 1);
        return d;
      },
    },
    // "today"
    { re: /\btoday\b/i, fn: () => new Date(base) },
    // Bare weekday (no "this"/"next"/"on") — last, because it's the least specific
    {
      re: new RegExp(`\\b(${weekdayAlt})\\b`, "i"),
      fn: (m) => _voiceNextWeekday(_VOICE_WEEKDAYS[m[1].toLowerCase()], base, false),
    },
  ];
  for (const { re, fn } of datePatterns) {
    const m = text.match(re);
    if (m) {
      try {
        out.due_date = _voiceIsoDate(fn(m));
      } catch (_) {}
      text = text.replace(re, " ");
      break;
    }
  }

  // Remove trailing/leading prepositions left over after keyword extraction
  // (e.g. "call vendor on" → "call vendor").
  text = text.replace(/\s{2,}/g, " ").trim();
  text = text.replace(/\b(on|by|for|at)\s*$/i, "").trim();
  text = text.replace(/^(on|by|for|at)\s+/i, "").trim();
  text = text.replace(/\s{2,}/g, " ").trim();

  out.task_text = text;
  return out;
}
