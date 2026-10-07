"""监控告警: watch strike-zone changes and confirmed news, raise alerts only for balls
that land in the strike zone, deliver them in-app and by e-mail (sender in
config/alerts-v1.json, SMTP from VIP_SMTP_*). Run by ``python -m app.jobs alerts``.
"""
