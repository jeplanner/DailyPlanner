/* ================================================
   AUTH JS — password show/hide, strength meter,
   confirm-match validation. No external deps.
   ================================================ */

(function () {
    "use strict";

    /* ── Show / hide password ── */
    document.querySelectorAll("[data-toggle-password]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var id = btn.getAttribute("data-toggle-password");
            var field = document.getElementById(id);
            if (!field) return;
            var isHidden = field.type === "password";
            field.type = isHidden ? "text" : "password";
            btn.setAttribute("aria-pressed", String(isHidden));
            btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
            btn.querySelector("span").textContent = isHidden ? "🙈" : "👁";
        });
    });

    /* ── Lightweight password strength scorer.
       Scores 0-4 like zxcvbn-lite without the 400 KB. ── */
    function scorePassword(pw) {
        if (!pw) return 0;
        var score = 0;
        if (pw.length >= 8)  score++;
        if (pw.length >= 12) score++;
        var classes = 0;
        if (/[a-z]/.test(pw))  classes++;
        if (/[A-Z]/.test(pw))  classes++;
        if (/\d/.test(pw))     classes++;
        if (/[^A-Za-z0-9]/.test(pw)) classes++;
        if (classes >= 3) score++;
        if (classes === 4 && pw.length >= 10) score++;
        // Cap at 4 (visual scale).
        return Math.min(4, score);
    }
    var strengthLabels = ["Too short", "Weak", "Fair", "Strong", "Excellent"];

    document.querySelectorAll("[data-strength-meter]").forEach(function (input) {
        var meterId = input.getAttribute("data-strength-meter");
        var meter = document.getElementById(meterId);
        if (!meter) return;
        var label = meter.querySelector(".pw-meter-label");
        input.addEventListener("input", function () {
            var s = scorePassword(input.value);
            meter.setAttribute("data-score", String(s));
            if (label) label.textContent = input.value ? strengthLabels[s] : "Password strength";
        });
    });

    /* ── Confirm-password live match check ──
       Compares values raw, but strips trailing whitespace on submit
       because autofill / mobile keyboards routinely append a space the
       user can't see. We don't trim leading whitespace because some
       passphrases legitimately start with a space; we don't compare
       trimmed values during typing because that would let "abc " and
       "abc" register as a match while typing. */
    document.querySelectorAll("[data-match]").forEach(function (confirmEl) {
        var sourceId = confirmEl.getAttribute("data-match");
        var source = document.getElementById(sourceId);
        if (!source) return;
        var err = document.getElementById("match-error");

        function check() {
            if (!confirmEl.value) {
                confirmEl.removeAttribute("aria-invalid");
                if (err) err.hidden = true;
                return;
            }
            var match = confirmEl.value === source.value;
            confirmEl.setAttribute("aria-invalid", String(!match));
            if (err) {
                err.hidden = match;
                if (!match) {
                    // Hint at the most common cause: invisible whitespace.
                    var lenDiff = source.value.length - confirmEl.value.length;
                    if (Math.abs(lenDiff) === 1
                        && (source.value.trim() === confirmEl.value.trim())) {
                        err.textContent = "Passwords differ by a trailing space — check both fields.";
                    } else {
                        err.textContent = "Passwords don't match.";
                    }
                }
            }
        }
        confirmEl.addEventListener("input", check);
        source.addEventListener("input", check);

        var form = confirmEl.closest("form");
        if (form) {
            form.addEventListener("submit", function (e) {
                // Auto-strip trailing whitespace from BOTH fields right
                // before submit. Common autofill / mobile-keyboard bug.
                if (source.value !== source.value.replace(/\s+$/, "")) {
                    source.value = source.value.replace(/\s+$/, "");
                }
                if (confirmEl.value !== confirmEl.value.replace(/\s+$/, "")) {
                    confirmEl.value = confirmEl.value.replace(/\s+$/, "");
                }
                if (confirmEl.value !== source.value) {
                    e.preventDefault();
                    check();
                    confirmEl.focus();
                }
            });
        }
    });
})();
