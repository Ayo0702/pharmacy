{
    'name': 'BigFix Pharmacy Reports',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Multi-branch pharmacy analytics, NAFDAC reports, and HMO split-billing.',
    'description': """
        - Multi-branch setup for pharmacy chains.
        - Analytics for Sales, Product, and Stock.
        - OWL-based Pharmacy Dashboard.
        - NAFDAC Controlled Drug PDF Reports.
        - HMO Split-Billing for POS orders.
    """,
    'author': 'BigFix', 'Ayo'
    'website': 'https://www.bigfix.com',
    'depends': [
        'point_of_sale',
        'stock',
        'account',
        'spreadsheet_dashboard',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/branch_views.xml',
        'views/analytics_views.xml',
        'report/nafdac_register.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bigfix_pharmacy_reports/static/src/css/dashboard.css',
            'bigfix_pharmacy_reports/static/src/js/dashboard.esm.js',
            'bigfix_pharmacy_reports/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OEEL-1',
}
