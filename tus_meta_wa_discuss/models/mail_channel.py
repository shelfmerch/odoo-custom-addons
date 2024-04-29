from odoo import _, api, fields, models, modules, tools, Command
import json
from collections import defaultdict
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.mail.models.discuss.discuss_channel import Channel
from odoo.osv import expression
from markupsafe import Markup


def _channel_info(self):
    """ Get the information header for the current channels
        :returns a list of updated channels values
        :rtype : list(dict)
    """
    if not self:
        return []
    channel_infos = []
    # sudo: discuss.channel.rtc.session - reading sessions of accessible channel is acceptable
    rtc_sessions_by_channel = self.sudo().rtc_session_ids._mail_rtc_session_format_by_channel(extra=True)
    current_partner, current_guest = self.env["res.partner"]._get_current_persona()
    self.env['discuss.channel'].flush_model()
    self.env['discuss.channel.member'].flush_model()
    # Query instead of ORM for performance reasons: "LEFT JOIN" is more
    # efficient than "id IN" for the cross-table condition between channel
    # (for channel_type) and member (for other fields).
    self.env.cr.execute("""
             SELECT discuss_channel_member.id
               FROM discuss_channel_member
          LEFT JOIN discuss_channel
                 ON discuss_channel.id = discuss_channel_member.channel_id
                AND discuss_channel.channel_type != 'channel'
              WHERE discuss_channel_member.channel_id in %(channel_ids)s
                AND (
                    discuss_channel.id IS NOT NULL
                 OR discuss_channel_member.rtc_inviting_session_id IS NOT NULL
                 OR discuss_channel_member.partner_id = %(current_partner_id)s
                 OR discuss_channel_member.guest_id = %(current_guest_id)s
                )
           ORDER BY discuss_channel_member.id ASC
    """, {'channel_ids': tuple(self.ids), 'current_partner_id': current_partner.id or None, 'current_guest_id': current_guest.id or None})
    all_needed_members = self.env['discuss.channel.member'].browse([m['id'] for m in self.env.cr.dictfetchall()])
    all_needed_members._discuss_channel_member_format()  # prefetch in batch
    members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    invited_members_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    member_of_current_user_by_channel = defaultdict(lambda: self.env['discuss.channel.member'])
    for member in all_needed_members:
        members_by_channel[member.channel_id] += member
        if member.rtc_inviting_session_id:
            invited_members_by_channel[member.channel_id] += member
        if (current_partner and member.partner_id == current_partner) or (current_guest and member.guest_id == current_guest):
            member_of_current_user_by_channel[member.channel_id] = member
    for channel in self:
        custom_channel = ''

        if channel._fields.get('whatsapp_channel'):
            if channel.whatsapp_channel:
                custom_channel += 'WpChannels'
        if channel._fields.get('instagram_channel'):
            if channel.instagram_channel:
                custom_channel += 'InstaChannels'
        if channel._fields.get('facebook_channel'):
            if channel.facebook_channel:
                custom_channel += 'FbChannels'

        if not custom_channel:
            info = {
                'avatarCacheKey': channel._get_avatar_cache_key(),
                'channel_type': channel.channel_type,
                'memberCount': channel.member_count,
                'id': channel.id,
                'name': channel.name,
                'defaultDisplayMode': channel.default_display_mode,
                'description': channel.description,
                'uuid': channel.uuid,
                'state': 'open',
                'is_editable': channel.is_editable,
                'is_minimized': False,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
                'authorizedGroupFullName': channel.group_public_id.full_name,
                'allow_public_upload': channel.allow_public_upload,
                'model': "discuss.channel",
            }
        else:
            info = {
                'avatarCacheKey': channel._get_avatar_cache_key(),
                'channel_type': custom_channel,
                'memberCount': channel.member_count,
                'id': channel.id,
                'name': channel.name,
                'defaultDisplayMode': channel.default_display_mode,
                'description': channel.description,
                'uuid': channel.uuid,
                'state': 'open',
                'is_editable': channel.is_editable,
                'is_minimized': False,
                'is_whatsapp': True,
                'group_based_subscription': bool(channel.group_ids),
                'create_uid': channel.create_uid.id,
                'authorizedGroupFullName': channel.group_public_id.full_name,
                'allow_public_upload': channel.allow_public_upload,
                'model': "discuss.channel",
            }
        # find the channel member state
        if current_partner or current_guest:
            info['message_needaction_counter'] = channel.message_needaction_counter
            member = member_of_current_user_by_channel.get(channel, self.env['discuss.channel.member']).with_prefetch([m.id for m in member_of_current_user_by_channel.values()])
            if member:
                info['channelMembers'] = [('ADD', list(member._discuss_channel_member_format().values()))]
                info['state'] = member.fold_state or 'open'
                info['message_unread_counter'] = member.message_unread_counter
                info['is_minimized'] = member.is_minimized
                info['custom_notifications'] = member.custom_notifications
                info['mute_until_dt'] = member.mute_until_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if member.mute_until_dt else False
                info['seen_message_id'] = member.seen_message_id.id
                info['custom_channel_name'] = member.custom_channel_name
                info['is_pinned'] = member.is_pinned
                info['last_interest_dt'] = member.last_interest_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if member.rtc_inviting_session_id:
                    info['rtc_inviting_session'] = {'id': member.rtc_inviting_session_id.id}
        # add members info
        if channel.channel_type != 'channel':
            # avoid sending potentially a lot of members for big channels
            # exclude chat and other small channels from this optimization because they are
            # assumed to be smaller and it's important to know the member list for them
            info['channelMembers'] = [('ADD', list(members_by_channel[channel]._discuss_channel_member_format().values()))]
            info['seen_partners_info'] = sorted([{
                'id': cm.id,
                'partner_id' if cm.partner_id else 'guest_id': cm.partner_id.id if cm.partner_id else cm.guest_id.id,
                'fetched_message_id': cm.fetched_message_id.id,
                'seen_message_id': cm.seen_message_id.id,
            } for cm in members_by_channel[channel]],
                key=lambda p: p.get('partner_id', p.get('guest_id')))
        # add RTC sessions info
        info.update({
            'invitedMembers': [('ADD', list(invited_members_by_channel[channel]._discuss_channel_member_format(
                fields={'id': True, 'channel': {}, 'persona': {'partner': {'id', 'name', 'im_status'}, 'guest': {'id', 'name', 'im_status'}}}).values()))],
            'rtcSessions': [('ADD', rtc_sessions_by_channel.get(channel, []))],
        })
        channel_infos.append(info)
    return channel_infos


