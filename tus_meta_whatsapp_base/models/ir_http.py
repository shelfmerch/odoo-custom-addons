# -*- coding: utf-8 -*-
# ----------------------------------------------------------
# ir_http modular http routing
# ----------------------------------------------------------

from odoo import api, http, models, tools, SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, MissingError
from odoo.http import request, content_disposition
from odoo.tools import consteq, pycompat


class IrBinaryInherit(models.AbstractModel):
    _inherit = 'ir.binary'

    def _record_to_stream(self, record, field_name):
        """
        Permission to Attachment
        """
        record = record.sudo()
        return super()._record_to_stream(record=record, field_name=field_name)

    # def _find_record(
    #         self, xmlid=None, res_model='ir.attachment', res_id=None,
    #         access_token=None,
    # ):
    #     """
    #     Find and return a record either using an xmlid either a model+id
    #     pair. This method is an helper for the ``/web/content`` and
    #     ``/web/image`` controllers and should not be used in other
    #     contextes.
    #
    #     :param Optional[str] xmlid: xmlid of the record
    #     :param Optional[str] res_model: model of the record,
    #         ir.attachment by default.
    #     :param Optional[id] res_id: id of the record
    #     :param Optional[str] access_token: access token to use instead
    #         of the access rights and access rules.
    #     :returns: single record
    #     :raises MissingError: when no record was found.
    #     """
    #     record = None
    #     if xmlid:
    #         record = self.env.ref(xmlid, False)
    #     elif res_id is not None and res_model in self.env:
    #         record = self.env[res_model].sudo().browse(res_id).exists()
    #     if not record:
    #         raise MissingError(f"No record found for xmlid={xmlid}, res_model={res_model}, id={res_id}")
    #
    #     record = self._find_record_check_access(record, access_token)
    #     return record

class IrHttpInherit(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_record_and_check(self, xmlid=None, model=None, id=None, field='datas', access_token=None):
        # get object and content
        record = None
        if xmlid:
            record = self._xmlid_to_obj(self.env, xmlid)
        elif id and model in self.env:
            record = self.env[model].sudo().browse(int(id))

        # obj exists
        if not record or field not in record:
            return None, 404

        try:
            if model == 'ir.attachment':
                record_sudo = record.sudo()
                if access_token and not consteq(record_sudo.access_token or '', access_token):
                    return None, 403
                elif (access_token and consteq(record_sudo.access_token or '', access_token)):
                    record = record_sudo
                elif record_sudo.public:
                    record = record_sudo
                elif self.env.user.has_group('base.group_portal'):
                    # Check the read access on the record linked to the attachment
                    # eg: Allow to download an attachment on a task from /my/task/task_id
                    record.check('read')
                    record = record_sudo

            # check read access
            try:
                # We have prefetched some fields of record, among which the field
                # 'write_date' used by '__last_update' below. In order to check
                # access on record, we have to invalidate its cache first.
                if not record.env.su:
                    record._cache.clear()
                record['__last_update']
            except AccessError:
                return None, 403

            return record, 200
        except MissingError:
            return None, 404