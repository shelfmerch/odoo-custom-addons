/* @odoo-module */

import { url } from "@web/core/utils/urls";
import { patch } from "@web/core/utils/patch";
import { AND, Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { assignDefined, assignIn } from "@mail/utils/common/misc";
import { ThreadService } from "@mail/core/common/thread_service";

patch(Thread.prototype, {
    update(data) {
        const { id, name, attachments, description, ...serverData } = data;
        assignDefined(this, { id, name, description });
        if (attachments) {
            this.attachments = attachments;
        }
        if (serverData) {
            assignDefined(this, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "avatarCacheKey",
                "description",
                "hasWriteAccess",
                "is_pinned",
                "isLoaded",
                "isLoadingAttachments",
                "mainAttachment",
                "message_unread_counter",
                "message_needaction_counter",
                "name",
                "seen_message_id",
                "state",
                "type",
                "status",
                "group_based_subscription",
                "last_interest_dt",
                "custom_notifications",
                "mute_until_dt",
                "is_editable",
                "defaultDisplayMode",
            ]);
            assignIn(this, data, [
                "custom_channel_name",
                "memberCount",
                "channelMembers",
                "invitedMembers",
            ]);
            if ("channel_type" in data) {
                this.type = data.channel_type;
            }
            if ("channelMembers" in data) {
                if (this.type === "chat" || this.type === "WpChannels") {
                    for (const member of this.channelMembers) {
                        if (
                            member.persona.notEq(this._store.user) ||
                            (this.channelMembers.length === 1 &&
                                member.persona?.eq(this._store.user))
                        ) {
                            this.chatPartner = member.persona;
                        }
                    }
                }
            }
            if ("seen_partners_info" in serverData) {
                this._store.ChannelMember.insert(
                    serverData.seen_partners_info.map(
                        ({ id, fetched_message_id, partner_id, guest_id, seen_message_id }) => ({
                            id,
                            persona: {
                                id: partner_id ?? guest_id,
                                type: partner_id ? "partner" : "guest",
                            },
                            lastFetchedMessage: fetched_message_id
                                ? { id: fetched_message_id }
                                : undefined,
                            lastSeenMessage: seen_message_id ? { id: seen_message_id } : undefined,
                        })
                    )
                );
            }
        }
        if (this.type === "channel") {
            this._store.discuss.channels.threads.add(this);
        } else if (this.type === "chat" || this.type === "group") {
            this._store.discuss.chats.threads.add(this);
        }
        if (!this.type && !["mail.box", "discuss.channel"].includes(this.model)) {
            this.type = "chatter";
        }
        if (this.type === "WpChannels") {
            this._store.discuss.WpChannels.threads.add(this);
        }
    return super.update(data);
    },
    get imgUrl() {
        if (this.type === "channel" || this.type === "group") {
            return url(
                `/discuss/channel/${this.id}/avatar_128`,
                assignDefined({}, { unique: this.avatarCacheKey })
            );
        }
        if (this.type === "chat" || this.type === "WpChannels") {
            if (this.chatPartner && this.chatPartner.id) {
                return url(
                    `/web/image/res.partner/${this.chatPartner.id}/avatar_128`,
                    assignDefined({}, { unique: this.chatPartner.write_date })
                );
            }
        }
        return super.imgUrl;
    },
});

patch(ThreadService.prototype, {
    /**
     *
     * @param {import("models").Thread} thread
     */
    canUnpin(thread) {
        return thread.type === "WpChannels" || thread.type === "chat" && this.getCounter(thread) === 0;
    }
});
