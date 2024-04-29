/* @odoo-module */
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Dialog } from "@web/core/dialog/dialog";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { View } from "@web/views/view";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { htmlToTextContentInline } from "@mail/utils/common/format";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {string} [className]
 * @extends {Component<Props, Env>}
 */
export class AgentListPanel extends Component {
    static components = {
        ActionPanel,
        View,
    };
    static props = ["className?"];
    static template = "discuss.AgentListPanel";

    setup() {
        this.store = useService("mail.store");
        this.rpc = useService("rpc");
        const buttonTemplate = "web.FormViewDialog.ToMany.buttons";
        this.AgentListService = useState(useService("discuss.AgentListPanel"));
        if (this.props.thread && this.props.thread.correspondent){ this.activeID = this.props.thread.correspondent.id}
        else if (this.props.thread && this.props.thread.correspondents){ this.activeID = this.props.thread.correspondents[0].id}
        this.viewProps = {
            type: "form",
            buttonTemplate,

            context: this.props.context || {},
//            display: { controlPanel: true },
            mode: "edit",
            resId: this.activeID || false,
            resModel: 'res.partner',
            preventCreate: this.props.preventCreate,
            preventEdit: this.props.preventEdit,
            discardRecord: this.discardRecord.bind(this),
            saveRecord: async (record, { saveAndNew }) => {
                const saved = await record.save({ reload: false });
                if (saved) {
                    await this.props.onRecordSaved(record);
                    if (saveAndNew) {
                        const context = Object.assign({}, this.props.context);
                        Object.keys(context).forEach((k) => {
                            if (k.startsWith("default_")) {
                                delete context[k];
                            }
                        });
                        await record.model.load({ resId: false, context });
                    }
                }
                return saved;
            },
        };
    }

    async discardRecord() {
        if (this.props.onRecordDiscarded) {
            await this.props.onRecordDiscarded();
        }
    }

    /**
     * Prompt the user for confirmation and unpin the given message if
     * confirmed.
     *
     * @param {import('@mail/core/common/message_model').Message} message
     */
    onClickUnpin(message) {
        this.AgentListService.unpin(message);
    }

    /**
     * Get the message to display when nothing is pinned on this thread.
     */
    get emptyText() {
        if (this.props.thread.type === "channel") {
            return _t("This channel doesn't have any pinned messages.");
        } else {
            return _t("This conversation doesn't have any pinned messages.");
        }
    }

    get title() {
        return _t("Contact");
    }
}

AgentListPanel.props = {
    thread: { type: Object, optional: true },

    context: { type: Object, optional: true },
    mode: {
        optional: true,
        validate: (m) => ["edit", "readonly"].includes(m),
    },
    onRecordSaved: { type: Function, optional: true },
    onRecordDiscarded: { type: Function, optional: true },
    removeRecord: { type: Function, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    title: { type: String, optional: true },
    viewId: { type: [Number, Boolean], optional: true },
    preventCreate: { type: Boolean, optional: true },
    preventEdit: { type: Boolean, optional: true },
    isToMany: { type: Boolean, optional: true },
    size: Dialog.props.size,
};
AgentListPanel.defaultProps = {
    onRecordSaved: () => {},
    preventCreate: true,
    preventEdit: false,
    isToMany: false,
};