export interface paths {
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/seals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Status */
        get: operations["status_api_strategy_seals_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/research/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["list_runs_api_research_runs_get"];
        put?: never;
        /** Run */
        post: operations["run_api_research_runs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/research/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read */
        get: operations["read_api_research_runs__run_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/identities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Identities
         * @description List synthetic login options for the demo login page (5 roles x 2 workspaces).
         *     Development mode only: in production this would hand every account name to anyone.
         */
        get: operations["list_identities_api_identities_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/state": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Auth State
         * @description What the UI should show first: the dev identity picker, a login form, or the app.
         */
        get: operations["auth_state_api_auth_state_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["change_password_api_auth_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/demo/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["list_runs_api_demo_runs_get"];
        put?: never;
        /**
         * Create Run
         * @description Authorized business write (data_admin). Writes run + audit + outbox in ONE txn.
         */
        post: operations["create_run_api_demo_runs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/demo/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Audit
         * @description Needs audit.read (system_admin, which holds every permission).
         */
        get: operations["read_audit_api_demo_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/demo/outbox": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Outbox
         * @description Worker/ops view of undispatched outbox rows.
         */
        get: operations["read_outbox_api_demo_outbox_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/demo/outbox/{outbox_id}/dispatch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Dispatched */
        post: operations["mark_dispatched_api_demo_outbox__outbox_id__dispatch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/intake/synthetic": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Ingest Synthetic
         * @description data_admin imports the synthetic fixture. Idempotent by entry_key.
         */
        post: operations["ingest_synthetic_api_intake_synthetic_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/intake/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Items
         * @description Timeline of readable items. Sorted: dated first (newest), unknown-date last.
         */
        get: operations["list_items_api_intake_items_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/intake/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Item */
        get: operations["get_item_api_intake_items__item_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/companies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Companies */
        get: operations["list_companies_api_companies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/companies/{company_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company Timeline */
        get: operations["company_timeline_api_companies__company_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/judgments/auto-run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Auto */
        post: operations["run_auto_api_judgments_auto_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/judgments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Effective */
        get: operations["list_effective_api_judgments_get"];
        put?: never;
        /** Create Judgment */
        post: operations["create_judgment_api_judgments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/judgments/proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Propose Judgment */
        post: operations["propose_judgment_api_judgments_proposals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/judgments/catalog/{company_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Rubric Catalog */
        get: operations["rubric_catalog_api_judgments_catalog__company_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/judgments/{slot_key}/override": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Override */
        post: operations["override_api_judgments__slot_key__override_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/companies/{company_id}/score": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company Score */
        get: operations["company_score_api_companies__company_id__score_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Current */
        get: operations["current_api_strategy_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/simulate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Simulate */
        post: operations["simulate_api_strategy_simulate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish */
        post: operations["publish_api_strategy_publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/run-golden": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Golden */
        post: operations["run_golden_api_strategy_run_golden_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/transitions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Transitions */
        get: operations["transitions_api_strategy_transitions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strategy/evaluations/{evaluation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Evaluation */
        get: operations["evaluation_api_strategy_evaluations__evaluation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/templates/{company_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read */
        get: operations["read_api_templates__company_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/templates/{company_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Preview */
        post: operations["preview_api_templates__company_id__preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/templates/{company_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish */
        post: operations["publish_api_templates__company_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/me/watchlist/{security_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Watch */
        post: operations["add_watch_api_me_watchlist__security_id__post"];
        /** Remove Watch */
        delete: operations["remove_watch_api_me_watchlist__security_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/me/watchlist": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Watch */
        get: operations["list_watch_api_me_watchlist_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/me/notes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notes */
        get: operations["list_notes_api_me_notes_get"];
        put?: never;
        /** Add Note */
        post: operations["add_note_api_me_notes_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/worker/outbox/{outbox_id}/claim": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Claim Outbox */
        post: operations["claim_outbox_api_worker_outbox__outbox_id__claim_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/worker/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Tasks */
        get: operations["tasks_api_worker_tasks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/worker/outbox/{outbox_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry */
        post: operations["retry_api_worker_outbox__outbox_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/worker/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Source Runs */
        get: operations["source_runs_api_worker_sources_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strike-zone/policy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Policy */
        get: operations["get_policy_api_strike_zone_policy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strike-zone": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Board */
        get: operations["board_api_strike_zone_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/strike-zone/companies/{company_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Company */
        get: operations["company_api_strike_zone_companies__company_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sources */
        get: operations["sources_api_admin_sources_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/news-feeds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Feeds */
        get: operations["list_feeds_api_admin_news_feeds_get"];
        put?: never;
        /** Create Feed */
        post: operations["create_feed_api_admin_news_feeds_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/news-feeds/{feed_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Feed */
        put: operations["update_feed_api_admin_news_feeds__feed_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/llm-providers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Providers */
        get: operations["list_providers_api_admin_llm_providers_get"];
        put?: never;
        /** Create Provider */
        post: operations["create_provider_api_admin_llm_providers_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/llm-presets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Llm Presets
         * @description 内置模型预设（config/model-presets-v1.json）：添加模型时用来预填表单，不含任何密钥。
         */
        get: operations["llm_presets_api_admin_llm_presets_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/llm-providers/{provider_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Provider */
        put: operations["update_provider_api_admin_llm_providers__provider_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/llm-providers/{provider_id}/api-key": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Clear Provider Key
         * @description 清除页面保存的 API Key（之后如设置了环境变量则改用环境变量）。
         */
        delete: operations["clear_provider_key_api_admin_llm_providers__provider_id__api_key_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/model-scenes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Model Scene List
         * @description 每个调用大模型的场景用哪个模型，以及当前实际生效的模型（不含任何密钥）。
         */
        get: operations["model_scene_list_api_admin_model_scenes_get"];
        /**
         * Model Scene Save
         * @description 整体替换本工作区的场景绑定（模型 + 推理强度）；没列出的场景改为使用默认模型与推荐强度。
         */
        put: operations["model_scene_save_api_admin_model_scenes_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/notify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Notify Settings */
        get: operations["notify_settings_api_admin_notify_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/roles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Roles */
        get: operations["roles_api_admin_roles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users_api_admin_users_get"];
        put?: never;
        /** Create User */
        post: operations["create_user_api_admin_users_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get User */
        get: operations["get_user_api_admin_users__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update User */
        patch: operations["update_user_api_admin_users__user_id__patch"];
        trace?: never;
    };
    "/api/admin/users/{user_id}/roles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Set Roles */
        put: operations["set_roles_api_admin_users__user_id__roles_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/users/{user_id}/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset Password */
        post: operations["reset_password_api_admin_users__user_id__password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/users/{user_id}/sign-out": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign Out */
        post: operations["sign_out_api_admin_users__user_id__sign_out_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Audit */
        get: operations["audit_api_admin_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Events */
        get: operations["events_api_news_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Event */
        get: operations["event_api_news_events__event_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Files
         * @description Upload one or more daily Excel files; the feed is named after the file.
         */
        post: operations["import_files_api_news_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/score": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Score */
        post: operations["score_api_news_score_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/links/{link_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review */
        post: operations["review_api_news_links__link_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/links/review-batch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Review Batch
         * @description 批量确认 / 驳回 AI 预判结果（按 AI 给出的公司、关联度、影响分原样确认）。
         */
        post: operations["review_batch_api_news_links_review_batch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/feeds/{feed_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Feed */
        post: operations["run_feed_api_news_feeds__feed_id__run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/feeds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Feeds */
        get: operations["feeds_api_news_feeds_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Alerts */
        get: operations["alerts_api_alerts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/alerts/scan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Scan
         * @description Run the monitor now (normally ``python -m app.jobs alerts`` on a schedule).
         */
        post: operations["scan_api_alerts_scan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** My Notifications */
        get: operations["my_notifications_api_notifications_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/{notification_id}/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Read One */
        post: operations["read_one_api_notifications__notification_id__read_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/read-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Read All */
        post: operations["read_all_api_notifications_read_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/notifications/settings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Settings  */
        get: operations["get_settings__api_notifications_settings_get"];
        /** Put Settings */
        put: operations["put_settings_api_notifications_settings_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/skills": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Skills */
        get: operations["skills_api_admin_skills_get"];
        put?: never;
        /** Create Skill */
        post: operations["create_skill_api_admin_skills_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/skills/{skill_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Skill */
        put: operations["update_skill_api_admin_skills__skill_id__put"];
        post?: never;
        /** Delete Skill */
        delete: operations["delete_skill_api_admin_skills__skill_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Collectors */
        get: operations["collectors_api_admin_collectors_get"];
        put?: never;
        /** Create Collector */
        post: operations["create_collector_api_admin_collectors_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Collector Options
         * @description Models and skills a collector can pick (no key values, only whether each key is set).
         */
        get: operations["collector_options_api_admin_collectors_options_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/presets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Collector Presets List
         * @description 预置采集定时器包（config/collector-presets-v1.json）及本工作区是否已导入。
         */
        get: operations["collector_presets_list_api_admin_collectors_presets_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/presets/install": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Collector Presets Install
         * @description 导入预置采集定时器：缺的创建、已有的跳过（按 Skill 标识和定时器名称判断），可重复执行。
         */
        post: operations["collector_presets_install_api_admin_collectors_presets_install_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/{task_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Collector */
        put: operations["update_collector_api_admin_collectors__task_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/{task_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Run Collector
         * @description Run now (synchronously; a search-enabled model may take a minute or two).
         */
        post: operations["run_collector_api_admin_collectors__task_id__run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/admin/collectors/{task_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Collector Runs */
        get: operations["collector_runs_api_admin_collectors__task_id__runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/watchlist/companies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Watch List
         * @description 本工作区关注的公司（只有 active 的参与第二段匹配）。
         */
        get: operations["watch_list_api_watchlist_companies_get"];
        put?: never;
        /**
         * Watch Add
         * @description 关注一家公司（公司档案里没有就按名称新建，并写入别名）。
         */
        post: operations["watch_add_api_watchlist_companies_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/watchlist/companies/{watch_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Watch Delete
         * @description 取消关注（已有关联保留）。
         */
        delete: operations["watch_delete_api_watchlist_companies__watch_id__delete"];
        options?: never;
        head?: never;
        /**
         * Watch Update
         * @description 改状态（active / archived）或备注。
         */
        patch: operations["watch_update_api_watchlist_companies__watch_id__patch"];
        trace?: never;
    };
    "/api/companies/{company_id}/aliases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Alias List */
        get: operations["alias_list_api_companies__company_id__aliases_get"];
        put?: never;
        /** Alias Add */
        post: operations["alias_add_api_companies__company_id__aliases_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/companies/{company_id}/aliases/{alias_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Alias Delete */
        delete: operations["alias_delete_api_companies__company_id__aliases__alias_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/companies/{company_id}/news": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Company News
         * @description 公司资讯流：已确认 + 待确认的关联，按时间倒序，游标分页。
         */
        get: operations["company_news_api_companies__company_id__news_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/events/{event_id}/mentions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Event Mentions
         * @description 第一段抽取出的全部公司提及（关注与否），及第二段匹配结果。
         */
        get: operations["event_mentions_api_news_events__event_id__mentions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/suggested-companies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Suggested
         * @description 建议关注：近期被多条资讯提及、但本工作区未关注的公司。
         */
        get: operations["suggested_api_news_suggested_companies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/suggested-companies/add": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Suggested Add
         * @description 一键关注（没有就新建公司并写入别名）。
         */
        post: operations["suggested_add_api_news_suggested_companies_add_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/match-jobs/estimate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Match Estimate
         * @description 执行前预估：涉及事件数与预计大模型调用次数。
         */
        post: operations["match_estimate_api_news_match_jobs_estimate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/match-jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Match Jobs */
        get: operations["match_jobs_api_news_match_jobs_get"];
        put?: never;
        /**
         * Match Job Create
         * @description 排队一个 重新匹配（rematch）或 重新研判（reassess，需 news.reassess）任务，后台执行。
         */
        post: operations["match_job_create_api_news_match_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/match-jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Match Job */
        get: operations["match_job_api_news_match_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/news/match-jobs/{job_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Match Job Cancel
         * @description 取消排队中或执行中的任务（已处理的部分保留）。
         */
        post: operations["match_job_cancel_api_news_match_jobs__job_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Api Root */
        get: operations["api_root_api_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AliasIn */
        AliasIn: {
            /** Alias */
            alias: string;
            /**
             * Kind
             * @default short
             * @enum {string}
             */
            kind: "name" | "short" | "en" | "former" | "ticker";
            /**
             * Market
             * @description kind=ticker 时可指明市场；不填按代码形状推断
             */
            market?: ("SH" | "SZ" | "BJ" | "HK" | "US") | null;
        };
        /** AliasListOut */
        AliasListOut: {
            /** Company Id */
            company_id: string;
            /** Items */
            items: components["schemas"]["AliasOut"][];
        };
        /** AliasOut */
        AliasOut: {
            /** Id */
            id: string;
            /** Company Id */
            company_id: string;
            /** Alias */
            alias: string;
            /**
             * Alias Norm
             * @description 归一化结果（matching/normalize.py），匹配时比较的就是它
             */
            alias_norm: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "name" | "short" | "en" | "former" | "ticker";
            /** Market */
            market: ("SH" | "SZ" | "BJ" | "HK" | "US") | null;
            /**
             * Source
             * @enum {string}
             */
            source: "seed" | "manual" | "suggested";
            /** Created At */
            created_at: string;
        };
        /** BatchReviewIn */
        BatchReviewIn: {
            /** Action */
            action: string;
            /** Link Ids */
            link_ids: string[];
        };
        /** Body_import_files_api_news_import_post */
        Body_import_files_api_news_import_post: {
            /** Files */
            files: string[];
            /**
             * Score
             * @default true
             */
            score: boolean;
        };
        /** CollectorIn */
        CollectorIn: {
            /** Name */
            name: string;
            /** Prompt */
            prompt: string;
            /**
             * Provider Id
             * @description 单独指定模型；不填则跟随场景“资讯采集”的模型
             */
            provider_id?: string | null;
            /** Skill Id */
            skill_id?: string | null;
            schedule: components["schemas"]["ScheduleIn"];
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /**
             * Scope Kind
             * @description general=行业/主题采集；targeted=定向公司采集（目标公司作为识别提示，ADR 0016）。不填：新建为 general，修改时保持原值
             */
            scope_kind?: ("general" | "targeted") | null;
            /**
             * Target Company Ids
             * @description scope_kind=targeted 时的目标公司（公司档案 id），至少一个；不填保持原值
             */
            target_company_ids?: string[] | null;
            /**
             * Industry
             * @description 行业/主题，可选；不填保持原值
             */
            industry?: string | null;
        };
        /** CompanyNewsItemOut */
        CompanyNewsItemOut: {
            /** Link Id */
            link_id: string;
            /** Event Id */
            event_id: string;
            /** Title */
            title: string;
            /** Summary */
            summary: string;
            /** Published At */
            published_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "proposed" | "confirmed";
            /** Relevance */
            relevance: number | null;
            /** Impact */
            impact: number | null;
            /** Key Point */
            key_point: string;
            /** Evidence */
            evidence: string;
            /** Match Method */
            match_method: ("ticker" | "alias" | "contains") | null;
            /**
             * Url
             * @description 代表性原文链接
             */
            url: string | null;
        };
        /** CompanyNewsOut */
        CompanyNewsOut: {
            /** Company Id */
            company_id: string;
            /** Items */
            items: components["schemas"]["CompanyNewsItemOut"][];
            /**
             * Next Cursor
             * @description 下一页游标；null = 没有更多
             */
            next_cursor: string | null;
        };
        /** CreateIn */
        CreateIn: {
            /** Company Id */
            company_id: string;
            /** Dimension */
            dimension: string;
            /** Rubric Ref */
            rubric_ref: string;
            /** Criterion */
            criterion: string;
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
            /**
             * Period End
             * Format: date
             */
            period_end: string;
            /** Grade */
            grade: number;
            /** Confidence */
            confidence: number | string;
            /** Reason */
            reason: string;
            /**
             * Effective From
             * Format: date-time
             */
            effective_from: string;
            /**
             * Valid Until
             * Format: date-time
             */
            valid_until: string;
            /** Evidence */
            evidence: components["schemas"]["EvidenceIn"][];
        };
        /** EventOut */
        EventOut: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Summary */
            summary: string;
            /** Category */
            category: string | null;
            /** First Published At */
            first_published_at: string | null;
            /** Last Published At */
            last_published_at: string | null;
            /** Item Count */
            item_count: number;
            /** Ai Status */
            ai_status: string;
            /** Ai Model */
            ai_model: string | null;
            /** Ai Error */
            ai_error: string | null;
            /** Impact Score */
            impact_score: number | null;
            /** Links */
            links: components["schemas"]["LinkOut"][];
            /** Items */
            items?: components["schemas"]["ItemOut"][] | null;
        };
        /** EvidenceIn */
        EvidenceIn: {
            /** Source Revision Id */
            source_revision_id: string;
            /** Hash */
            hash: string;
            /** Start */
            start: number;
            /** End */
            end: number;
            /** Quote */
            quote: string;
            /**
             * Relation
             * @default supports
             * @enum {string}
             */
            relation: "supports" | "contradicts";
        };
        /** FeedIn */
        FeedIn: {
            /** Feed Key */
            feed_key: string;
            /** Name */
            name: string;
            /**
             * Kind
             * @default rss
             */
            kind: string;
            /** Url */
            url?: string | null;
            /** Schedule */
            schedule?: string | null;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        /** FormalRow */
        FormalRow: {
            /** Seal Id */
            seal_id: string;
            /** Security Id */
            security_id: string;
            /** Ticker */
            ticker: string;
            /** Currency */
            currency: string;
            /** Release Id */
            release_id: string;
            /** Market Session */
            market_session: string;
            /** Phase */
            phase: string;
            /**
             * Evaluation As Of
             * Format: date-time
             */
            evaluation_as_of: string;
            /**
             * Knowledge Cutoff
             * Format: date-time
             */
            knowledge_cutoff: string;
            /** Generated At */
            generated_at?: string | null;
            /** Evaluation Id */
            evaluation_id?: string | null;
            /** Manifest Hash */
            manifest_hash?: string | null;
            /** Validity */
            validity?: string | null;
            /** Application */
            application?: string | null;
            /** Membership */
            membership?: string | null;
            /**
             * Gaps
             * @default []
             */
            gaps: string[];
        };
        /** FormalStatus */
        FormalStatus: {
            /** Available */
            available: boolean;
            /** Reason */
            reason?: string | null;
            /** Rows */
            rows: components["schemas"]["FormalRow"][];
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** ItemOut */
        ItemOut: {
            /** Id */
            id: string;
            /** Feed */
            feed: string | null;
            /** Title */
            title: string;
            /** Summary */
            summary: string;
            /** Source Text */
            source_text: string | null;
            /** Url */
            url: string | null;
            /** Company Hint */
            company_hint: string | null;
            /** Note */
            note: string | null;
            /** Published At */
            published_at: string | null;
        };
        /** LinkOut */
        LinkOut: {
            /** Alerts */
            alerts?: number | null;
            /** Id */
            id: string;
            /** Company Id */
            company_id: string | null;
            /** Company */
            company: string;
            /** Company Label */
            company_label: string;
            /** Ticker Hint */
            ticker_hint: string | null;
            /** Relevance */
            relevance: number | null;
            /** Impact */
            impact: number | null;
            /** Rationale */
            rationale: string;
            /** Status */
            status: string;
            /** Proposed By */
            proposed_by: string;
            /** Reviewed At */
            reviewed_at: string | null;
        };
        /** LoginIn */
        LoginIn: {
            /** Login */
            login: string;
            /** Password */
            password: string;
        };
        /** MatchEstimateOut */
        MatchEstimateOut: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "rematch" | "reassess";
            /** Events */
            events: number;
            /**
             * Estimated Calls
             * @description 预计调用大模型次数；rematch 为 0
             */
            estimated_calls: number;
        };
        /** MatchJobIn */
        MatchJobIn: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "rematch" | "reassess";
            /**
             * Date From
             * @description 按事件最后发布时间筛选（北京时间日期，含）
             */
            date_from?: string | null;
            /**
             * Date To
             * @description 含当天
             */
            date_to?: string | null;
            /**
             * Event Ids
             * @description 只处理这些事件；与日期范围可同时给出（取交集）
             */
            event_ids?: string[] | null;
        };
        /** MatchJobOut */
        MatchJobOut: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "rematch" | "reassess";
            /** Params */
            params: {
                [key: string]: unknown;
            };
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed" | "cancelled";
            /** Total */
            total: number;
            /** Processed */
            processed: number;
            /** Links Added */
            links_added: number;
            /** Links Updated */
            links_updated: number;
            /** Estimated Calls */
            estimated_calls: number;
            /** Error */
            error: string | null;
            /** Created By */
            created_by: string | null;
            /** Created At */
            created_at: string;
            /** Started At */
            started_at: string | null;
            /** Finished At */
            finished_at: string | null;
        };
        /** MatchJobPage */
        MatchJobPage: {
            /** Items */
            items: components["schemas"]["MatchJobOut"][];
            /** Total */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** MentionListOut */
        MentionListOut: {
            /** Event Id */
            event_id: string;
            /**
             * Extract Status
             * @enum {string}
             */
            extract_status: "pending" | "done" | "rule_only" | "failed";
            /** Extract Version */
            extract_version: string | null;
            /** Extracted At */
            extracted_at: string | null;
            /** Items */
            items: components["schemas"]["MentionOut"][];
        };
        /** MentionOut */
        MentionOut: {
            /** Id */
            id: string;
            /** Event Id */
            event_id: string;
            /**
             * Name
             * @description 原文写法
             */
            name: string;
            /** Name Norm */
            name_norm: string;
            /** Ticker Raw */
            ticker_raw: string | null;
            /** Ticker Norm */
            ticker_norm: string | null;
            /** Market */
            market: ("SH" | "SZ" | "BJ" | "HK" | "US") | null;
            /**
             * Relevance
             * @description 0..1
             */
            relevance: number | null;
            /**
             * Impact
             * @description -1..1
             */
            impact: number | null;
            /**
             * Key Point
             * @description ≤80 字要点
             */
            key_point: string;
            /**
             * Evidence
             * @description 原文证据（短引文）
             */
            evidence: string;
            /**
             * Extractor
             * @description llm:<provider>/<model>@news-extract:v1 | rule:v1
             */
            extractor: string;
            /**
             * Company Id
             * @description 第二段匹配到的关注公司；null = 未关注或未匹配
             */
            company_id: string | null;
            /** Link Id */
            link_id: string | null;
            /** Link Status */
            link_status: ("proposed" | "confirmed" | "rejected") | null;
            /** Match Method */
            match_method: ("ticker" | "alias" | "contains") | null;
            /** Created At */
            created_at: string;
        };
        /** ModelPresetOut */
        ModelPresetOut: {
            /** Provider Key */
            provider_key: string;
            /** Name */
            name: string;
            /** Vendor */
            vendor: string;
            /** Base Url */
            base_url: string;
            /** Model */
            model: string;
            /** Api Key Env */
            api_key_env: string;
            /** Search Mode */
            search_mode: string;
            /** Note */
            note: string;
            /** Doc Url */
            doc_url: string;
            /**
             * Reasoning Style
             * @description openai | deepseek；空 = 不发送推理强度
             */
            reasoning_style?: string | null;
            /**
             * Reasoning Efforts
             * @description 该预设允许的推理强度
             */
            reasoning_efforts?: string[];
            /**
             * Model Reasoning Efforts
             * @description 按模型名覆盖允许的推理强度
             */
            model_reasoning_efforts?: {
                [key: string]: string[];
            };
        };
        /** ModelPresetsOut */
        ModelPresetsOut: {
            /** Version */
            version: number;
            /** Verified On */
            verified_on: string;
            /** Items */
            items: components["schemas"]["ModelPresetOut"][];
            /**
             * Search Modes
             * @description 联网方式 → 中文名
             */
            search_modes: {
                [key: string]: string;
            };
        };
        /** NoteIn */
        NoteIn: {
            /** Company Id */
            company_id: string;
            /** Body */
            body: string;
        };
        /** OverrideIn */
        OverrideIn: {
            /** Value */
            value: {
                [key: string]: unknown;
            };
            /**
             * Release
             * @default false
             */
            release: boolean;
        };
        /** PasswordIn */
        PasswordIn: {
            /** Current */
            current: string;
            /** New */
            new: string;
        };
        /** PasswordReset */
        PasswordReset: {
            /**
             * Password
             * @description 留空则生成一次性密码
             */
            password?: string | null;
        };
        /** PresetInstallIn */
        PresetInstallIn: {
            /**
             * Provider Id
             * @description 给这些定时器单独指定的能联网模型；不填则定时器跟随场景“资讯采集”的模型
             */
            provider_id?: string | null;
            /**
             * Keys
             * @description 只导入这些预置任务（不填则全部）
             */
            keys?: string[] | null;
        };
        /** PresetInstallOut */
        PresetInstallOut: {
            /** Version */
            version: number;
            /** Skill Id */
            skill_id: string;
            /** Skill Created */
            skill_created: boolean;
            /** Provider Id */
            provider_id: string | null;
            /** Follows Scene */
            follows_scene: boolean;
            /** Created */
            created: components["schemas"]["PresetRef"][];
            /** Skipped */
            skipped: components["schemas"]["PresetRef"][];
        };
        /** PresetListOut */
        PresetListOut: {
            /** Version */
            version: number;
            /** Name */
            name: string;
            /** Description */
            description: string;
            skill: components["schemas"]["PresetSkillOut"];
            /** Items */
            items: components["schemas"]["PresetTaskOut"][];
            /** Total */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** PresetRef */
        PresetRef: {
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Task Id */
            task_id: string;
        };
        /** PresetScheduleOut */
        PresetScheduleOut: {
            /** Type */
            type: string;
            /** Times */
            times?: string[] | null;
            /** Weekdays */
            weekdays?: number[] | null;
            /** Minutes */
            minutes?: number | null;
        };
        /** PresetSkillOut */
        PresetSkillOut: {
            /** Skill Key */
            skill_key: string;
            /** Name */
            name: string;
            /** Description */
            description: string;
            /** Installed */
            installed: boolean;
            /** Skill Id */
            skill_id: string | null;
        };
        /** PresetTaskOut */
        PresetTaskOut: {
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Prompt */
            prompt: string;
            /** Merged From */
            merged_from: string[];
            schedule: components["schemas"]["PresetScheduleOut"];
            /** Schedule Text */
            schedule_text: string;
            /** Installed */
            installed: boolean;
            /** Task Id */
            task_id: string | null;
        };
        /** ProposalIn */
        ProposalIn: {
            /** Company Id */
            company_id: string;
            /** Dimension */
            dimension: string;
            /** Rubric Ref */
            rubric_ref: string;
            /** Criterion */
            criterion: string;
            /**
             * Period Start
             * Format: date
             */
            period_start: string;
            /**
             * Period End
             * Format: date
             */
            period_end: string;
            /** Grade */
            grade: number;
            /** Confidence */
            confidence: number | string;
            /** Reason */
            reason: string;
            /**
             * Effective From
             * Format: date-time
             */
            effective_from: string;
            /**
             * Valid Until
             * Format: date-time
             */
            valid_until: string;
            /** Evidence */
            evidence: components["schemas"]["EvidenceIn"][];
            /**
             * Research Method
             * @default local_evidence_review
             * @constant
             */
            research_method: "local_evidence_review";
            /** Author Label */
            author_label: string;
            /** Limitations */
            limitations: string;
        };
        /** ProviderIn */
        ProviderIn: {
            /** Provider Key */
            provider_key: string;
            /** Name */
            name: string;
            /** Base Url */
            base_url: string;
            /** Model */
            model: string;
            /**
             * Api Key Env
             * @description 可选：密钥所在的环境变量名（页面保存的 Key 优先）
             */
            api_key_env?: string | null;
            /**
             * Api Key
             * @description 只写：在页面填写的 API Key，加密后入库，任何接口都不再返回；留空表示不修改
             */
            api_key?: string | null;
            /**
             * Is Default
             * @default false
             */
            is_default: boolean;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /**
             * Temperature
             * @default 0
             */
            temperature: number;
            /**
             * Search Mode
             * @default none
             */
            search_mode: string;
        };
        /** PublishIn */
        PublishIn: {
            /** Expected Version */
            expected_version?: number | null;
            /**
             * Quality Threshold
             * @default 70
             */
            quality_threshold: string;
            /** Simulation Token */
            simulation_token?: string | null;
        };
        /** ReviewIn */
        ReviewIn: {
            /** Action */
            action: string;
            /** Relevance */
            relevance?: number | null;
            /** Impact */
            impact?: number | null;
            /** Company Id */
            company_id?: string | null;
        };
        /** RolesIn */
        RolesIn: {
            /** Roles */
            roles: string[];
        };
        /** RunDetail */
        RunDetail: {
            /** Id */
            id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "partial" | "completed";
            /** Manifest Hash */
            manifest_hash: string;
            /** Created At */
            created_at: string;
            /** Manifest */
            manifest: {
                [key: string]: unknown;
            };
            /** Result */
            result: {
                [key: string]: unknown;
            };
        };
        /** RunIn */
        RunIn: {
            /** Source Key */
            source_key: string;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** RunSummary */
        RunSummary: {
            /** Id */
            id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "partial" | "completed";
            /** Manifest Hash */
            manifest_hash: string;
            /** Created At */
            created_at: string;
        };
        /** SceneBindingIn */
        SceneBindingIn: {
            /**
             * Scene
             * @description 场景键；旧键 news_analysis 等同 news_extract
             */
            scene: string;
            /**
             * Provider Id
             * @description 不填 = 使用默认模型
             */
            provider_id?: string | null;
            /**
             * Reasoning Effort
             * @description 推理强度；不填 = 场景推荐强度。须在所选模型允许的强度内（allowed_efforts_by_provider），且需要指定模型
             */
            reasoning_effort?: ("none" | "low" | "medium" | "high" | "xhigh" | "max") | null;
        };
        /** SceneBindingsIn */
        SceneBindingsIn: {
            /** Bindings */
            bindings: components["schemas"]["SceneBindingIn"][];
        };
        /** SceneModelOut */
        SceneModelOut: {
            /** Id */
            id: string | null;
            /** Name */
            name: string;
            /** Model */
            model: string;
            /** Search Mode */
            search_mode: string;
            /** Key Configured */
            key_configured: boolean;
            /** Key Source */
            key_source: string;
        };
        /** SceneOut */
        SceneOut: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Description */
            description: string;
            /**
             * Aliases
             * @description 旧场景键，读取与保存时自动换成 key
             */
            aliases: string[];
            /**
             * Status
             * @description active=已有调用代码 | planned=接口已定、调用代码在 planned_in 的 PR 落地
             */
            status: string;
            /** Planned In */
            planned_in: string | null;
            /** Requires Search */
            requires_search: boolean;
            /** Provider Id */
            provider_id: string | null;
            /**
             * Reasoning Effort
             * @description 场景绑定里填的推理强度；null = 按推荐
             */
            reasoning_effort: string | null;
            /**
             * Effective Reasoning Effort
             * @description 实际会发送的强度（已按厂商映射并过滤）；null = 不发送
             */
            effective_reasoning_effort: string | null;
            /**
             * Effort Source
             * @description scene=场景绑定 | provider_options=模型自身配置 | recommended=场景推荐 | none
             */
            effort_source: string;
            /**
             * Allowed Efforts
             * @description 当前生效模型允许的推理强度
             */
            allowed_efforts: string[];
            /**
             * Recommended
             * @description 推荐模型与强度，第一项为首选
             */
            recommended: components["schemas"]["SceneRecommendationOut"][];
            /** Cost Note */
            cost_note: string;
            /**
             * Source
             * @description scene=场景绑定 | workspace_default=工作区默认模型 | builtin=内置默认
             */
            source: string;
            effective: components["schemas"]["SceneModelOut"];
            /** Problem */
            problem: string | null;
        };
        /** SceneRecommendationOut */
        SceneRecommendationOut: {
            /**
             * Preset
             * @description config/model-presets-v1.json 的 provider_key
             */
            preset: string;
            /** Preset Name */
            preset_name: string;
            /** Model */
            model: string;
            /** Reasoning Effort */
            reasoning_effort: string | null;
            /** Why */
            why: string;
        };
        /** ScenesOut */
        ScenesOut: {
            /** Version */
            version: number;
            /**
             * Efforts
             * @description 全部推理强度取值
             */
            efforts: string[];
            /**
             * Allowed Efforts By Provider
             * @description 本工作区每个模型（id）允许的推理强度；空列表 = 该模型不发送推理强度
             */
            allowed_efforts_by_provider: {
                [key: string]: string[];
            };
            /** Items */
            items: components["schemas"]["SceneOut"][];
        };
        /** ScheduleIn */
        ScheduleIn: {
            /** Type */
            type: string;
            /** Times */
            times?: string[] | null;
            /** Weekdays */
            weekdays?: number[] | null;
            /** Minutes */
            minutes?: number | null;
        };
        /** ScoreIn */
        ScoreIn: {
            /** Event Ids */
            event_ids?: string[] | null;
            /**
             * Limit
             * @default 20
             */
            limit: number;
        };
        /** SecurityRef */
        SecurityRef: {
            /** Market */
            market: string;
            /** Ticker */
            ticker: string;
        };
        /** SettingIn */
        SettingIn: {
            /** Email */
            email?: string | null;
            /**
             * Email Enabled
             * @default true
             */
            email_enabled: boolean;
            /**
             * Inapp Enabled
             * @default true
             */
            inapp_enabled: boolean;
        };
        /** SkillIn */
        SkillIn: {
            /** Skill Key */
            skill_key: string;
            /** Name */
            name: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** Body */
            body: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        /** SuggestedAddIn */
        SuggestedAddIn: {
            /** Name Norm */
            name_norm: string;
            /**
             * Name
             * @description 新建公司时用的名称；不填取最常见写法
             */
            name?: string | null;
            /** Ticker */
            ticker?: string | null;
        };
        /** SuggestedAddOut */
        SuggestedAddOut: {
            watch: components["schemas"]["WatchCompanyOut"];
            /** Company Created */
            company_created: boolean;
            /** Aliases Added */
            aliases_added: number;
        };
        /** SuggestedCompanyOut */
        SuggestedCompanyOut: {
            /** Name */
            name: string;
            /** Name Norm */
            name_norm: string;
            /** Ticker Norm */
            ticker_norm: string | null;
            /** Market */
            market: ("SH" | "SZ" | "BJ" | "HK" | "US") | null;
            /**
             * Events
             * @description 近 days 天内提及它的事件数
             */
            events: number;
            /** Last Seen At */
            last_seen_at: string | null;
            /** Sample Event Ids */
            sample_event_ids: string[];
            /**
             * Company Id
             * @description 公司档案里已有（但本工作区未关注）时的公司 id
             */
            company_id: string | null;
        };
        /** SuggestedCompanyPage */
        SuggestedCompanyPage: {
            /** Min Events */
            min_events: number;
            /** Days */
            days: number;
            /** Items */
            items: components["schemas"]["SuggestedCompanyOut"][];
            /** Total */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** TemplateIn */
        TemplateIn: {
            /** Expected Version */
            expected_version?: number | null;
            /** Patches */
            patches: {
                [key: string]: unknown;
            }[];
        };
        /** UserCreate */
        UserCreate: {
            /**
             * Login
             * @description 登录名，一般用邮箱
             */
            login: string;
            /** Display Name */
            display_name: string;
            /** Roles */
            roles: string[];
            /**
             * Password
             * @description 留空则生成一次性初始密码
             */
            password?: string | null;
        };
        /** UserPatch */
        UserPatch: {
            /** Display Name */
            display_name?: string | null;
            /** Disabled */
            disabled?: boolean | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** WatchCompanyIn */
        WatchCompanyIn: {
            /**
             * Company Id
             * @description 关注已有公司；与 name 二选一
             */
            company_id?: string | null;
            /**
             * Name
             * @description 公司档案里没有时按名称新建
             */
            name?: string | null;
            /**
             * Tickers
             * @description 新建公司时的证券代码，如 688428.SH、09969.HK
             */
            tickers?: string[];
            /** Aliases */
            aliases?: components["schemas"]["AliasIn"][];
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** WatchCompanyOut */
        WatchCompanyOut: {
            /** Id */
            id: string;
            /** Company Id */
            company_id: string;
            /**
             * Company
             * @description 公司名
             */
            company: string;
            /** Securities */
            securities: components["schemas"]["SecurityRef"][];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "archived";
            /** Note */
            note: string;
            /** Alias Count */
            alias_count: number;
            /**
             * Links 30D
             * @description 近 30 天关联（确认 + 待确认）的事件数
             */
            links_30d: number;
            /** Added By */
            added_by: string | null;
            /** Added At */
            added_at: string;
        };
        /** WatchCompanyPage */
        WatchCompanyPage: {
            /** Items */
            items: components["schemas"]["WatchCompanyOut"][];
            /** Total */
            total: number;
            /** Limit */
            limit: number;
            /** Offset */
            offset: number;
        };
        /** WatchCompanyPatch */
        WatchCompanyPatch: {
            /** Status */
            status?: ("active" | "archived") | null;
            /** Note */
            note?: string | null;
        };
        /** ZoneBoard */
        ZoneBoard: {
            /** As Of */
            as_of: string;
            /** Policy */
            policy: {
                [key: string]: unknown;
            };
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Rows */
            rows: components["schemas"]["ZoneRow"][];
        };
        /** ZoneCheck */
        ZoneCheck: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Passed */
            passed: boolean | null;
            /** Detail */
            detail: string;
        };
        /** ZoneRow */
        ZoneRow: {
            /** Company Id */
            company_id: string;
            /** Company */
            company: string;
            /** Industry Key */
            industry_key: string;
            /** Security Id */
            security_id: string;
            /** Ticker */
            ticker: string;
            /** Market */
            market: string;
            /** Quality Score */
            quality_score?: number | null;
            /** Coverage */
            coverage?: string | null;
            /** Valuation Score */
            valuation_score?: number | null;
            /** Pe Ttm */
            pe_ttm?: number | null;
            /** Zone */
            zone: string;
            /** Label */
            label: string;
            /** Margin Of Safety */
            margin_of_safety?: string | null;
            /** Checks */
            checks: components["schemas"]["ZoneCheck"][];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    status_api_strategy_seals_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FormalStatus"];
                };
            };
        };
    };
    list_runs_api_research_runs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunSummary"][];
                };
            };
        };
    };
    run_api_research_runs_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_api_research_runs__run_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_identities_api_identities_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    me_api_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    auth_state_api_auth_state_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    login_api_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    change_password_api_auth_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_runs_api_demo_runs_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_run_api_demo_runs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_audit_api_demo_audit_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    read_outbox_api_demo_outbox_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    mark_dispatched_api_demo_outbox__outbox_id__dispatch_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                outbox_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ingest_synthetic_api_intake_synthetic_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_items_api_intake_items_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    get_item_api_intake_items__item_id__get: {
        parameters: {
            query?: {
                revision_id?: string | null;
            };
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_companies_api_companies_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    company_timeline_api_companies__company_id__timeline_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_auto_api_judgments_auto_run_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_effective_api_judgments_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_judgment_api_judgments_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    propose_judgment_api_judgments_proposals_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProposalIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rubric_catalog_api_judgments_catalog__company_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    override_api_judgments__slot_key__override_post: {
        parameters: {
            query?: never;
            header: {
                "If-Match-Generation": number;
                "Idempotency-Key"?: string | null;
            };
            path: {
                slot_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OverrideIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    company_score_api_companies__company_id__score_get: {
        parameters: {
            query?: {
                as_of?: string | null;
                cutoff?: string | null;
            };
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    current_api_strategy_current_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    simulate_api_strategy_simulate_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PublishIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_api_strategy_publish_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PublishIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_golden_api_strategy_run_golden_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    transitions_api_strategy_transitions_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    evaluation_api_strategy_evaluations__evaluation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                evaluation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_api_templates__company_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_api_templates__company_id__preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_api_templates__company_id__publish_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    add_watch_api_me_watchlist__security_id__post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                security_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_watch_api_me_watchlist__security_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                security_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_watch_api_me_watchlist_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_notes_api_me_notes_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    add_note_api_me_notes_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NoteIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    claim_outbox_api_worker_outbox__outbox_id__claim_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                outbox_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    tasks_api_worker_tasks_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    retry_api_worker_outbox__outbox_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                outbox_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    source_runs_api_worker_sources_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    get_policy_api_strike_zone_policy_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
    board_api_strike_zone_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ZoneBoard"];
                };
            };
        };
    };
    company_api_strike_zone_companies__company_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ZoneRow"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sources_api_admin_sources_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    }[];
                };
            };
        };
    };
    list_feeds_api_admin_news_feeds_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_feed_api_admin_news_feeds_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_feed_api_admin_news_feeds__feed_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feed_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FeedIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_providers_api_admin_llm_providers_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_provider_api_admin_llm_providers_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProviderIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    llm_presets_api_admin_llm_presets_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelPresetsOut"];
                };
            };
        };
    };
    update_provider_api_admin_llm_providers__provider_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProviderIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    clear_provider_key_api_admin_llm_providers__provider_id__api_key_delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                provider_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    model_scene_list_api_admin_model_scenes_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenesOut"];
                };
            };
        };
    };
    model_scene_save_api_admin_model_scenes_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SceneBindingsIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenesOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    notify_settings_api_admin_notify_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    roles_api_admin_roles_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    list_users_api_admin_users_get: {
        parameters: {
            query?: {
                q?: string | null;
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_user_api_admin_users_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_user_api_admin_users__user_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user_api_admin_users__user_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    set_roles_api_admin_users__user_id__roles_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RolesIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_password_api_admin_users__user_id__password_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordReset"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sign_out_api_admin_users__user_id__sign_out_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    audit_api_admin_audit_get: {
        parameters: {
            query?: {
                /** @description 按动作前缀过滤，如 identity. */
                action?: string | null;
                /** @description 操作人登录名 */
                actor?: string | null;
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    events_api_news_events_get: {
        parameters: {
            query?: {
                company_id?: string | null;
                status?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    event_api_news_events__event_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    import_files_api_news_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_import_files_api_news_import_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    score_api_news_score_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScoreIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_api_news_links__link_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                link_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LinkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_batch_api_news_links_review_batch_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BatchReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_feed_api_news_feeds__feed_id__run_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                feed_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    feeds_api_news_feeds_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    alerts_api_alerts_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    scan_api_alerts_scan_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    my_notifications_api_notifications_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_one_api_notifications__notification_id__read_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                notification_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_all_api_notifications_read_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    get_settings__api_notifications_settings_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    put_settings_api_notifications_settings_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SettingIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    skills_api_admin_skills_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_skill_api_admin_skills_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SkillIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_skill_api_admin_skills__skill_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                skill_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SkillIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_skill_api_admin_skills__skill_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                skill_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collectors_api_admin_collectors_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    create_collector_api_admin_collectors_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CollectorIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collector_options_api_admin_collectors_options_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    collector_presets_list_api_admin_collectors_presets_get: {
        parameters: {
            query?: {
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PresetListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collector_presets_install_api_admin_collectors_presets_install_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PresetInstallIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PresetInstallOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_collector_api_admin_collectors__task_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CollectorIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    run_collector_api_admin_collectors__task_id__run_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    collector_runs_api_admin_collectors__task_id__runs_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    watch_list_api_watchlist_companies_get: {
        parameters: {
            query?: {
                status?: ("active" | "archived") | null;
                q?: string | null;
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WatchCompanyPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    watch_add_api_watchlist_companies_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WatchCompanyIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WatchCompanyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    watch_delete_api_watchlist_companies__watch_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                watch_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    watch_update_api_watchlist_companies__watch_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                watch_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WatchCompanyPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WatchCompanyOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    alias_list_api_companies__company_id__aliases_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AliasListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    alias_add_api_companies__company_id__aliases_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AliasIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AliasOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    alias_delete_api_companies__company_id__aliases__alias_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                company_id: string;
                alias_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    company_news_api_companies__company_id__news_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                company_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompanyNewsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    event_mentions_api_news_events__event_id__mentions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MentionListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    suggested_api_news_suggested_companies_get: {
        parameters: {
            query?: {
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuggestedCompanyPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    suggested_add_api_news_suggested_companies_add_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SuggestedAddIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuggestedAddOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    match_estimate_api_news_match_jobs_estimate_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MatchJobIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchEstimateOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    match_jobs_api_news_match_jobs_get: {
        parameters: {
            query?: {
                /** @description 每页条数 */
                limit?: number;
                /** @description 跳过条数 */
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchJobPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    match_job_create_api_news_match_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MatchJobIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchJobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    match_job_api_news_match_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchJobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    match_job_cancel_api_news_match_jobs__job_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MatchJobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 契约已发布、实现尚未合入（错误码 not_implemented） */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    api_root_api_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
}
