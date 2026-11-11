from datetime import timedelta

# A full-term pregnancy is counted as 40 weeks (280 days) from the first day
# of the last menstrual period (LMP).
FULL_TERM_DAYS = 280
FULL_TERM_WEEKS = 40


def calculate_edd(lmp_date):
    """Estimated due date using Naegele's rule: LMP + 280 days."""
    return lmp_date + timedelta(days=FULL_TERM_DAYS)


def gestational_progress(lmp_date, today):
    """
    Summarise how far along a pregnancy is.

    Returns a dict with:
      weeks          - completed weeks of gestation
      days           - extra days beyond the completed weeks (0-6)
      trimester      - 1, 2 or 3
      days_to_go     - days until the EDD (negative once past it)
      percent        - progress toward 40 weeks, capped at 100
    """
    elapsed = max(0, (today - lmp_date).days)
    weeks, days = divmod(elapsed, 7)

    if weeks < 13:
        trimester = 1
    elif weeks < 28:
        trimester = 2
    else:
        trimester = 3

    return {
        'weeks': weeks,
        'days': days,
        'trimester': trimester,
        'days_to_go': (calculate_edd(lmp_date) - today).days,
        'percent': min(100, round(elapsed / FULL_TERM_DAYS * 100)),
    }
