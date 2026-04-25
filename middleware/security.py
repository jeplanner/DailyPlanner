def apply_security_headers(app):
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # CDN allow-list:
        #   unpkg.com            → feather-icons
        #   cdn.jsdelivr.net     → @yaireo/tagify, marked
        #   cdn.quilljs.com      → Quill rich-text editor
        # img-src includes *.supabase.co so user-uploaded prayer/photos
        # served from Supabase Storage's public CDN render in <img> tags.
        # blob: covers any future client-side preview from File API.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "  https://unpkg.com https://cdn.jsdelivr.net https://cdn.quilljs.com; "
            "style-src 'self' 'unsafe-inline' "
            "  https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.quilljs.com; "
            "style-src-elem 'self' 'unsafe-inline' "
            "  https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdn.quilljs.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://www.google.com https://*.supabase.co; "
            "connect-src 'self' "
            "  https://unpkg.com https://cdn.jsdelivr.net https://cdn.quilljs.com "
            "  https://query1.finance.yahoo.com https://api.mfapi.in "
            "  https://*.supabase.co;"
        )
        return response
