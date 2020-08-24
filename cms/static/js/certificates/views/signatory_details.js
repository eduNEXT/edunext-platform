// Backbone Application View:  Signatory Details

define([
    'jquery',
    'underscore',
    'underscore.string',
    'backbone',
    'gettext',
    'js/utils/templates',
    'common/js/components/utils/view_utils',
    'js/views/baseview',
    'js/certificates/views/signatory_editor',
    'text!templates/signatory-details.underscore',
    'text!templates/signatory-actions.underscore',
    'edx-ui-toolkit/js/utils/html-utils'
],
function($, _, str, Backbone, gettext, TemplateUtils, ViewUtils, BaseView, SignatoryEditorView,
          signatoryDetailsTemplate, signatoryActionsTemplate, HtmlUtils) {
    'use strict';
    var SignatoryDetailsView = BaseView.extend({
        tagName: 'div',
        events: {
            'click .edit-signatory': 'editSignatory',
            'click  .signatory-panel-save': 'saveSignatoryData',
            'click  .signatory-panel-close': 'closeSignatoryEditView'

        },

        className: function() {
            // Determine the CSS class names for this model instance
            var index = this.model.collection.indexOf(this.model);
            return [
                'signatory-details',
                'signatory-details-view-' + index
            ].join(' ');
        },

        initialize: function() {
            // Set up the initial state of the attributes set for this model instance
            this.eventAgg = _.extend({}, Backbone.Events);
            this.edit_view = new SignatoryEditorView({
                model: this.model,
                isEditingAllCollections: false,
                eventAgg: this.eventAgg
            });
        },

        loadTemplate: function(name) {
            // Retrieve the corresponding template for this model
            return TemplateUtils.loadTemplate(name);
        },

        editSignatory: function(event) {
            // Retrieve the edit view for this model
            if (event && event.preventDefault) { event.preventDefault(); }
            this.$el.html(HtmlUtils.HTML(this.edit_view.render()).toString());
            this.$el.append(HtmlUtils.template(signatoryActionsTemplate)().toString());
            this.edit_view.delegateEvents();
            this.delegateEvents();
        },

        saveSignatoryData: function(event) {
            // Persist the data for this model
            var certificate = this.model.get('certificate');
            var self = this;
            if (event && event.preventDefault) { event.preventDefault(); }
            if (!certificate.isValid()) {
                return;
            }
            ViewUtils.runOperationShowingMessage(
                gettext('Saving'),
                function() {
                    var dfd = $.Deferred();
                    var actionableModel = certificate;
                    actionableModel.save({}, {
                        success: function() {
                            actionableModel.setOriginalAttributes();
                            dfd.resolve();
                            self.closeSignatoryEditView();
                        }
                    });
                    return dfd;
                });
        },

        closeSignatoryEditView: function(event) {
            // Enable the cancellation workflow for the editing view
            if (event && event.preventDefault) { event.preventDefault(); }
            if (event) { this.model.reset(); }
            this.render();
        },

        render: function() {
            // Assemble the detail view for this model
            var attributes = $.extend({}, this.model.attributes, {
                signatory_number: this.model.collection.indexOf(this.model) + 1
            });
            return HtmlUtils.setHtml(this.$el, HtmlUtils.template(signatoryDetailsTemplate)(attributes));
        }
    });
    return SignatoryDetailsView;
});
