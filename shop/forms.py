from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    city = forms.CharField(max_length=100, required=False)
    payment_reference = forms.CharField(max_length=100, label="Mobile money transaction reference")
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)


class DonationForm(forms.Form):
    donor_name = forms.CharField(max_length=150, label="Your name")
    email = forms.EmailField()
    amount = forms.DecimalField(min_value=1, max_digits=10, decimal_places=2)
    purpose = forms.CharField(max_length=200, required=False, label="Purpose (optional)")
    payment_reference = forms.CharField(max_length=100, required=False, label="Mobile money reference")
