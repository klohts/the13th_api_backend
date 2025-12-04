from datetime import datetime, timedelta

def get_today_intel(db):
    return {
        "active_deals": count_active_deals(db),
        "stuck_followups": count_stuck_followups(db),
        "team_response": compute_team_response(db),
        "automation_rate": compute_automation_rate(db),
    }

def get_live_feed(db):
    insights = []
    
    if deal_at_risk := detect_deal_at_risk(db):
        insights.append(deal_at_risk)

    if slow_threads := detect_slowing_threads(db):
        insights.append(slow_threads)

    if overload := detect_team_overload(db):
        insights.append(overload)

    return {"items": insights}
