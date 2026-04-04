
import time
import logging
import requests
import os

logger = logging.getLogger("daily_plan")


def call_gemini(prompt, retries=2):
    """Try Gemini first, fall back to Groq automatically."""
    result = _gemini(prompt, retries)
    if result and not result.startswith("AI service"):
        return result

    # Gemini failed — try Groq
    logger.info("Gemini unavailable, falling back to Groq")
    result = _groq(prompt)
    if result:
        return result

    return "AI service is busy. Please try again in a few seconds."


def call_ai(prompt):
    """Alias — same as call_gemini (tries both providers)."""
    return call_gemini(prompt)


def _gemini(prompt, retries=2):
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if not API_KEY:
        return None

    model = "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            if response.status_code in [429, 503]:
                time.sleep(2 * (attempt + 1))
                continue

            logger.error("Gemini error %s: %s", response.status_code, response.text)
            break
        except requests.exceptions.Timeout:
            logger.warning("Gemini timeout (attempt %d)", attempt + 1)
            continue
        except Exception as e:
            logger.error("Gemini exception: %s", str(e))
            break

    return None


def _groq(prompt):
    API_KEY = os.getenv("GROQ_API_KEY")
    if not API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1024,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]

        logger.error("Groq error %s: %s", response.status_code, response.text)
    except requests.exceptions.Timeout:
        logger.warning("Groq timeout")
    except Exception as e:
        logger.error("Groq exception: %s", str(e))

    return None
