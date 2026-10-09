# -*- encoding: utf-8 -*-
from dal import autocomplete, forward
from django import forms
from django.conf import settings
from django.contrib.admin.filters import SimpleListFilter
from django.forms.widgets import Media, MEDIA_TYPES, media_property


class AutocompleteFilter(SimpleListFilter):
    template = "dal_admin_filters/autocomplete-filter.html"
    title = ''
    field_name = ''
    field_pk = 'id'
    use_pk_exact = True
    autocomplete_url = ''
    is_placeholder_title = False
    widget_attrs = {}
    forwards = []

    class Media:
        css = {
            'all': (
                'dal_admin_filters/css/autocomplete-fix.css',
            )
        }
        js = (
            'dal_admin_filters/js/forward-fix.js',
            'dal_admin_filters/js/querystring.js',
        )

    def __init__(self, request, params, model, model_admin):
        if self.parameter_name is None:
            self.parameter_name = self.field_name
            if self.use_pk_exact:
                self.parameter_name += '__{}__exact'.format(self.field_pk)
        super(AutocompleteFilter, self).__init__(request, params, model, model_admin)

        widget = self.get_widget(request)

        self._add_media(model_admin, widget)

        field = forms.ModelChoiceField(
            queryset=self.get_queryset_for_field(model, self.field_name),
            widget=widget
        )

        attrs = self.widget_attrs.copy()
        attrs['id'] = 'id-%s-dal-filter' % self.field_name
        if self.is_placeholder_title:
            attrs['data-placeholder'] = self.title
        self.rendered_widget = field.widget.render(
            name=self.parameter_name,
            value=self.used_parameters.get(self.parameter_name, ''),
            attrs=attrs
        )

    def get_queryset_for_field(self, model, name):
        return getattr(model, name).get_queryset()

    @staticmethod
    def get_dependency_media():
        """
        Scripts the widget and forward-fix.js rely on, in the order they need them.

        select2.full.js binds to the global jQuery, which admin's jquery.init.js removes,
        and forward-fix.js reads django.jQuery as soon as it loads. Nothing else pins this
        order, so without it the merged admin media can put select2 after jquery.init.js.
        """
        extra = '' if settings.DEBUG else '.min'
        return Media(js=(
            'admin/js/vendor/jquery/jquery%s.js' % extra,
            'admin/js/vendor/select2/select2.full.js',
            'admin/js/jquery.init.js',
            'dal_admin_filters/js/forward-fix.js',
        ))

    def _add_media(self, model_admin, widget):
        admin_class = model_admin.__class__
        if 'Media' not in vars(admin_class):
            # An inherited Media is shared with every other subclass of that parent,
            # so give this admin its own; its media property still includes the parents' media.
            admin_class.Media = type('Media', (object,), dict())
            if 'media' not in vars(admin_class):
                admin_class.media = media_property(admin_class)

        def _get_media(obj):
            return Media(media=getattr(obj, 'Media', None))

        media = (
            self.get_dependency_media()
            + _get_media(model_admin)
            + widget.media
            + _get_media(AutocompleteFilter)
            + _get_media(self)
        )

        for name in MEDIA_TYPES:
            setattr(model_admin.Media, name, getattr(media, "_" + name))

    def get_forwards(self):
        return tuple(
            forward.Field(field, field) if isinstance(field, str) else field
            for field in self.forwards
        ) or None

    def get_widget(self, request):
        widget = autocomplete.ModelSelect2(
            url=self.get_autocomplete_url(request),
            forward=self.get_forwards(),
        )
        return widget

    def get_autocomplete_url(self, request):
        return self.autocomplete_url

    def has_output(self):
        return True

    def lookups(self, request, model_admin):
        return ()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset
