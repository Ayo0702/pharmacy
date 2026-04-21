/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, onMounted, useRef } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class BigFixDashboard extends Component {
    static template = "bigfix_pharmacy_reports.BigFixDashboard";
    static components = { Layout };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            branches: [],
            selectedBranch: "all",
            locations: [],
            selectedLocation: "all",
            recent_sales: [],
            top_products: [],
            stock_coverage: [],
            payment_breakdown: [],
            branch_comparison: [],
            loading: true,
        });

        this.salesChartRef = useRef("salesChart");
        this.paymentChartRef = useRef("paymentChart");
        this.inventoryChartRef = useRef("inventoryChart");
        this.comparisonChartRef = useRef("comparisonChart");

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.fetchBranches();
            await this.fetchData();
        });

        onMounted(() => {
            if (!this.state.loading) {
                this.renderCharts();
            }
        });
    }

    async fetchBranches() {
        this.state.branches = await this.orm.searchRead("res.branch", [], ["name"]);
    }

    async onBranchChange(ev) {
        this.state.selectedBranch = ev.target.value;
        this.state.selectedLocation = "all";
        await this.fetchLocations();
        await this.fetchData();
        this.renderCharts();
    }

    async fetchLocations() {
        if (this.state.selectedBranch === "all") {
            this.state.locations = [];
            return;
        }
        const branch = await this.orm.read("res.branch", [parseInt(this.state.selectedBranch)], ["warehouse_id"]);
        if (branch && branch[0] && branch[0].warehouse_id) {
            this.state.locations = await this.orm.searchRead("stock.location", 
                [["warehouse_id", "=", branch[0].warehouse_id[0]], ["usage", "=", "internal"]], 
                ["name", "display_name"]
            );
        } else {
            this.state.locations = [];
        }
    }

    async onLocationChange(ev) {
        this.state.selectedLocation = ev.target.value;
        await this.fetchData();
        this.renderCharts();
    }

    async fetchData() {
        this.state.loading = true;
        let domain = [];
        const stockDomain = [...domain];
        if (this.state.selectedLocation !== "all") {
            stockDomain.push(["location_id", "=", parseInt(this.state.selectedLocation)]);
        }

        const [recent_sales, top_products, stock_coverage, payment_breakdown] = await Promise.all([
            this.orm.searchRead("bigfix.report.sales", domain, ["date_order", "total_orders", "total_sales"], { limit: 7, order: "date_order desc" }),
            this.orm.searchRead("bigfix.report.product.location", domain, ["product_id", "qty_sold", "revenue"], { limit: 5, order: "revenue desc" }),
            this.orm.searchRead("bigfix.report.stock.sale", stockDomain, ["product_id", "current_stock", "avg_daily_sales"], { limit: 10, order: "current_stock asc" }),
            this.orm.searchRead("bigfix.pharmacy.payment.report", domain, ["payment_category", "amount"], { limit: 100 })
        ]);

        this.state.recent_sales = recent_sales.reverse();
        this.state.top_products = top_products;
        this.state.stock_coverage = stock_coverage;
        this.state.payment_breakdown = payment_breakdown;
        
        if (this.state.selectedBranch === 'all') {
            await this.fetchBranchComparison();
        }
        
        this.state.loading = false;
    }

    async fetchBranchComparison() {
        const data = await this.orm.readGroup(
            "bigfix.report.sales", 
            [], 
            ["total_sales:sum"], 
            ["branch_id"]
        );
        this.state.branch_comparison = data.map(d => ({
            name: d.branch_id ? d.branch_id[1] : 'Unknown',
            total: d.total_sales
        }));
    }

    renderCharts() {
        this.renderSalesChart();
        this.renderPaymentChart();
        this.renderInventoryChart();
        if (this.state.selectedBranch === 'all') {
            this.renderComparisonChart();
        }
    }

    renderSalesChart() {
        if (this.salesChart) this.salesChart.destroy();
        const ctx = this.salesChartRef.el.getContext("2d");
        this.salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.state.recent_sales.map(s => s.date_order),
                datasets: [{
                    label: 'Revenue',
                    data: this.state.recent_sales.map(s => s.total_sales),
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    }

    renderPaymentChart() {
        if (this.paymentChart) this.paymentChart.destroy();
        const ctx = this.paymentChartRef.el.getContext("2d");
        const cats = ['cash', 'online', 'hmo'];
        const data = cats.map(cat => 
            this.state.payment_breakdown
                .filter(p => p.payment_category === cat)
                .reduce((acc, p) => acc + p.amount, 0)
        );

        this.paymentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Cash', 'Online', 'HMO'],
                datasets: [{
                    data: data,
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b'],
                    borderWidth: 0
                }]
            },
            options: { cutout: '70%', responsive: true, maintainAspectRatio: false }
        });
    }

    renderInventoryChart() {
        if (this.inventoryChart) this.inventoryChart.destroy();
        const ctx = this.inventoryChartRef.el.getContext("2d");
        const top_stock = this.state.stock_coverage.slice(0, 10);
        this.inventoryChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: top_stock.map(s => s.product_id[1].split(' ')[0]), // Short name
                datasets: [{
                    label: 'Current Stock',
                    data: top_stock.map(s => s.current_stock),
                    backgroundColor: '#6366f1'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
        });
    }

    renderComparisonChart() {
        if (this.comparisonChart) this.comparisonChart.destroy();
        if (!this.comparisonChartRef.el) return;
        const ctx = this.comparisonChartRef.el.getContext("2d");
        this.comparisonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.state.branch_comparison.map(b => b.name),
                datasets: [{
                    label: 'Revenue by Branch',
                    data: this.state.branch_comparison.map(b => b.total),
                    backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#0ea5e9', '#ec4899'],
                    borderRadius: 8
                }]
            },
            options: { 
                indexAxis: 'y',
                responsive: true, 
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }

    openReport(actionXmlId) {
        let domain = [];
        if (this.state.selectedBranch !== "all") {
            domain.push(["branch_id", "=", parseInt(this.state.selectedBranch)]);
        }
        if (this.state.selectedLocation !== "all" && actionXmlId === 'bigfix_pharmacy_reports.action_bigfix_report_stock_sale') {
            domain.push(["location_id", "=", parseInt(this.state.selectedLocation)]);
        }
        this.actionService.doAction(actionXmlId, {
            additionalContext: { 
                search_default_branch_id: parseInt(this.state.selectedBranch),
                search_default_location_id: parseInt(this.state.selectedLocation),
            },
            props: { domain }
        });
    }
}

registry.category("actions").add("bigfix_pharmacy_reports.dashboard", BigFixDashboard);
