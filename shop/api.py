from django.contrib.auth import get_user_model
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .emails import send_donation_received
from .models import Category, Donation, Order, Product
from .services import CheckoutError, create_order

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "slug", "description", "kind", "price", "stock", "in_stock", "image", "category")


class OrderItemSerializer(serializers.Serializer):
    product = serializers.CharField(source="product.name")
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    lines = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Order
        fields = ("id", "full_name", "email", "phone", "address", "city", "notes", "payment_reference",
                  "status", "created", "items", "total", "lines")
        read_only_fields = ("id", "status", "created")

    def validate_lines(self, value):
        for l in value:
            if "product" not in l or "quantity" not in l:
                raise serializers.ValidationError("Each line needs 'product' and 'quantity'.")
        return value


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = ("id", "donor_name", "email", "amount", "purpose", "payment_reference", "status", "created")
        read_only_fields = ("id", "status", "created")

    def validate_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return v


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, data):
        return User.objects.create_user(**data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category")
        p = self.request.query_params
        if p.get("category"):
            qs = qs.filter(category__slug=p["category"])
        if p.get("kind"):
            qs = qs.filter(kind=p["kind"])
        if p.get("q"):
            qs = qs.filter(name__icontains=p["q"])
        return qs


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        lines = data.pop("lines")
        try:
            order = create_order(request.user, data, [(l["product"], l["quantity"]) for l in lines])
        except (CheckoutError, ValueError, TypeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="downloads")
    def downloads(self, request, pk=None):
        order = self.get_object()
        if not order.downloads_unlocked:
            return Response({"detail": "Payment not yet confirmed."}, status=status.HTTP_403_FORBIDDEN)
        out = []
        for i in order.items.all():
            if i.product.is_digital and i.product.digital_file:
                out.append({"product": i.product.name, "url": i.product.digital_file.url, "expires_in": 300})
        return Response(out)


class DonationViewSet(viewsets.GenericViewSet):
    serializer_class = DonationSerializer
    permission_classes = [AllowAny]
    queryset = Donation.objects.none()

    def create(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.save(user=request.user if request.user.is_authenticated else None)
        send_donation_received(d)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class RegisterViewSet(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    queryset = User.objects.none()

    def create(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"username": ser.data["username"]}, status=status.HTTP_201_CREATED)


router = DefaultRouter()
router.register("products", ProductViewSet, basename="api-product")
router.register("categories", CategoryViewSet, basename="api-category")
router.register("orders", OrderViewSet, basename="api-order")
router.register("donations", DonationViewSet, basename="api-donation")
router.register("register", RegisterViewSet, basename="api-register")
