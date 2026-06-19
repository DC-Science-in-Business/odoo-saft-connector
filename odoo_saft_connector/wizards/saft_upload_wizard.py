# -*- coding: utf-8 -*-
"""Wizard de upload e análise de ficheiro SAF-T via API D&C."""
import base64
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Timeout (segundos) para o processamento do XML na API
_API_TIMEOUT_UPLOAD = 180
_API_TIMEOUT_GET = 30


class SaftUploadWizard(models.TransientModel):
    _name = 'saft.upload.wizard'
    _description = 'Upload e Análise de SAF-T'

    saft_file = fields.Binary(
        string='Ficheiro SAF-T (XML)',
        required=True,
        help='Exporte o ficheiro SAF-T do vosso software de contabilidade (extensão .xml).',
    )
    file_name = fields.Char(string='Nome do ficheiro')
    requested_tier = fields.Selection(
        selection=[('t1', 'Standard'), ('t2', 'Premium'), ('t3', 'Enterprise')],
        string='Tier Solicitado',
        help='Deixe em branco para usar o tier da subscrição contratada.',
    )

    # --- Helpers privados ---

    def _get_api_credentials(self):
        """Obtém configurações da API. Levanta UserError se incompletas."""
        params = self.env['ir.config_parameter'].sudo()
        api_url = params.get_param('saft_connector.api_url', '').rstrip('/')
        tenant_id = params.get_param('saft_connector.tenant_id', '')
        api_key = params.get_param('saft_connector.api_key', '')
        default_tier = params.get_param('saft_connector.default_tier', 't1')

        if not api_url or not tenant_id or not api_key:
            raise UserError(
                _(
                    'A API SAF-T não está configurada.\n'
                    'Vá a Configurações > SAF-T Analyser e preencha URL, Tenant ID e API Key.'
                )
            )
        return api_url, tenant_id, api_key, default_tier

    @staticmethod
    def _build_headers(tenant_id: str, api_key: str) -> dict:
        return {
            'X-Tenant-Id': tenant_id,
            'X-API-Key': api_key,
        }

    @staticmethod
    def _handle_http_error(exc):
        """Extrai a mensagem de erro estruturada da API, se disponível."""
        try:
            detail = exc.response.json()
            if isinstance(detail, dict) and 'detail' in detail:
                inner = detail['detail']
                if isinstance(inner, dict):
                    return inner.get('message', str(exc))
                return str(inner)
        except Exception:
            pass
        return str(exc)

    # --- Acção principal ---

    def action_analyse(self):
        """Envia o ficheiro SAF-T para a API e cria o registo de análise."""
        try:
            import requests
        except ImportError:
            raise UserError(
                _('O módulo Python "requests" não está instalado no servidor Odoo.')
            )

        self.ensure_one()
        api_url, tenant_id, api_key, default_tier = self._get_api_credentials()
        headers = self._build_headers(tenant_id, api_key)
        file_bytes = base64.b64decode(self.saft_file)
        effective_tier = self.requested_tier or default_tier
        file_name = self.file_name or 'saft.xml'

        # --- 1. Enviar ficheiro e obter job ---
        try:
            params = {'requested_tier': effective_tier}
            resp = requests.post(
                f'{api_url}/api/v1/reports',
                headers=headers,
                files={'file': (file_name, file_bytes, 'application/xml')},
                params=params,
                timeout=_API_TIMEOUT_UPLOAD,
            )
            resp.raise_for_status()
            job_data = resp.json()
        except requests.exceptions.ConnectionError:
            raise UserError(
                _(
                    'Não foi possível conectar à API SAF-T.\n'
                    'Verifique a URL em Configurações e a conectividade de rede.'
                )
            )
        except requests.exceptions.Timeout:
            raise UserError(
                _(
                    'Timeout ao processar o ficheiro SAF-T.\n'
                    'Tente com um ficheiro mais pequeno ou contacte o suporte.'
                )
            )
        except requests.exceptions.HTTPError as exc:
            msg = self._handle_http_error(exc)
            raise UserError(_('Erro da API SAF-T ao submeter: %s') % msg)

        job_id = job_data.get('job_id')
        if not job_id:
            raise UserError(_('A API não devolveu um job_id válido.'))

        # --- 2. Obter KPIs ---
        try:
            kpi_resp = requests.get(
                f'{api_url}/api/v1/reports/{job_id}/kpis',
                headers=headers,
                timeout=_API_TIMEOUT_GET,
            )
            kpi_resp.raise_for_status()
            kpi_data = kpi_resp.json()
        except requests.exceptions.HTTPError as exc:
                raise UserError(_('Erro ao obter KPIs: %s') % self._handle_http_error(exc))
        except Exception as exc:
                raise UserError(_('Erro inesperado ao obter KPIs: %s') % exc)

        # --- 3. Obter relatório HTML ---
        html_content = ''
        try:
            html_resp = requests.get(
                f'{api_url}/api/v1/reports/{job_id}/download',
                headers=headers,
                timeout=_API_TIMEOUT_GET,
            )
            html_resp.raise_for_status()
            html_content = html_resp.text
        except Exception as exc:
            _logger.warning('Não foi possível obter HTML do relatório: %s', exc)

        # --- 4. Criar registo ---
        kpis = kpi_data.get('kpis', {})
        period = job_data.get('period', {})

        vals = {
            'file_name': file_name,
            'tier': job_data.get('tier', effective_tier),
            'job_id': job_id,
            'status': 'done',
            'rows': job_data.get('rows', 0),
            'duration_ms': job_data.get('duration_ms', 0.0),
            'kpi_faturacao_total': kpis.get('faturacao_total', 0.0),
            'kpi_ticket_medio': kpis.get('ticket_medio', 0.0),
            'kpi_taxa_devolucoes': kpis.get('taxa_devolucoes', 0.0),
            'kpi_concentracao_clientes': kpis.get('concentracao_clientes', 0.0),
            'kpi_produto_top1': str(kpis.get('produto_top1', '') or ''),
            'kpi_cliente_top1': str(kpis.get('cliente_top1', '') or ''),
            'kpi_iva_estimado': kpis.get('iva_estimado', 0.0),
            'kpis_raw': json.dumps(kpis, indent=2, ensure_ascii=False),
        }

        # Datas do período
        start_raw = period.get('start', '')
        end_raw = period.get('end', '')
        if start_raw:
            vals['period_start'] = str(start_raw)[:10]
        if end_raw:
            vals['period_end'] = str(end_raw)[:10]

        report = self.env['saft.report'].create(vals)

        # Guardar HTML como anexo se disponível
        if html_content:
            try:
                att_datas = base64.b64encode(html_content.encode('utf-8')).decode('ascii')
                attachment = self.env['ir.attachment'].create({
                    'name': f'relatorio_saft_{job_id}.html',
                    'datas': att_datas,
                    'mimetype': 'text/html',
                    'res_model': 'saft.report',
                    'res_id': report.id,
                    'public': False,
                })
                report.report_html_attachment_id = attachment
            except Exception as exc:
                _logger.warning('Não foi possível guardar HTML como anexo: %s', exc)

        # --- 5. Abrir o registo criado ---
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'saft.report',
            'res_id': report.id,
            'view_mode': 'form',
            'target': 'current',
        }
