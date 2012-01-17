# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.forms.fields import ChoiceField
from django.utils.html import strip_tags
from support.models import SubjectCategory, Ticket
from website.models.faq import Question
from website.views import addPlaceForm, send_message

__author__ = 'Evren Esat Ozkan'

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db.models.query_utils import Q
from django.forms.models import ModelForm, ModelChoiceField
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_exempt
from places.models import *
from places.options import   NO_OF_BEDS
from django.http import  HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from datetime import datetime
import logging
log = logging.getLogger('genel')


#yapildi: sozlesme popup
#yapildi: rezervasyon
#yapil: paypal capture
#yap: iletisim
#yap: ask a question, login/anonim
#yap: komisyon
#yap: donemsel fiyat
#yap: COKDiLLi:: profile description || Place description || messages || reviews
#yap: yorum yaz, duzenle
#yap: yorum goster!!!!!!!!!
#yap: IE kontrolu
#yap: arkadasini davet et
#yap: facebook twitter ikonlari
#fixme: ganishow
#yap ganishow dynamic
#yapild: register thanks >> dashboard
#yapıldı: arkadas ekle, cikar



def list_places(request):
    pls = request.user.place_set.filter(active=True).order_by('-id')
    return render_to_response('dashboard/place_list.html', {"places":pls}, context_instance=RequestContext(request))


@csrf_exempt
def save_photo_order(request, id):
    place = get_object_or_404(Place, owner=request.user, pk=id)
    if request.method == 'POST':
        iids = request.POST.get('iids',[])
        place.reorderPhotos(iids)
        return HttpResponse([1], mimetype='application/json')

@csrf_exempt
def add_friend(request, id):
    user = request.user
    friend = User.objects.get(pk=id)
    if request.method == 'POST':
        f = Friendship(profile=user.get_profile(), user_id=id)
        f.save()
        result = {'message':force_unicode(_('Friendship request successfully sent.'))}
        send_message(request, force_unicode(_('%s wants to be friends with you.')) % user.profile.private_name, receiver=friend, typ=20)
    return HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')

@csrf_exempt
def publish_place(request):
    user = request.user
    if request.method == 'POST':
        id = int(request.POST['id'])
        published = id > 0
        Place.objects.filter(pk=abs(id), owner = user).update(published=published)
        if not published:
            result = {'message':force_unicode(_('Place successfully unlisted from site.'))}
        else:
            result = {'url':reverse('show_place', args=[id]) }
            messages.success(request, _('This place is now published!'))
    return HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')

@csrf_exempt
def delete_place(request):
    user = request.user
    if request.method == 'POST':
        id = int(request.POST['id'])
        Place.objects.filter(pk=id, owner = user).update(active=False, published=False)
        result = {'message':force_unicode(_('Place is deleted.'))}
    return HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')

@csrf_exempt
def confirm_friendship(request):
    user = request.user
    id = int(request.POST.get('id'))
    mid = request.POST.get('mid')
    confirmed =  id>0
    id = abs(id)
    friend = User.objects.get(pk=abs(id))
    if request.method == 'POST':
        f = user.friendship_set.filter(profile=friend.get_profile())
        if f:
            f = f[0]
            if confirmed:
                f.confirmed =  True
                f.save()
                result = _('Friendship request accepted.')
            else:
                f.delete()
                result = _('Friendship request declined.')
            send_message(request, force_unicode(result), receiver=friend, replyto=Message.objects.get(pk=mid))
        else:
            result = _('Can\'t find the request. Could be canceled by the other side.')
        result = {'message':force_unicode(result)}
    return HttpResponse(json.dumps(result, ensure_ascii=False), mimetype='application/json')

@csrf_exempt
def save_calendar(request, id):
    place = get_object_or_404(Place, owner=request.user, pk=id)
    if request.method == 'POST':
        unavails = request.POST.get('unavails',[])
#        log.info('unv: %s'%request.POST.get('unavails'))
        place.setUnavailDates(unavails)
        return HttpResponse([1], mimetype='application/json')

def calendar(request, id):
    place = get_object_or_404(Place, owner=request.user, pk=id)
    return render_to_response('dashboard/calendar.html',
            {'reserved_dates':place.getReservedDates(), 'place':place},
        context_instance=RequestContext(request))



def show_faq(request, type=None):
    return render_to_response('dashboard/dash_faq.html',
            {'faq':Question.getFaqs(request.LANGUAGE_CODE)},
        context_instance=RequestContext(request))


