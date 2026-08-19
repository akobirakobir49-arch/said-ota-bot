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


def _headers() -> dict:
    return {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"}


def _request(method: str, url: str, payload: dict | None = None,
             timeout: int = 180) -> dict:
    """Gemini API chaqiruvi (429/5xx da qayta urinish bilan)."""
    last_err = None
    for attempt in range(1, 5):
        try:
            if method == "GET":
                r = requests.get(url, headers=_headers(), timeout=timeout)
            else:
                r = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(60, 5 * 2 ** (attempt - 1))
                log.warning("Gemini %s -> %s, %ss kutilmoqda (urinish %s/4)",
                            url.rsplit("/", 1)[-1], r.status_code, wait, attempt)
                time.sleep(wait)
                last_err = f"HTTP {r.status_code}: {r.text[:400]}"
                continue
            raise GeminiError(f"Gemini HTTP {r.status_code}: {r.text[:600]}")
        except requests.RequestException as e:
            last_err = str(e)
            log.warning("Tarmoq xatosi: %s (urinish %s/4)", e, attempt)
            time.sleep(5 * attempt)
    raise GeminiError(f"Gemini javob bermadi. Oxirgi xato: {last_err}")


# ------------------------------------------------------------------
# Mavjud modellarni aniqlash (modellar vaqt o'tishi bilan o'zgaradi)
# ------------------------------------------------------------------
_models_cache: list[dict] | None = None
_resolved: dict[str, str] = {}


def list_models(force: bool = False) -> list[dict]:
    """Kalit uchun mavjud bo'lgan barcha modellarni qaytaradi."""
    global _models_cache
    if _models_cache is not None and not force:
        return _models_cache
    models: list[dict] = []
    page_token = None
    for _ in range(10):
        url = f"{config.GEMINI_BASE}?pageSize=1000"
        if page_token:
            url += f"&pageToken={page_token}"
        data = _request("GET", url, timeout=60)
        models += data.get("models", [])
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    _models_cache = models
    return models


def _short(name: str) -> str:
    return name.split("/")[-1]


def _available() -> tuple[set[str], dict[str, dict]]:
    try:
        models = list_models()
    except GeminiError as e:
        log.warning("Modellar ro'yxatini olib bo'lmadi (%s) — ustuvor ro'yxatdan foydalaniladi.", e)
        return set(), {}
    by_name = {_short(m.get("name", "")): m for m in models}
    return set(by_name), by_name


def _pick(kind: str) -> str:
    """kind: 'text' yoki 'image'. Mavjud modellardan eng mosini tanlaydi."""
    if kind in _resolved:
        return _resolved[kind]

    configured = config.TEXT_MODEL if kind == "text" else config.IMAGE_MODEL
    if configured and configured != "auto":
        _resolved[kind] = configured
        return configured

    prefs = (config.TEXT_MODEL_PREFERENCE if kind == "text"
             else config.IMAGE_MODEL_PREFERENCE)
    names, by_name = _available()

    if names:
        for p in prefs:
            if p in names:
                _resolved[kind] = p
                log.info("Tanlangan %s modeli: %s", kind, p)
                return p
        # Ustuvor ro'yxatdan topilmadi — mos keladigan boshqasini qidiramiz
        def ok(n: str) -> bool:
            m = by_name.get(n, {})
            methods = m.get("supportedGenerationMethods") or []
            is_image = "image" in n
            if kind == "image":
                return is_image and "-lite-" not in n
            return (not is_image) and "flash" in n and "embedding" not in n and (
                not methods or "generateContent" in methods)

        cands = sorted((n for n in names if ok(n)), reverse=True)
        if cands:
            _resolved[kind] = cands[0]
            log.warning("Ustuvor %s modeli topilmadi, ishlatilmoqda: %s", kind, cands[0])
            return cands[0]

    _resolved[kind] = prefs[0]
    log.warning("Model ro'yxati mavjud emas — sinab ko'rilmoqda: %s", prefs[0])
    return prefs[0]


def text_model() -> str:
    return _pick("text")


def image_model() -> str:
    return _pick("image")


def _post(model: str, payload: dict, timeout: int = 180) -> dict:
    """generateContent chaqiruvi. Model topilmasa — keyingi variantga o'tadi."""
    url = f"{config.GEMINI_BASE}/{model}:generateContent"
    try:
        return _request("POST", url, payload, timeout)
    except GeminiError as e:
        if "404" not in str(e):
            raise
        # Model o'chirilgan/almashtirilgan — ro'yxatni yangilab qayta tanlaymiz
        log.warning("'%s' modeli mavjud emas, muqobili qidirilmoqda...", model)
        _resolved.clear()
        list_models(force=True)
        kind = "image" if "image" in model else "text"
        alt = _pick(kind)
        if alt == model:
            raise
        log.info("Muqobil model: %s", alt)
        return _request("POST", f"{config.GEMINI_BASE}/{alt}:generateContent",
                        payload, timeout)


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
    resp = _post(text_model(), payload)
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
    resp = _post(text_model(), payload)
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
_IMAGE_KEYS = ("data", "b64_json", "bytesBase64Encoded", "imageBytes", "image_bytes")
_IMAGE_MAGIC = ("iVBORw0KGgo", "/9j/", "R0lGOD", "UklGR")  # png, jpeg, gif, webp


def _find_image_b64(obj) -> str | None:
    """Javob JSON'ining istalgan joyidan base64 rasmni topadi (API shakli o'zgarsa ham)."""
    if isinstance(obj, dict):
        for k in _IMAGE_KEYS:
            v = obj.get(k)
            if isinstance(v, str) and len(v) > 512 and v.lstrip().startswith(_IMAGE_MAGIC):
                return v
        for v in obj.values():
            found = _find_image_b64(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_image_b64(v)
            if found:
                return found
    elif isinstance(obj, str):
        if len(obj) > 512 and obj.lstrip().startswith(_IMAGE_MAGIC):
            return obj
    return None


def _decode(b64: str) -> bytes | None:
    try:
        if "," in b64[:64] and b64.lstrip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        return base64.b64decode(b64)
    except Exception as e:  # noqa: BLE001
        log.error("Rasmni dekodlab bo'lmadi: %s", e)
        return None


def generate_image(image_prompt: str) -> bytes | None:
    """Rasm baytlarini qaytaradi. Muvaffaqiyatsiz bo'lsa None.

    Avval yangi Interactions API sinaladi, ishlamasa eski generateContent.
    """
    full_prompt = f"{image_prompt}\n\nStyle: {config.IMAGE_STYLE}"
    model = image_model()
    log.info("Rasm generatsiya qilinmoqda (%s)...", model)

    # --- 1) Yangi Interactions API ---
    try:
        resp = _request("POST", config.GEMINI_INTERACTIONS, {
            "model": model,
            "input": [{"type": "text", "text": full_prompt}],
        }, timeout=240)
        b64 = _find_image_b64(resp)
        if b64:
            return _decode(b64)
        log.warning("Interactions javobida rasm topilmadi: %s", json.dumps(resp)[:400])
    except GeminiError as e:
        log.warning("Interactions API ishlamadi (%s) — generateContent sinaladi.", str(e)[:200])

    # --- 2) Eski generateContent ---
    for cfg in ({"responseModalities": ["TEXT", "IMAGE"]}, {}):
        payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}
        if cfg:
            payload["generationConfig"] = cfg
        try:
            resp = _post(model, payload, timeout=240)
        except GeminiError as e:
            log.warning("generateContent xatosi: %s", str(e)[:250])
            continue
        b64 = _find_image_b64(resp)
        if b64:
            return _decode(b64)
        log.warning("Javobda rasm topilmadi: %s", json.dumps(resp)[:400])

    log.error("Rasm generatsiya qilinmadi — post matn holida chiqadi.")
    return None
