/* @odoo-module */

import { DiscussApp } from "@mail/core/common/discuss_app_model";
import { Record } from "@mail/core/common/record";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers


patch(OutOfFocusService.prototype, {
   async notify(message, channel) {
        const modelsHandleByPush = ["mail.thread", "discuss.channel"];
        if (
            modelsHandleByPush.includes(message.model) &&
            (await this.hasServiceWorkInstalledAndPushSubscriptionActive())
        ) {
            return;
        }
        const author = message.author;
        let notificationTitle;
        if (!author) {
            notificationTitle = _t("New message");
        } else {
            if (channel.channel_type === "channel") {
                notificationTitle = _t("%(author name)s from %(channel name)s", {
                    "author name": author.name,
                    "channel name": channel.displayName,
                });
            } else {
                notificationTitle = author.name;
            }
        }
        var message = message.body || '';
        const notificationContent = htmlToTextContentInline(message).substring(
            0,
            PREVIEW_MSG_MAX_SIZE
        );
        this.sendNotification({
            message: notificationContent,
            title: notificationTitle,
            type: "info",
        });
    }
});

patch(DiscussApp, {
    new(data) {
        const res = super.new(data);
        res.WpChannels = {
            extraClass: "o-mail-DiscussSidebarCategory-tus-WpChannels",
            id: "WpChannels",
            name: _t("WhatsApp Messages"),
            isOpen: false,
            canView: false,
            canAdd: true,
            addTitle: _t("Start a Whatsapp Conversion"),
            serverStateKey: "is_discuss_sidebar_category_whatsapp_open",
            addHotkey: "w",
        };
        return res;
    },

});

patch(DiscussApp.prototype, {

     setup(env) {
        super.setup(env);
        this.WpChannels = Record.one("DiscussAppCategory");
    },
});