@login_required
def trips(request):
    user = request.user
    profile = user.get_profile()
    context = {
                'current':user.guestings.filter(start__lte=datetime.today(), end__gte=datetime.today()),
                'upcoming':user.guestings.filter(status__in=[10,20]),
                'previous':user.guestings.filter(end__lte=datetime.today()),
               'bookmarks':profile.favorites.all()
    }
    return render_to_response('dashboard/trips.html', context, context_instance=RequestContext(request))

@login_required
def show_requests(request):
    user = request.user
    profile = user.get_profile()
    context = {
                'requests':user.hostings.filter(status__in=[10,20]),
    }
    return render_to_response('dashboard/requests.html', context, context_instance=RequestContext(request))

@login_required
def show_reviews(request):
    user = request.user
    profile = user.get_profile()
    byyou = list(user.place_reviews_by_you.all()) + list(user.personal_reviews_by_you.all())
    aboutyou = list(user.place_reviews_about_you.all()) + list(user.personal_reviews_about_you.all())
    context = {
                'byyou':byyou,
                'aboutyou':aboutyou,
    }
    return render_to_response('dashboard/reviews.html', context, context_instance=RequestContext(request))

@login_required
def friends(request):
    user = request.user
    profile = user.get_profile()
    context = {
               'friends':profile.friendship_set.filter(confirmed=True)
    }
    return render_to_response('dashboard/friends.html', context, context_instance=RequestContext(request))

def list_messages(rq, count=None):
    user = rq.user
    msgs = []
    mesajlar = Message.objects.select_related().filter( Q(sender=user)|Q(receiver=user),
                           replyto__isnull=True).order_by('-last_message_time')
    if count:
        mesajlar = mesajlar[:count]
    for m in mesajlar:
        m.icon = 'read'
        m.line = m.get_type_display()
        if m.sender != user:
            m.participant = m.get_sender_name()
            if not m.read: m.icon = 'new'
        else:
            m.participant = m.get_receiver_name()

        if m.type in [10,20]:
            obj = m.participant
        elif m.type == 30:
            obj = m.place.title
        else:
            obj = None

        if obj:
            m.line = m.line % obj

        if m.replied:
            latest  = m.message_set.latest()
            if not latest.read and latest.sender!=user:
                m.icon = 'replied'
        msgs.append(m)
    return msgs

@login_required
def dashboard(request):
    user = request.user
    profile = user.get_profile()
    bookings = []
    bookings.extend(Booking.objects.filter(status__in=[10,20,30], valid=True, host=user)[:2])
    bookings.extend(Booking.objects.filter(status__in=[10,20,30], valid=True, guest=user)[:2])
    context = {'places':user.place_set.all(),
               'form' : addPlaceForm(),
               'msgs':list_messages(request, 4),
               'bookmarks':profile.favorites.all(),
               'bookings':bookings,

    }
    return render_to_response('dashboard.html', context, context_instance=RequestContext(request))

def show_messages(request):
    context = {'msgs':list_messages(request),}
    return render_to_response('dashboard/user_messages.html', context, context_instance=RequestContext(request))


def show_booking(request, id):
    user = request.user
    booking = Booking.objects.get(Q(guest=user)|Q(host=user), pk=id)
    context={
        'user_is_guest':booking.guest == user,
        'user_is_host':booking.host == user,
        'total_price': booking.guest_payment,
        'booking':booking,
        'place':booking.place,
    }
    if request.method =='POST':
        if request.POST.get('confirmation')=='confirm':
            booking.status = 20
            booking.confirmation_date = datetime.today()
            booking.capturePayment(request)
            messages.success(request, _('Booking request confirmed.'))
        elif request.POST.get('confirmation')=='reject':
            booking.status = 40
            booking.rejection_date = datetime.today()
            booking.voidPayment(request)
            messages.success(request, _('Booking request rejected.'))
        booking.save()
        #yap: send_message to guest
    return render_to_response('dashboard/show_booking.html', context, context_instance=RequestContext(request))



