"""Gemini API bilan ishlash: mavzu qidirish, matn yozish, rasm generatsiya qilish."""
import base64
import json
import logging
import re
import time

import requests

import config

log = logging.getLogger("gemini")


class GeminiError(RuntimeError):
    pass


def _post(model: str, payload: dict, timeout: int = 180) -> dict:
    """Gemini generateContent chaqiruvi (qayta urinish bilan)."""
    url = f"{config.GEMINI_BASE}/{model}:generateContent"
    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    last_err = None
    for attempt in range(1, 5):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            # 429 / 5xx — kutib qayta urinamiz
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(60, 5 * 2 ** (attempt - 1))
                log.warning("Gemini %s -> %s, %ss kutilmoqda (urinish %s/4)",
                            model, r.status_code, wait, attempt)
                time.sleep(wait)
                last_err = f"HTTP {r.status_code}: {r.text[:400]}"
                continue
            raise GeminiError(f"Gemini HTTP {r.status_code}: {r.text[:600]}")
        except requests.RequestException as e:
            last_err = str(e)
            log.warning("Tarmoq xatosi: %s (urinish %s/4)", e, attempt)
            time.sleep(5 * attempt)
    raise GeminiError(f"Gemini javob bermadi. Oxirgi xato: {last_err}")


def _collect_text(resp: dict) -> str:
    """Javobdagi barcha matn qismlarini yig'ib beradi."""
    out = []
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            if isinstance(part.get("text"), str):
                out.append(part["text"])
    return "".join(out).strip()


def _extract_json(text: str) -> dict:
    """Model javobidan JSON obyektini ajratib oladi (```json bloklarini ham qo'llaydi)."""
    if not text:
        raise GeminiError("Gemini bo'sh javob qaytardi")

    # ```json ... ``` blokini tozalaymiz
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    candidate = fence.group(1).strip() if fence else text.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Birinchi '{' dan oxirgi '}' gacha bo'lgan qismni sinab ko'ramiz
    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise GeminiError(f"JSON o'qib bo'lmadi. Javob boshi: {text[:400]}")


# ------------------------------------------------------------------
# 1) Internetdan mavzu qidirish — google_search grounding bilan
# ------------------------------------------------------------------
def research(category: str, month_name: str, recent_topics: list[str]) -> dict:
    import prompts

    recent = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "- (hali yo'q)"
    prompt = prompts.RESEARCH_PROMPT.format(
        category=category, month_name=month_name, recent_topics=recent
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4096},
    }
    log.info("Mavzu qidirilmoqda: %s", category)
    resp = _post(config.TEXT_MODEL, payload)
    data = _extract_json(_collect_text(resp))

    if not data.get("topic") or not data.get("facts"):
        raise GeminiError(f"Tadqiqot natijasi to'liq emas: {data}")
    log.info("Topilgan mavzu: %s", data["topic"])
    return data


# ------------------------------------------------------------------
# 2) Post matnini yozish
# ------------------------------------------------------------------
def _json_call(prompt: str, temperature: float = 0.85) -> dict:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    resp = _post(config.TEXT_MODEL, payload)
    return _extract_json(_collect_text(resp))


def write_post(research_data: dict) -> dict:
    import prompts

    prompt = prompts.WRITE_PROMPT.format(
        research_json=json.dumps(research_data, ensure_ascii=False, indent=2),
        style_guide=prompts.STYLE_GUIDE,
    )
    log.info("Post matni yozilmoqda...")
    return _json_call(prompt, temperature=0.9)


def fix_post(post: dict, qc: dict, research_data: dict) -> dict:
    import prompts

    prompt = prompts.FIX_PROMPT.format(
        post_text=post.get("post_text", ""),
        problems="\n".join(f"- {p}" for p in qc.get("problems", [])) or "- (ko'rsatilmagan)",
        fix_instructions=qc.get("fix_instructions", "Postni yaxshilang."),
        research_json=json.dumps(research_data, ensure_ascii=False, indent=2),
        style_guide=prompts.STYLE_GUIDE,
    )
    log.info("Post tuzatilmoqda...")
    return _json_call(prompt, temperature=0.7)


# ------------------------------------------------------------------
# 3) Sifat nazorati (LLM-judge)
# ------------------------------------------------------------------
def quality_check(post_text: str, research_data: dict) -> dict:
    import prompts

    prompt = prompts.QC_PROMPT.format(
        post_text=post_text,
        research_json=json.dumps(research_data, ensure_ascii=False, indent=2),
    )
    log.info("Sifat nazorati (LLM) o'tkazilmoqda...")
    try:
        result = _json_call(prompt, temperature=0.2)
    except GeminiError as e:
        # Judge ishlamasa postni bloklamaymiz, faqat ogohlantiramiz
        log.warning("LLM sifat nazorati bajarilmadi: %s", e)
        return {"verdict": "PASS", "score": 0, "problems": [f"QC ishlamadi: {e}"],
                "fix_instructions": ""}
    result.setdefault("verdict", "PASS")
    result.setdefault("score", 0)
    result.setdefault("problems", [])
    result.setdefault("fix_instructions", "")
    return result


# ------------------------------------------------------------------
# 4) Rasm generatsiya qilish (nanobanana)
# ------------------------------------------------------------------
def generate_image(image_prompt: str) -> bytes | None:
    """Rasm baytlarini qaytaradi. Muvaffaqiyatsiz bo'lsa None."""
    full_prompt = f"{image_prompt}\n\nStyle: {config.IMAGE_STYLE}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    log.info("Rasm generatsiya qilinmoqda...")
    try:
        resp = _post(config.IMAGE_MODEL, payload, timeout=240)
    except GeminiError as e:
        log.error("Rasm generatsiyasi xatosi: %s", e)
        return None

    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                try:
                    return base64.b64decode(blob["data"])
                except Exception as e:  # noqa: BLE001
                    log.error("Rasmni dekodlab bo'lmadi: %s", e)
                    return None

    log.error("Javobda rasm topilmadi. Javob: %s", json.dumps(resp)[:600])
    return None
