# -*- coding: utf-8 -*-
{
    'name': 'SAF-T Analyser by D&C Science in Business',
    'version': '16.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Analyse Portuguese SAF-T files and get executive KPIs — revenue, returns, customer concentration — with a premium HTML report, directly in Odoo.',
    'description': """
SAF-T Analyser - D&C Science in Business
==========================================

Conecta o Odoo ao motor de análise SAF-T via API.

Funcionalidades:
- Upload de ficheiros SAF-T (XML) diretamente no Odoo
- KPIs executivos: faturação, ticket médio, devolucões, concentração
- Relatório HTML premium para download
- Histórico de análises por empresa
- Configuração de API e tier (Standard / Premium / Enterprise)

A análise é processada no servidor D&C. O vosso código e dados nunca saem do fluxo seguro.
    """,
    'author': 'D&C Science in Business',
    'website': 'https://sciencebusiness.pt',
    'support': 'consulting@sciencebusiness.pt',
    'license': 'OPL-1',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/saft_report_views.xml',
        'views/saft_upload_wizard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 0.0,
    'currency': 'EUR',
}
