from django.views.generic import TemplateView, FormView, View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings

from .controllers import CertController
from .forms import CertificateForm, RedeemForm, RedeemSelectForm


cert_controller = CertController(secret_key=settings.SECRET_KEY)


# =============================================
# МИКСИН ДЛЯ ЗАЩИТЫ
# =============================================
class CertAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/login/'
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'beauty_app/auth/access_denied.html', status=403)
        return redirect(self.login_url)


# =============================================
# ВСЕ ВЬЮХИ
# =============================================
class IndexView(CertAdminRequiredMixin, TemplateView):
    template_name = 'cert_app/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = cert_controller.get_statistics()
        context.update(stats)
        context['recent_certificates'] = cert_controller.get_all_certificates()[:5]
        return context


class CertificateListView(CertAdminRequiredMixin, TemplateView):
    template_name = 'cert_app/index.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = cert_controller.get_statistics()
        context.update(stats)
        context['recent_certificates'] = cert_controller.get_all_certificates()[:5]
        return context


class CertificateDetailView(CertAdminRequiredMixin, DetailView):
    template_name = 'cert_app/certificate_detail.html'
    
    def get_object(self):
        return cert_controller.find_by_id(self.kwargs['pk'])


class CertificateAddView(CertAdminRequiredMixin, FormView):
    template_name = 'cert_app/certificate_form.html'
    form_class = CertificateForm
    
    def get_success_url(self):
        return f'/admin-dashboard/certificates/{self.certificate.pk}/'
    
    def form_valid(self, form):
        phone = form.cleaned_data['phone']
        email = form.cleaned_data['email']
        price = int(form.cleaned_data['price'])
        client_name = form.cleaned_data.get('client_name', '')
        need_qr = form.cleaned_data.get('need_qr', False)
        
        try:
            self.certificate = cert_controller.create_new_cert(
                phone=phone,
                email=email,
                price=price,
                client_name=client_name,
                need_qr=need_qr
            )
            messages.success(self.request, '✅ Сертификат создан! Письмо отправлено.')
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        
        return super().form_valid(form)


class CertificateRedeemView(CertAdminRequiredMixin, FormView):
    """Шаг 1: Ввод телефона"""
    template_name = 'cert_app/redeem_form.html'
    form_class = RedeemForm
    
    def form_valid(self, form):
        phone: str = form.cleaned_data['phone']

        # Проверяем, есть ли активные сертификаты
        certificates = cert_controller.find_by_phone(phone)
        
        if not certificates.exists():
            messages.error(self.request, f'Активных сертификатов для номера {phone} не найдено.')
            return self.form_invalid(form)
        
        # Если один сертификат — сразу гасим
        if certificates.count() == 1:
            cert = certificates.first()
            cert_controller.redeem_by_id(cert.id)
            messages.success(self.request, f'✅ Сертификат {cert.token[:8]} для {phone} погашен!')
            return redirect('cert_app:list')
        
        # Если несколько — переходим к выбору
        self.request.session['redeem_phone'] = phone
        return redirect('cert_app:redeem_select')


class CertificateRedeemSelectView(CertAdminRequiredMixin, FormView):
    """Шаг 2: Выбор сертификата из списка"""
    template_name = 'cert_app/redeem_select_form.html'
    form_class = RedeemSelectForm
    success_url = '/admin-dashboard/certificates/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        phone = self.request.session.get('redeem_phone')
        if phone:
            certificates = cert_controller.find_by_phone(phone)
            kwargs['certificates'] = certificates
        else:
            kwargs['certificates'] = []
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        phone = self.request.session.get('redeem_phone')
        context['phone'] = phone
        if phone:
            context['certificates'] = cert_controller.find_by_phone(phone)
        return context
    
    def form_valid(self, form):
        certificate_id = form.cleaned_data['certificate_id']
        try:
            cert = cert_controller.redeem_by_id(int(certificate_id))
            messages.success(self.request, f'✅ Сертификат {cert.token[:8]} для {cert.phone} погашен!')
        except ValueError as e:
            messages.error(self.request, str(e))
        
        # Очищаем сессию
        if 'redeem_phone' in self.request.session:
            del self.request.session['redeem_phone']
        
        return super().form_valid(form)


class CertificateDeleteView(CertAdminRequiredMixin, View):
    def post(self, request, pk):
        success = cert_controller.delete_certificate(pk)
        if success:
            messages.success(request, '✅ Сертификат удалён!')
        else:
            messages.error(request, '❌ Сертификат не найден')
        return redirect('cert_app:list')


class CertificateResendEmailView(CertAdminRequiredMixin, View):
    def post(self, request, pk):
        certificate = cert_controller.find_by_id(pk)
        if not certificate:
            messages.error(request, '❌ Сертификат не найден')
            return redirect('cert_app:list')
        
        success = cert_controller.send_certificate_email(certificate)
        if success:
            messages.success(request, f'✅ Письмо отправлено на {certificate.email}')
        else:
            messages.error(request, '❌ Ошибка отправки')
        return redirect('cert_app:detail', pk=pk)