def show_message(request, id):
    user = request.user
    msg = Message.objects.get(Q(sender=user)|Q(receiver=user), pk=id)
    msg.message_set.filter(read=False, receiver=user).update(read=True)
    if msg.receiver == user:
        participant = msg.sender
        receiver = msg.sender
        if not msg.read:
            msg.read = True
            msg.save()
    else:
        participant = msg.receiver
        receiver = msg.receiver
    if request.method == 'POST':
        send_message(request, strip_tags(request.POST['message']), receiver=receiver, replyto=msg)
        msg.last_message_time = datetime.now()
        msg.replied = True
        msg.save()
        messages.success(request, _('Your message successfully sent.'))
    msgs = list(Message.objects.select_related().filter(replyto=msg))
    msgs.append(msg)
    msgslist = []
    for m in msgs:
        m.sender_name =  m.sender.get_full_name() if m.sender == user else m.get_sender_name()
        msgslist.append(m)
    context = {'msg':msg,'msgs':msgslist, 'participant':participant, 'toname':participant.get_profile().private_name}
    return render_to_response('dashboard/show_message.html', context, context_instance=RequestContext(request))

#@csrf_exempt
def new_message(request, id):
    user = request.user
    receiver = User.objects.get(pk=id)
    if request.method == 'POST':
        msg = send_message(request, strip_tags(request.POST['message']), receiver=receiver)
        messages.success(request, _('Your message successfully sent.'))
        return HttpResponseRedirect(reverse('show_message', args=[msg.id]))
    context = {'participant':receiver, 'toname':receiver.get_profile().private_name}
    return render_to_response('dashboard/show_message.html', context, context_instance=RequestContext(request))

class PasswordForm(forms.Form):
    old = forms.CharField(widget=forms.PasswordInput(),label=_('Old password'))
    new1 = forms.CharField(widget=forms.PasswordInput(),label=_('New password'))
    new2 = forms.CharField(widget=forms.PasswordInput(),label=_('New password (again)'))

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['old']):
                if form.cleaned_data['new1']==form.cleaned_data['new2']:
                    user.set_password(form.cleaned_data['new1'])
                    messages.success(request, _('Your password successfully changed.'))
                else:
                    messages.error(request, _('The two password fields didn\'t match.'))
            else:
                messages.error(request, _('Your old password was entered incorrectly. Please enter it again.'))
    else:
        form = PasswordForm()
    context = {'form':form,}
    return render_to_response('dashboard/change_password.html', context, context_instance=RequestContext(request))


@login_required
def edit_profile(request):
    lang = request.LANGUAGE_CODE
    user = request.user
    profile = user.get_profile()
    if request.method == 'POST':
        form = ProfileForm(request.POST,instance=profile)
        uform = UserForm(request.POST,instance=user)
        if form.is_valid() and uform.is_valid():
            profile = form.save()
            user = uform.save()
            messages.success(request, _('Your profile successfully updated.'))
    else:
        form = ProfileForm(instance=profile)
        uform = UserForm(instance=user)
    context = {'form':form,'profile':profile,'user':user,'uform':uform}
    return render_to_response('dashboard/edit_profile.html', context, context_instance=RequestContext(request))


class ProfileForm(ModelForm):
#    lat= forms.FloatField(widget=forms.HiddenInput())
#    lon= forms.FloatField(widget=forms.HiddenInput())
#    currency = ModelChoiceField(Currency.objects.filter(active=True), empty_label=None)

#    neighborhood= forms.FloatField(widget=forms.HiddenInput())

#    postcode= forms.CharField(widget=forms.HiddenInput())
#    def __init__(self, *args, **kwargs):
#        super(ProfileForm, self).__init__(*args, **kwargs)
#        self.fields.insert (0, 'first_name' , forms.CharField())
#        self.fields.insert (1, 'last_name' , forms.CharField())
#        self.fields.insert (2, 'email' , forms.EmailField())

    class Meta:
        model=Profile
        fields = ('city','phone','occupation','brithdate')

class UserForm(ModelForm):
    class Meta:
        model=User
        fields = ('first_name','last_name','email')

@login_required
def edit_profile(request):
    lang = request.LANGUAGE_CODE
    user = request.user
    profile = user.get_profile()
    if request.method == 'POST':
        form = ProfileForm(request.POST,instance=profile)
        uform = UserForm(request.POST,instance=user)
        if form.is_valid() and uform.is_valid():
            profile = form.save()
            user = uform.save()
            messages.success(request, _('Your profile successfully updated.'))
    else:
        form = ProfileForm(instance=profile)
        uform = UserForm(instance=user)
    context = {'form':form,'profile':profile,'user':user,'uform':uform}
    return render_to_response('dashboard/edit_profile.html', context, context_instance=RequestContext(request))





