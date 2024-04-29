import base64
import io

from PIL import Image

from odoo import fields, models
from odoo.tools import image_process


class ProductProductInherit(models.Model):
    _inherit = "product.template"

    image_500 = fields.Image("Meta Image")

    def write(self, vals):
        res = super(ProductProductInherit, self).write(vals)
        for rec in self:
            if vals.get("image_1920", False):
                img = Image.open(io.BytesIO(base64.b64decode(vals.get("image_1920"))))
                width, height = img.size
                if width < 500 and height < 500:
                    process_image = image_process(
                        base64.b64decode(vals.get("image_1920")), size=(500, 500)
                    )
                    vals.update({"image_500": base64.b64encode(process_image)})
                else:
                    vals.update({"image_500": vals.get("image_1920")})
        return res
