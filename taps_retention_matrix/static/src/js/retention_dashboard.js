odoo.define('taps_retention_matrix.retention_dashboard', function (require) {
"use strict";

/**
 * This file defines the Purchase Dashboard view (alongside its renderer, model
 * and controller). This Dashboard is added to the top of list and kanban Purchase
 * views, it extends both views with essentially the same code except for
 * _onDashboardActionClicked function so we can apply filters without changing our
 * current view.
 */

var core = require('web.core');
var ListController = require('web.ListController');
var ListModel = require('web.ListModel');
var ListRenderer = require('web.ListRenderer');
var ListView = require('web.ListView');
var KanbanController = require('web.KanbanController');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var SampleServer = require('web.SampleServer');
var view_registry = require('web.view_registry');
var session = require('web.session');

var QWeb = core.qweb;

// Add mock of method 'retrieve_dashboard' in SampleServer, so that we can have
// the sample data in empty purchase kanban and list view
let dashboardValues;
SampleServer.mockRegistry.add('retention.matrix/retrieve_dashboard', (companyId, departmentId) => {
    return Object.assign({}, dashboardValues);
});


//--------------------------------------------------------------------------
// List View
//--------------------------------------------------------------------------

var ExpenseListDashboardRenderer = ListRenderer.extend({
    events:_.extend({}, ListRenderer.prototype.events, {
        'click .o_dashboard_action': '_onDashboardActionClicked',
        'click .o_search_panel_field[name="company_id"]': '_onCompanyClick',
        'click .o_search_panel_field[name="department_id"]': '_onDepartmentClick',
    }),
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var retention_dashboard = QWeb.render('taps_retention_matrix.RetentionDashboard', {
                values: values,
            });
            self.$el.prepend(retention_dashboard);
        });
    },

    /**
     * @private
     * @param {MouseEvent}
     */
    _onDashboardActionClicked: function (e) {
        e.preventDefault();
        var $action = $(e.currentTarget);
        this.trigger_up('dashboard_open_action', {
            action_name: $action.attr('name')+"_list",
            action_context: $action.attr('context'),
        });
    },
    _onCompanyClick: function (ev) {
        var companyId = $(ev.currentTarget).data('value');
        console.log("Company Clicked:", companyId);
        this._companyId = companyId;
        this.reload();
    },

    _onDepartmentClick: function (ev) {
        var departmentId = $(ev.currentTarget).data('value');
        console.log("Department Clicked:", departmentId);
        this._departmentId = departmentId;
        this.reload();
    },     
});

var ExpenseListDashboardModel = ListModel.extend({
    /**
     * @override
     */
    init: function () {
        this.dashboardValues = {};
        this._super.apply(this, arguments);
        this._companyId;
        this._departmentId;
    },
    /**
     * @override
     */
    __get: function (localID) {
        var result = this._super.apply(this, arguments);
        if (_.isObject(result)) {
            result.dashboardValues = this.dashboardValues[localID];
        }
        return result;
    },
    /**
     * @override
     * @returns {Promise}
     */
    __load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
    /**
     * @override
     * @returns {Promise}
     */
    __reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },
 
    /**
     * @private
     * @param {Promise} super_def a promise that resolves with a dataPoint id
     * @returns {Promise -> string} resolves to the dataPoint id
     */
    _loadDashboard: function (super_def) {
        var self = this;
        // console.log("Load Dashboard:", companyId, departmentId);
        var dashboard_def = this._rpc({
            model: 'retention.matrix',
            method: 'retrieve_dashboard',
            args: [this._companyId, this._departmentId],
        });
        return Promise.all([super_def, dashboard_def]).then(function(results) {
            var id = results[0];
            dashboardValues = results[1];
            self.dashboardValues[id] = dashboardValues;
            return id;
        });
    },
});

var ExpenseListDashboardController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
    }),

    /**
     * @private
     * @param {OdooEvent} e
     */
    _onDashboardOpenAction: function (e) {
        return this.do_action(e.data.action_name,
            {additional_context: JSON.parse(e.data.action_context)});
    },
});

var ExpenseListDashboardView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Model: ExpenseListDashboardModel,
        Renderer: ExpenseListDashboardRenderer,
        Controller: ExpenseListDashboardController,
    }),
});


view_registry.add('taps_retention_matrix_tree_dashboard_upload', ExpenseListDashboardView);

return {
    ExpenseListDashboardModel: ExpenseListDashboardModel,
    ExpenseListDashboardRenderer: ExpenseListDashboardRenderer,
    ExpenseListDashboardController: ExpenseListDashboardController
};

});
