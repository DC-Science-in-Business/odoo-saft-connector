# -*- coding: utf-8 -*-
"""Extensão de res.config.settings para guardar as credenciais da API SAF-T."""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Configurações da API SAF-T ---
    saft_api_url = fields.Char(
        string='URL da API SAF-T',
        config_parameter='saft_connector.api_url',
        default='https://api.saft.sciencebusiness.pt',
        help='Endereço do servidor da API SAF-T (ex: https://api.saft.sciencebusiness.pt)',
    )
    saft_tenant_id = fields.Char(
        string='Tenant ID',
        config_parameter='saft_connector.tenant_id',
        help='Identificador único da vossa licença. Obtido no portal D&C.',
    )
    saft_api_key = fields.Char(
        string='API Key',
        config_parameter='saft_connector.api_key',
        help='Chave secreta da API. Trate como password – não partilhe.',
    )
    saft_default_tier = fields.Selection(
        selection=[('t1', 'Standard'), ('t2', 'Premium'), ('t3', 'Enterprise')],
        string='Tier Padrão',
        config_parameter='saft_connector.default_tier',
        default='t1',
        help='Tier a usar quando o upload não especifica explicitamente.',
    )

    def action_test_saft_connection(self):
        """Testa a ligação à API e apresenta uma notificação com o resultado."""
        import requests

        self.ensure_one()
        api_url = self.env['ir.config_parameter'].sudo().get_param(
            'saft_connector.api_url', ''
        )
        if not api_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'SAF-T API',
                    'message': 'Preencha a URL da API antes de testar.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        try:
            resp = requests.get(f'{api_url.rstrip("/")}/api/v1/health', timeout=10)
            resp.raise_for_status()
            data = resp.json()
            msg = f'Ligação OK — {data.get("service", "API")} v{data.get("version", "?")}'
            notif_type = 'success'
        except Exception as exc:
            msg = f'Falha de ligação: {exc}'
            notif_type = 'danger'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SAF-T API',
                'message': msg,
                'type': notif_type,
                'sticky': notif_type == 'danger',
            },
        }
