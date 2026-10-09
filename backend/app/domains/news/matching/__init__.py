"""资讯→公司两段式匹配（ADR 0016，docs/24-news-company-matching.md）。

* ``normalize``  名称与证券代码归一化（R10a，已实现）
* ``extract``    第一段：从事件抽取全部提及的公司 → ``news_mention``（R10b）
* ``resolve``    第二段：按 ``company_alias`` 在关注列表里确定性查找 → ``news_event_company``（R10b）
* ``watchlist``  关注列表与别名维护（R10b）
* ``suggest``    建议关注：未关注但被反复提及的公司（R10b）
* ``stream``     公司档案的资讯流（R10b）
* ``jobs``       重新匹配 / 重新研判 后台任务（R11）

Like every domain package: no FastAPI imports, never commits.
"""
