import json
import re


def validate_json(raw_output: str, lead_magnet: str = "none") -> list:
    """
    Parses and validates the AI JSON output.
    Tolerates partial/truncated JSON and any number of ideas (not strictly 15).
    """

    clean = raw_output

    # Strip markdown fences
    clean = re.sub(r"```json\s*", "", clean)
    clean = re.sub(r"```\s*", "", clean)
    clean = clean.strip()

    # Remove control characters except newline/tab
    clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", " ", clean)

    # Fix trailing commas before } or ]
    clean = re.sub(r",\s*}", "}", clean)
    clean = re.sub(r",\s*]", "]", clean)

    parsed = None

    # ── Attempt 1: parse as-is ──
    try:
        parsed = json.loads(clean)
    except Exception:
        pass

    # ── Attempt 2: extract the ideas array substring and repair ──
    if parsed is None:
        try:
            arr_start = clean.find('"ideas"')
            if arr_start != -1:
                bracket = clean.find("[", arr_start)
                if bracket != -1:
                    # find the last complete idea object — look for last },
                    # then close the array + wrapper properly
                    chunk = clean[bracket:]

                    # count how many complete objects we have
                    depth = 0
                    last_complete = 0
                    for ci, ch in enumerate(chunk):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                last_complete = ci

                    # rebuild a valid array from complete objects
                    fixed = chunk[:last_complete + 1] + "]"
                    fixed = re.sub(r",\s*]", "]", fixed)
                    ideas_list = json.loads(fixed)
                    parsed = {"ideas": ideas_list}
        except Exception:
            pass

    # ── Attempt 3: find any [...] block that looks like an ideas array ──
    if parsed is None:
        try:
            bracket_open = clean.rfind("[{")
            if bracket_open != -1:
                chunk = clean[bracket_open:]
                depth = 0
                last_complete = 0
                for ci, ch in enumerate(chunk):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            last_complete = ci
                fixed = "[" + chunk[1:last_complete + 1] + "]"
                fixed = re.sub(r",\s*]", "]", fixed)
                ideas_list = json.loads(fixed)
                parsed = {"ideas": ideas_list}
        except Exception:
            pass

    if parsed is None:
        raise Exception(
            "AI output could not be parsed as JSON. Raw output:\n\n" + clean[:500]
        )

    # ── Extract ideas list ──
    ideas = None
    if isinstance(parsed, list):
        ideas = parsed
    elif isinstance(parsed, dict):
        for key in ("ideas", "content_ideas", "results", "data", "output"):
            if key in parsed and isinstance(parsed[key], list):
                ideas = parsed[key]
                break
        if ideas is None:
            for val in parsed.values():
                if isinstance(val, list) and len(val) > 0:
                    ideas = val
                    break

    if not ideas:
        raise Exception(
            f"Could not find ideas array in AI response. Keys found: {list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}"
        )

    # ── Normalise each idea — fill missing fields with defaults ──
    required_fields = {
        "idea_id": 0,
        "idea_title": "Untitled",
        "platform": "Any Platform",
        "content_type": "Post",
        "description": "",
        "hook": "",
        "target_audience": "",
        "goal": "Lead Generation",
        "trend_used": "none",
        "cta": "",
    }

    final_output = []
    for idx, idea in enumerate(ideas):
        if not isinstance(idea, dict):
            continue
        for field, default in required_fields.items():
            if field not in idea or idea[field] in (None, ""):
                idea[field] = default if field != "idea_id" else idx + 1

        # handle lead_magnet
        if "lead_magnet" in idea:
            del idea["lead_magnet"]
        if lead_magnet.lower() != "none":
            idea["lead_magnet"] = lead_magnet

        final_output.append(idea)

    if not final_output:
        raise Exception("No valid ideas found in AI response after parsing.")

    return final_output
