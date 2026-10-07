"""The four business layers, in the order information flows.

    news        资讯雷达  事件 → 关联公司 → 关联度 / 影响分
    companies   公司档案  商业模式、财报、资讯聚合 → 经营 / 财务评分
    strategy    策略      能力圈 × 好生意 × 安全边际 → 击球区
    monitoring  监控告警  只处理落进击球区的球 → 站内通知 + 邮件

Dependencies only point downward in that list's reverse: monitoring may use strategy,
strategy may use companies, companies may use news; never the other way round.
Services raise ``app.core.errors`` and never commit; see docs/21-backend-layers.md.
"""
