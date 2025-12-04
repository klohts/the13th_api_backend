
def normalize_journey_points(points):
    """
    Ensures journey_points is a list of:
    { "day": int, "score": int }
    """
    normalized = []
    for p in points or []:
        try:
            day = p.get("day") if isinstance(p, dict) else getattr(p, "day", None)
            score = p.get("score") if isinstance(p, dict) else getattr(p, "score", None)
            if day is not None and score is not None:
                normalized.append({"day": int(day), "score": float(score)})
        except Exception:
            continue
    return normalized


def normalize_timeline_events(events):
    """
    Ensures timeline events are structured as:
    {
        "day": n,
        "event_type_label": "...",
        "headline": "...",
        "meta": "...",
        "email": { "role_label": "...", "preview": "..." }
    }
    """
    normalized = []
    for e in events or []:
        try:
            day = getattr(e, "day", None)
            headline = getattr(e, "headline", None)
            meta = getattr(e, "meta", None)
            event_type = getattr(e, "event_type", None)

            # email payload
            email_obj = getattr(e, "email", None)
            email_dict = None
            if email_obj:
                email_dict = {
                    "role_label": getattr(email_obj, "role_label", None),
                    "preview": getattr(email_obj, "preview", None),
                }

            normalized.append({
                "day": day,
                "day_label": getattr(e, "day_label", day),
                "event_type_label": getattr(e, "event_type_label", event_type),
                "headline": headline,
                "meta": meta,
                "email": email_dict,
            })
        except Exception:
            continue
    return normalized
