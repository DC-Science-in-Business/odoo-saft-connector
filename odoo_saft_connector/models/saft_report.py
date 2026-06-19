# -*- coding: utf-8 -*-
"""Modelo que representa uma análise SAF-T feita via API."""
import base64
import json

from odoo import api, fields, models


class SaftReport(models.Model):
    _name = 'saft.report'
    _description = 'Análise SAF-T'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # --- Identificação ---
    name = fields.Char(
        string='Referência',
        compute='_compute_name',
        store=True,
    )
    file_name = fields.Char(string='Ficheiro', readonly=True)
    job_id = fields.Char(string='Job ID (API)', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        readonly=True,
    )

    # --- Estado ---
    status = fields.Selection(
        selection=[('done', 'Concluído'), ('failed', 'Falhou')],
        string='Estado',
        default='done',
        readonly=True,
    )
    tier = fields.Selection(
        selection=[('t1', 'Standard'), ('t2', 'Premium'), ('t3', 'Enterprise')],
        string='Tier',
        readonly=True,
    )

    # --- Período e volume ---
    period_start = fields.Date(string='Início do Período', readonly=True)
    period_end = fields.Date(string='Fim do Período', readonly=True)
    rows = fields.Integer(string='Documentos Processados', readonly=True)
    duration_ms = fields.Float(string='Duração (ms)', readonly=True)

    # --- KPIs principais ---
    kpi_faturacao_total = fields.Float(
        string='Faturação Total (€)',
        digits=(16, 2),
        readonly=True,
        tracking=True,
    )
    kpi_ticket_medio = fields.Float(
        string='Ticket Médio (€)',
        digits=(16, 2),
        readonly=True,
    )
    kpi_taxa_devolucoes = fields.Float(
        string='Taxa Devoluções (%)',
        digits=(10, 2),
        readonly=True,
    )
    kpi_concentracao_clientes = fields.Float(
        string='Concentração Clientes (%)',
        digits=(10, 2),
        readonly=True,
    )
    kpi_produto_top1 = fields.Char(string='Produto #1', readonly=True)
    kpi_cliente_top1 = fields.Char(string='Cliente #1', readonly=True)
    kpi_iva_estimado = fields.Float(
        string='IVA Estimado (€)',
        digits=(16, 2),
        readonly=True,
    )

    # --- Relatório ---
    report_html_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Relatório HTML',
        readonly=True,
        copy=False,
        ondelete='set null',
    )
    report_download_url = fields.Char(
        string='URL de Download',
        compute='_compute_report_download_url',
    )
    kpis_raw = fields.Text(string='KPIs JSON', readonly=True)

    # --- Computed ---
    @api.depends('file_name', 'create_date')
    def _compute_name(self):
        for rec in self:
            date_str = rec.create_date.strftime('%Y-%m-%d') if rec.create_date else ''
            fname = (rec.file_name or 'SAF-T').replace('.xml', '').replace('.XML', '')
            rec.name = f'{fname} [{date_str}]'

    @api.depends('report_html_attachment_id')
    def _compute_report_download_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.report_html_attachment_id:
                rec.report_download_url = (
                    f'{base}/web/content/{rec.report_html_attachment_id.id}'
                    f'?download=true'
                )
            else:
                rec.report_download_url = False

    # --- Helpers ---
    def action_open_report(self):
        """Abre o relatório HTML num separador do browser."""
        self.ensure_one()
        if not self.report_download_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Relatório',
                    'message': 'Relatório HTML ainda não disponível.',
                    'type': 'warning',
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': self.report_download_url,
            'target': 'new',
        }

    def action_new_analysis(self):
        """Atalho para abrir o wizard de upload com contexto desta empresa."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'saft.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
