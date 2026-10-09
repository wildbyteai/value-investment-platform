// 页签 → 页面。页签的名字、所属菜单和可见权限在 config/menus-v1.json，由服务器按角色下发；
// 这里只负责“这个页签画哪个页面”。新增页签：在配置里加一项，在这里登记一个页面。
import React from "react";
import { NewsRadar, RawNewsPage } from "./radar";
import { CompaniesPage, Mine, ResearchPage, TodayPage } from "./company";
import { StrategyPage, StrikeZone } from "./strategy";
import { AlertsList, Inbox, NotifySettings } from "./monitor";
import { Collectors, Feeds, Models, NotifyAdmin, Skills, Sources, TasksPage } from "./settings";
import { Audit, Users } from "./accounts";

// Pages that load their own data. The shell only fetches for the others (see fetchPage).
export const SELF_LOADING = new Set([
  "events", "zone", "inbox", "alerts", "notify-settings", "sources", "feeds", "collectors", "skills", "models", "notify", "users", "audit",
]);

export const PAGES: Record<string, (p: any) => React.ReactNode> = {
  events: (p) => <NewsRadar {...p} />,
  news: (p) => <RawNewsPage {...p} />,
  companies: (p) => <CompaniesPage {...p} />,
  today: (p) => <TodayPage {...p} />,
  research: (p) => <ResearchPage {...p} />,
  mine: (p) => <Mine {...p} />,
  zone: (p) => <StrikeZone {...p} />,
  strategy: (p) => <StrategyPage {...p} />,
  inbox: (p) => <Inbox {...p} />,
  alerts: (p) => <AlertsList {...p} />,
  "notify-settings": (p) => <NotifySettings {...p} />,
  users: (p) => <Users {...p} />,
  sources: (p) => <Sources {...p} />,
  feeds: (p) => <Feeds {...p} />,
  collectors: (p) => <Collectors {...p} />,
  skills: (p) => <Skills {...p} />,
  models: (p) => <Models {...p} />,
  notify: (p) => <NotifyAdmin {...p} />,
  audit: (p) => <Audit {...p} />,
  tasks: (p) => <TasksPage {...p} />,
};
