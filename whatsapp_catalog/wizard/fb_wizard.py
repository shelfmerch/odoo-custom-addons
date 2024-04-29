import base64
import io

import xlsxwriter

from odoo import fields, models, tools


class FbReportWizard(models.TransientModel):
    _name = "fb.report.wizard"
    _description = "FB Report Wizard"

    binary_data = fields.Binary("Binary Data")
    product_ids = fields.Many2many(
        comodel_name="product.template", string="Product Ids"
    )
    brand = fields.Char("Brand")

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self._context.get("active_ids", False)
        model = self._context.get("active_model", False)
        if ids and model:
            product = self.env[model].browse(ids)
            res.update({"product_ids": [(6, 0, product.ids)]})
        return res

    def generate_fb_xlsx_report(self):
        filename = "FbReport.xlsx"
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Fb Product Report")
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        worksheet.set_zoom(100)
        worksheet.set_column(0, 0, 5)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, 2, 40)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 15)
        worksheet.set_column(5, 5, 15)
        worksheet.set_column(6, 6, 50)
        worksheet.set_column(7, 7, 50)
        worksheet.set_column(8, 8, 15)

        text_format = workbook.add_format(
            {
                "align": "left",
                "valign": "bottom",
                "font_name": "Calibri",
                "font_size": "9",
            }
        )

        column_titles = workbook.add_format(
            {
                "bold": True,
                "align": "left",
                "valign": "bottom",
                "font_name": "Calibri",
                "font_size": "9",
            }
        )

        row = 0
        column = 0

        worksheet.write(row, column, "id", column_titles)
        worksheet.write(row, column + 1, "title", column_titles)
        worksheet.write(row, column + 2, "description", column_titles)
        worksheet.write(row, column + 3, "availability", column_titles)
        worksheet.write(row, column + 4, "condition", column_titles)
        worksheet.write(row, column + 5, "price", column_titles)
        worksheet.write(row, column + 6, "link", column_titles)
        worksheet.write(row, column + 7, "image_link", column_titles)
        worksheet.write(row, column + 8, "brand", column_titles)
        row = 1

        IrConfigParam = self.env["ir.config_parameter"].sudo()
        base_url = IrConfigParam.get_param("web.base.url", False)

        for val in self.product_ids:
            worksheet.write(row, column, val.id, text_format)
            worksheet.write(row, column + 1, val.name, text_format)
            worksheet.write(
                row,
                column + 2,
                tools.html2plaintext(val.description or ""),
                text_format,
            )

            # TODO Dynamic stock calculation Remaining
            worksheet.write(row, column + 3, 'in stock', text_format)
            worksheet.write(row, column + 4, "New", text_format)
            worksheet.write(row, column + 5, val.list_price, text_format)
            worksheet.write(row, column + 6, base_url + val.website_url, text_format)
            image_link = base_url + "/web/image/%s/%s/image_1920" % (val._name, val.id)
            worksheet.write(row, column + 7, image_link, text_format)
            worksheet.write(row, column + 8, self.brand, text_format)
            row += 1

        workbook.close()
        output.seek(0)
        output = base64.encodebytes(output.read())
        self.write({"binary_data": output})
        return {
            "type": "ir.actions.act_url",
            "url": "web/content/?model=fb.report.wizard&field=binary_data&download=true&id=%s&filename=%s"
                   % (self.id, filename),
            "target": "download",
        }