@csrf_exempt
def pfoto(request):
    profile = request.user.get_profile()
    if request.method == 'POST':
        log.info('received POST to main multiuploader view')
        if request.FILES == None:
            return HttpResponseBadRequest('Must have files attached!')

        #getting file data for farther manipulations
        file = request.FILES[u'pfoto']
        wrapped_file = UploadedFile(file)
        filename = wrapped_file.name
#        file_size = wrapped_file.file.size
        log.info (u'Got file: %s'%filename)

        profile.photo=file
        profile.save()
        return HttpResponse('[1]', mimetype='application/json')




class PaymentSelectionBankForm(ModelForm):
    class Meta:
        model=PaymentSelection
        exclude= ('email','user','payment_type','active')
class PaymentSelectionPaypalForm(ModelForm):
    class Meta:
        model=PaymentSelection
        fields= ('email',)

@login_required
def edit_payment(request):
    user = request.user
    ps,yeni=PaymentSelection.objects.get_or_create(user=user)
    saved_ps = None
    if request.method == 'POST':
        bform = PaymentSelectionBankForm(request.POST,instance=ps)
        pform = PaymentSelectionPaypalForm(request.POST,instance=ps)
        if bform.is_valid():
            saved_ps = bform.save(commit=False)
            saved_ps.payment_type =3 #bank transfer
        if pform.is_valid():
            saved_ps = pform.save(commit=False)
            saved_ps.payment_type = 2 #paypal
        if saved_ps:
            saved_ps.save()
            messages.success(request, _('Your payment selection successfully updated.'))
    else:
        bform = PaymentSelectionBankForm(instance=ps)
        pform = PaymentSelectionPaypalForm(instance=ps)
    context = {'bform':bform,'pform':pform, 'ps':ps}
    return render_to_response('dashboard/edit_payment.html', context, context_instance=RequestContext(request))













class PlacePriceForm(ModelForm):
    currency = ModelChoiceField(Currency.objects.filter(active=True), empty_label=None)
    extra_limit = ChoiceField(choices=NO_OF_BEDS)
    class Meta:
        model=Place
        fields = ('price','currency','weekend_price','weekly_discount','monthly_discount','extra_limit','extra_price','cleaning_fee')

from django.forms.models import modelformset_factory
SPFormSet = modelformset_factory(SessionalPrice, extra=2,  exclude=('place','active'),can_delete =True)

@login_required
def edit_prices(request, id):
    lang = request.LANGUAGE_CODE
    user = request.user
    place = Place.objects.get(pk=id, owner=user)
    if request.method == 'POST':
        form = PlacePriceForm(request.POST,instance=place)
        spset = SPFormSet(request.POST, queryset=SessionalPrice.objects.filter(place=place))

        if spset.is_valid():
            spset = spset.save(commit=False)
            for f in spset:
                f.place = place
                f.save()
        if form.is_valid():
            saved_place = form.save()

            messages.success(request, _('Your pricing successfully updated.'))

    form = PlacePriceForm(instance=place)
    spset = SPFormSet(queryset=SessionalPrice.objects.filter(place=place))
    context = {'bform':form,'sform':spset,}
    return render_to_response('dashboard/edit_prices.html', context, context_instance=RequestContext(request))



class TicketForm(forms.ModelForm):
    body = forms.CharField(widget=forms.Textarea(attrs={'cols': '30', 'rows': '4'}), label=_(u'Your message'))
    subject = forms.CharField(widget=forms.TextInput(attrs={'size': '30'}), label=_(u'Subject'))
    #    tip = forms.ChoiceField(label='Değerlendirme',  choices=Mesaj.TIP)
    category = forms.ModelChoiceField(queryset=SubjectCategory.objects.exclude(hidden=True), label=_(u'Category'))

    class Meta:
        model = Ticket
        exclude = ('user', 'status')


@login_required
def support_create(request):
    if request.POST:
        form = TicketForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.status = 10
            obj.user = request.user
            obj.save()
#            mail2perm(obj, url=reverse('support_admin_show_ticket', args=(obj.id, )))
            messages.success(request, _('Your message successfully saved.'))
#            return HttpResponseRedirect(reverse('support_thanks'))
    else:
        form = TicketForm()
        form.fields['subject'].initial = request.GET.get('subject', '')
        form.fields['category'].initial = int(request.GET.get('category', 0))
    return render_to_response('dashboard/support_create.html', {'form': form, },
                              context_instance=RequestContext(request, {}))
