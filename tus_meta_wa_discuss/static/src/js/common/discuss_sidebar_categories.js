/* @odoo-module */

import { discussSidebarCategoriesRegistry } from "@mail/discuss/core/web/discuss_sidebar_categories";

discussSidebarCategoriesRegistry.add(
    "WpChannels",
    {
//        predicate: (store) => store.discuss.WpChannels.threads.some((thread) => thread?.is_pinned),
        value: (store) => store.discuss.WpChannels,
     },
    { sequence: 30 }
);