Channel._channel_info = _channel_info


class ChannelExtend(models.Model):
    _inherit = 'discuss.channel'

    @api.model
    # @api.returns('self', lambda channel: channel._channel_info()[0])
    def channel_get(self, partners_to, pin=True):
        """ Get the canonical private channel between some partners, create it if needed.
            To reuse an old channel (conversation), this one must be private, and contains
            only the given partners.
            :param partners_to : list of res.partner ids to add to the conversation
            :param pin : True if getting the channel should pin it for the current user
            :returns: channel_info of the created or existing channel
            :rtype: dict
        """
        partner_info = False
        if self.env.user.partner_id.id not in partners_to:
            partner_info = self.env['res.partner'].sudo().search([('id', 'in', partners_to)])
            partners_to.append(self.env.user.partner_id.id)
        # determine type according to the number of partner in the channel
        else:
            partner_info = self.env['res.partner'].sudo().search([('id', 'in', partners_to)])
        self.flush_model()
        self.env['discuss.channel.member'].flush_model()
        provider_channel_id = partner_info.channel_provider_line_ids.filtered(lambda s: s.provider_id == self.env.user.provider_id)
        if provider_channel_id:
            if not all(x in provider_channel_id.channel_id.channel_partner_ids.ids for x in partners_to):
                provider_channel_id = False
        if not provider_channel_id:
            provider_channel_id = self.env.user.partner_id.channel_provider_line_ids.filtered(lambda s: s.provider_id == self.env.user.provider_id)
            if not all(x in provider_channel_id.channel_id.channel_partner_ids.ids for x in partners_to):
                provider_channel_id = False

        if provider_channel_id:
            # get the existing channel between the given partners
            channel = self.browse(provider_channel_id.channel_id.filtered(lambda x: x.whatsapp_channel).id)
            # pin up the channel for the current partner
            if pin:
                self.env['discuss.channel.member'].search(
                    [('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write(
                    {'is_pinned': True})
            channel._broadcast(self.env.user.partner_id.ids)
        else:
            self.env.cr.execute("""
                        SELECT M.channel_id
                        FROM discuss_channel C, discuss_channel_member M
                        WHERE M.channel_id = C.id
                            AND M.partner_id IN %s
                            AND C.channel_type LIKE 'chat'
                            AND NOT EXISTS (
                                SELECT 1
                                FROM discuss_channel_member M2
                                WHERE M2.channel_id = C.id
                                    AND M2.partner_id NOT IN %s
                            )
                        GROUP BY M.channel_id
                        HAVING ARRAY_AGG(DISTINCT M.partner_id ORDER BY M.partner_id) = %s
                        LIMIT 1
                    """, (tuple(partners_to), tuple(partners_to), sorted(list(partners_to)),))
            result = self.env.cr.dictfetchall()
            if result:
                # get the existing channel between the given partners
                channel = self.browse(result[0].get('channel_id'))
                # pin up the channel for the current partner
                if pin:
                    self.env['discuss.channel.member'].search(
                        [('partner_id', '=', self.env.user.partner_id.id), ('channel_id', '=', channel.id)]).write({
                        'is_pinned': True,
                        'last_interest_dt': fields.Datetime.now(),
                    })
                channel._broadcast(self.env.user.partner_id.ids)
                return channel._channel_info()[0]

            # create a new one
            channel = self.create({
                'channel_partner_ids': [(4, partner_id) for partner_id in partners_to],
                'channel_member_ids': [
                    Command.create({
                        'partner_id': partner_id,
                        # only pin for the current user, so the chat does not show up for the correspondent until a message has been sent
                        'is_pinned': partner_id == self.env.user.partner_id.id
                    }) for partner_id in partners_to
                ],
                'channel_type': 'chat',
                # 'email_send': False,
                'name': ', '.join(self.env['res.partner'].sudo().browse(partners_to).mapped('name')),
            })
            have_user = self.env['res.users'].search([('partner_id', 'in', partner_info.ids)])
            if not have_user:
                channel.whatsapp_channel = True
            if partner_info:
                # partner_info.channel_id = channel.id
                partner_info.write({'channel_provider_line_ids': [
                    (0, 0, {'channel_id': channel.id, 'provider_id': self.env.user.provider_id.id})]})
            mail_channel_partner = self.env['discuss.channel.member'].sudo().search(
                [('channel_id', '=', channel.id), ('partner_id', '=', self.env.user.partner_id.id)])
            mail_channel_partner.write({'is_pinned': True})
            channel._broadcast(partners_to)
        return channel
        # return channel._channel_info()[0]

    def get_channel_agent(self, channel_id):
        if self.env.user:
            channel = self.env['discuss.channel'].sudo().browse(int(channel_id))
            partner_lst = channel.channel_partner_ids.ids
            channel_users = self.env['res.users'].sudo().search_read([('partner_id.id', 'in', partner_lst)],
                                                                     ['id', 'name'])
            users = self.env['res.users'].sudo().search([('partner_id.id', 'not in', partner_lst)])
            users_lst = []
            for user in users:
                if user.has_group('tus_meta_whatsapp_base.whatsapp_group_user') and user.provider_id and user.provider_id == self.env.user.provider_id:
                    users_lst.append({'name': user.name, 'id': user.id})
            dict = {'channel_users': channel_users, 'users': users_lst}
            return dict

    def add_agent(self, user_id, channel_id):
        user = self.env['res.users'].sudo().browse(int(user_id))
        channel = self.env['discuss.channel'].sudo().browse(int(channel_id))
        if channel.whatsapp_channel:
            channel.write({'channel_partner_ids': [(4, user.partner_id.id)]})
            mail_channel_partner = self.env['discuss.channel.member'].sudo().search(
                [('channel_id', '=', channel_id),
                 ('partner_id', '=', user.partner_id.id)])
            mail_channel_partner.write({'is_pinned': True})
            return True

    def remove_agent(self, user_id, channel_id):
        user = self.env['res.users'].sudo().browse(int(user_id))
        channel = self.env['discuss.channel'].sudo().browse(int(channel_id))
        if channel.whatsapp_channel:
            channel.write({'channel_partner_ids': [(3, user.partner_id.id)]})
            return True

    @api.constrains('channel_member_ids', 'channel_partner_ids')
    def _constraint_partners_chat(self):
        pass

    def add_members(self, partner_ids=None, guest_ids=None, invite_to_rtc_call=False, open_chat_window=False, post_joined_message=True):
        """ Adds the given partner_ids and guest_ids as member of self channels. """
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        partners = self.env['res.partner'].browse(partner_ids or []).exists()
        guests = self.env['mail.guest'].browse(guest_ids or []).exists()
        notifications = []
        all_new_members = self.env["discuss.channel.member"]
        for channel in self:
            members_to_create = []
            existing_members = self.env['discuss.channel.member'].search(expression.AND([
                [('channel_id', '=', channel.id)],
                expression.OR([
                    [('partner_id', 'in', partners.ids)],
                    [('guest_id', 'in', guests.ids)]
                ])
            ]))
            members_to_create += [{
                'partner_id': partner.id,
                'channel_id': channel.id,
            } for partner in partners - existing_members.partner_id]
            members_to_create += [{
                'guest_id': guest.id,
                'channel_id': channel.id,
            } for guest in guests - existing_members.guest_id]
            new_members = self.env['discuss.channel.member'].create(members_to_create)
            all_new_members += new_members
            for member in new_members.filtered(lambda member: member.partner_id):
                # notify invited members through the bus
                user = member.partner_id.user_ids[0] if member.partner_id.user_ids else self.env['res.users']
                if user:
                    notifications.append((member.partner_id, 'discuss.channel/joined', {
                        'channel': member.channel_id.with_user(user).with_context(allowed_company_ids=user.company_ids.ids)._channel_info()[0],
                        'invited_by_user_id': self.env.user.id,
                        'open_chat_window': open_chat_window,
                    }))
                if post_joined_message and not (channel._fields.get('whatsapp_channel') and channel.whatsapp_channel) or (channel._fields.get('instagram_channel') and channel.instagram_channel) or (
                        channel._fields.get('facebook_channel') and channel.facebook_channel):
                    # notify existing members with a new message in the channel
                    if member.partner_id == self.env.user.partner_id:
                        notification = Markup('<div class="o_mail_notification">%s</div>') % _('joined the channel')
                    else:
                        notification = (Markup('<div class="o_mail_notification">%s</div>') % _("invited %s to the channel")) % member.partner_id._get_html_link()
                    member.channel_id.message_post(body=notification, message_type="notification", subtype_xmlid="mail.mt_comment")
            for member in new_members.filtered(lambda member: member.guest_id):
                if post_joined_message:
                    member.channel_id.message_post(body=Markup('<div class="o_mail_notification">%s</div>') % _('joined the channel'),
                                                   message_type="notification", subtype_xmlid="mail.mt_comment")
                guest = member.guest_id
                if guest:
                    notifications.append((guest, 'discuss.channel/joined', {
                        'channel': member.channel_id.with_context(guest=guest)._channel_info()[0],
                    }))
            notifications.append((channel, 'mail.record/insert', {
                'Thread': {
                    'channelMembers': [('ADD', list(new_members._discuss_channel_member_format().values()))],
                    'id': channel.id,
                    'memberCount': channel.member_count,
                    'model': "discuss.channel",
                }
            }))
            if existing_members and (current_partner or current_guest):
                # If the current user invited these members but they are already present, notify the current user about their existence as well.
                # In particular this fixes issues where the current user is not aware of its own member in the following case:
                # create channel from form view, and then join from discuss without refreshing the page.
                notifications.append((current_partner or current_guest, 'mail.record/insert', {
                    'Thread': {
                        'channelMembers': [('ADD', list(existing_members._discuss_channel_member_format().values()))],
                        'id': channel.id,
                        'memberCount': channel.member_count,
                        'model': "discuss.channel",
                    }
                }))
        if invite_to_rtc_call:
            for channel in self:
                current_channel_member = self.env['discuss.channel.member'].search([('channel_id', '=', channel.id), ('is_self', '=', 'True')])
                # sudo: discuss.channel.rtc.session - reading rtc sessions of current user
                if current_channel_member and current_channel_member.sudo().rtc_session_ids:
                    # sudo: discuss.channel.rtc.session - current user can invite new members in call
                    current_channel_member.sudo()._rtc_invite_members(member_ids=new_members.ids)
        self.env['bus.bus']._sendmany(notifications)
        return all_new_members
    # def _set_last_seen_message(self, last_message, allow_older):
    #     """
    #     When Message Seen/Read in odoo, Double Blue Tick (Read Receipts) in WhatsApp
    #     """
    #     res = super()._set_last_seen_message(last_message, allow_older)
    #     last_message.write({'isWaMsgsRead': True})
    #     if last_message.isWaMsgsRead == True:
    #         channel_company_line_id = self.env['channel.provider.line'].search(
    #             [('channel_id', '=', last_message.res_id)])
    #         if channel_company_line_id.provider_id:
    #             provider_id = channel_company_line_id.provider_id
    #             if provider_id:
    #                 message_id = last_message.wa_message_id if last_message.wa_message_id else last_message
    #                 answer = provider_id.graph_api_wamsg_mark_as_read(message_id)
    #                 if answer.status_code == 200:
    #                     dict = json.loads(answer.text)
    #                     if provider_id.provider == 'graph_api':  # if condition for Graph API
    #                         if 'success' in dict and dict.get('success'):
    #                             last_message.write({'isWaMsgsRead': True})
    #     return res
