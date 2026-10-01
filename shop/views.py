import mimetypes

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .emails import send_donation_received
from .forms import CheckoutForm, DonationForm, RegisterForm
from .models import Category, Donation, Order, OrderItem, Product
from .services import CheckoutError, create_order


def home(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "shop/home.html", {"featured": products[:8], "categories": Category.objects.all()})


def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related("category")
    cat = request.GET.get("category")
    kind = request.GET.get("kind")
    q = request.GET.get("q", "").strip()
    if cat:
        qs = qs.filter(category__slug=cat)
    if kind in (Product.PHYSICAL, Product.DIGITAL):
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    ctx = {"page": page, "categories": Category.objects.all(), "cat": cat, "kind": kind, "q": q}
    # HTMX live search/filter swaps only the grid
    if request.headers.get("HX-Request"):
        return render(request, "shop/_product_grid.html", ctx)
    return render(request, "shop/product_list.html", ctx)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, "shop/product_detail.html", {"product": product})


# ---- Cart (HTMX) --------------------------------------------------------------
def _cart_response(request, cart):
    return render(request, "shop/_cart_body.html", {"items": cart.items(), "total": cart.total})


def cart_detail(request):
    cart = Cart(request)
    return render(request, "shop/cart.html", {"items": cart.items(), "total": cart.total})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = Cart(request)
    if not product.in_stock:
        messages.error(request, "Sorry, that item is out of stock.")
    else:
        cart.add(product, int(request.POST.get("quantity", 1) or 1))
    if request.headers.get("HX-Request"):
        return render(request, "shop/_cart_badge.html", {"cart_count": len(cart), "added": product})
    return redirect("cart")


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)
    try:
        cart.set(product, int(request.POST.get("quantity", 0)))
    except ValueError:
        pass
    return _cart_response(request, cart) if request.headers.get("HX-Request") else redirect("cart")


@require_POST
def cart_remove(request, pk):
    cart = Cart(request)
    cart.remove(get_object_or_404(Product, pk=pk))
    return _cart_response(request, cart) if request.headers.get("HX-Request") else redirect("cart")


# ---- Checkout & orders -----------------------------------------------------------
@login_required
def checkout(request):
    cart = Cart(request)
    if not len(cart):
        messages.info(request, "Your cart is empty.")
        return redirect("product_list")
    initial = {"full_name": request.user.get_full_name(), "email": request.user.email}
    form = CheckoutForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            data = {**form.cleaned_data, "proof_of_payment": form.cleaned_data.get("proof_of_payment") or ""}
            order = create_order(request.user, data, cart.data.items())
        except CheckoutError as e:
            form.add_error(None, str(e))
        else:
            cart.clear()
            return redirect("order_detail", pk=order.pk)
    return render(request, "shop/checkout.html", {
        "form": form, "items": cart.items(), "total": cart.total, "has_physical": cart.has_physical(),
    })


@login_required
def quote_pdf_view(request):
    from .pdf import quote_pdf

    cart = Cart(request)
    if not len(cart):
        return redirect("cart")
    resp = HttpResponse(quote_pdf(request.user, cart.items(), cart.total), content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="BCU-quote.pdf"'
    return resp


@login_required
def order_list(request):
    return render(request, "shop/order_list.html", {"orders": request.user.orders.prefetch_related("items__product")})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items__product"), pk=pk, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})


@login_required
def order_pdf_view(request, pk):
    from .pdf import order_pdf

    order = get_object_or_404(Order.objects.prefetch_related("items__product"), pk=pk, user=request.user)
    resp = HttpResponse(order_pdf(order), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="BCU-order-{order.short_id}.pdf"'
    return resp


@login_required
def download(request, pk, item_id):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    item = get_object_or_404(OrderItem, pk=item_id, order=order)
    product = item.product
    if not (product.is_digital and product.digital_file and order.downloads_unlocked):
        raise Http404
    try:
        # B2 private bucket: short-lived signed URL
        url = product.digital_file.url
        if url.startswith("http"):
            return HttpResponseRedirect(url)
    except Exception:
        pass
    # Local dev fallback
    ctype = mimetypes.guess_type(product.digital_file.name)[0] or "application/octet-stream"
    return FileResponse(product.digital_file.open("rb"), as_attachment=True, content_type=ctype,
                        filename=product.digital_file.name.split("/")[-1])


# ---- Donations -----------------------------------------------------------------
def donate(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {"donor_name": request.user.get_full_name(), "email": request.user.email}
    form = DonationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = Donation.objects.create(user=request.user if request.user.is_authenticated else None, **form.cleaned_data)
        send_donation_received(d)
        return render(request, "shop/donate_thanks.html", {"donation": d})
    return render(request, "shop/donate.html", {"form": form})


# ---- Accounts ---------------------------------------------------------------------
def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(request.GET.get("next") or "home")
    return render(request, "registration/register.html", {"form": form})
