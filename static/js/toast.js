/* ================================================
   TOAST NOTIFICATION SYSTEM
   Usage: showToast("Saved!", "success")
   Types: success, error, warning, info (default)
   ================================================ */

(function () {
    "use strict";

    // Create toast container on load
    let container;

    function ensureContainer() {
        if (container) return container;
        container = document.createElement("div");
        container.id = "toast-container";
        Object.assign(container.style, {
            position: "fixed",
            bottom: "24px",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "8px",
            zIndex: "10000",
            pointerEvents: "none",
        });
        document.body.appendChild(container);
        return container;
    }

    const COLORS = {
        success: { bg: "rgba(22, 163, 74, 0.92)", icon: "check-circle" },
        error:   { bg: "rgba(220, 38, 38, 0.92)", icon: "x-circle" },
        warning: { bg: "rgba(245, 158, 11, 0.92)", icon: "alert-triangle" },
        info:    { bg: "rgba(37, 99, 235, 0.92)", icon: "info" },
    };

    window.showToast = function (message, type, duration) {
        type = type || "info";
        duration = duration || 3000;
        const cfg = COLORS[type] || COLORS.info;
        const wrap = ensureContainer();

        const toast = document.createElement("div");
        Object.assign(toast.style, {
            background: cfg.bg,
            color: "#fff",
            padding: "10px 20px",
            borderRadius: "12px",
            fontSize: "14px",
            fontFamily: "'Inter', system-ui, sans-serif",
            fontWeight: "500",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            backdropFilter: "blur(8px)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
            opacity: "0",
            transform: "translateY(12px)",
            transition: "all 0.25s ease",
            pointerEvents: "auto",
            maxWidth: "90vw",
        });

        toast.innerHTML =
            '<i data-feather="' + cfg.icon + '" style="width:16px;height:16px;flex-shrink:0"></i>' +
            '<span>' + message + '</span>';

        wrap.appendChild(toast);

        // Render feather icon if available
        if (window.feather) feather.replace({ width: 16, height: 16 });

        // Animate in
        requestAnimationFrame(function () {
            toast.style.opacity = "1";
            toast.style.transform = "translateY(0)";
        });

        // Animate out + remove
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
            setTimeout(function () { toast.remove(); }, 300);
        }, duration);
    };
})();
