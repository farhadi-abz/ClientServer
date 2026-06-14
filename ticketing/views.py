from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .models import HardwareInventory, Ticket, TicketMessage
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import OrganizationalUnit
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import Ticket, TicketMessage, OrganizationalUnit
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


# ۱. دریافت توکن برای کلاینت (لاگین)
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username})


# ۲. دریافت تیکت و مشخصات سخت‌افزاری کلاینت
class SubmitTicketAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        user_info = data.get("user_info", {})
        hardware_info = data.get("hardware_info", {})

        if not user_info or not hardware_info:
            return Response(
                {"error": "اطلاعات ارسالی ناقص است"}, status=status.HTTP_400_BAD_REQUEST
            )

        # بروزرسانی یا ایجاد اطلاعات سخت‌افزاری بر اساس MAC Address
        hardware_obj, created = HardwareInventory.objects.update_or_create(
            mac_address=hardware_info.get("mac"),
            defaults={
                "hostname": hardware_info.get("hostname"),
                "ip_address": hardware_info.get("ip"),
                "cpu_model": hardware_info.get("cpu"),
                "motherboard": hardware_info.get("motherboard"),
                "ram_size": hardware_info.get("ram"),
            },
        )

        # ایجاد تیکت جدید (وضعیت پیش‌فرض NEW)
        # ایجاد تیکت جدید با ساختار صحیح
        ticket_obj = Ticket.objects.create(
            creator=user,
            fullname=user_info.get("fullname"),
            location_id=user_info.get(
                "location"
            ),  # <--- با اضافه شدن _id مشکل کاملاً حل می‌شود
            mobile=user_info.get("mobile"),
            phone=user_info.get("phone"),
            hardware=hardware_obj,
            status="NEW",
        )

        # ثبت اولین پیام تیکت که همان شرح مشکل است
        TicketMessage.objects.create(
            ticket=ticket_obj, sender=user, message_text=user_info.get("description")
        )

        return Response(
            {"message": "تیکت با موفقیت ثبت شد", "ticket_id": ticket_obj.id},
            status=status.HTTP_201_CREATED,
        )


class OrgUnitSerializer(ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ["id", "name", "parent"]


# اندپوینت دریافت چارت سازمانی برای کلاینت
class OrganizationalChartAPI(ListAPIView):
    permission_classes = [IsAuthenticated]  # فقط کاربران لاگین شده دسترسی دارند
    queryset = OrganizationalUnit.objects.all()
    serializer_class = OrgUnitSerializer


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    is_staff_reply = serializers.BooleanField(source="sender.is_staff", read_only=True)

    class Meta:
        model = TicketMessage
        fields = ["id", "sender_name", "message_text", "is_staff_reply", "created_at"]


class UserTicketListSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    handler_name = serializers.CharField(
        source="current_handler.get_full_name",
        default="در انتظار ارجاع",
        read_only=True,
    )
    location_name = serializers.CharField(source="location.__str__", read_only=True)

    class Meta:
        model = Ticket = Ticket
        fields = [
            "id",
            "fullname",
            "location_name",
            "status",
            "status_display",
            "handler_name",
            "messages",
            "created_at",
        ]


# ۱. دریافت لیست تمام تیکت‌های خود کاربر همراه با تاریخچه پیام‌ها
class UserTicketsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserTicketListSerializer

    def get_queryset(self):
        # کاربر فقط و فقط تیکت‌های خودش را می‌بیند
        return Ticket.objects.filter(creator=self.request.user).order_by("-created_at")


# ۲. ارسال پیام جدید (پاسخ) توسط کاربر روی تیکت موجود
class SendReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        try:
            ticket = Ticket.objects.get(id=ticket_id, creator=request.user)
        except Ticket.DoesNotExist:
            return Response(
                {"error": "تیکت یافت نشد یا دسترسی ندارید"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # اگر تیکت خاتمه یافته باشد، اجازه ارسال پیام جدید نمی‌دهیم
        if ticket.status == "CLOSED":
            return Response(
                {"error": "این تیکت خاتمه یافته است و امکان ارسال پاسخ وجود ندارد"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message_text = request.data.get("message_text", "").strip()
        if not message_text:
            return Response(
                {"error": "متن پیام نمی‌تواند خالی باشد"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_msg = TicketMessage.objects.create(
            ticket=ticket, sender=request.user, message_text=message_text
        )

        return Response(
            {"message": "پاسخ شما با موفقیت ثبت شد"}, status=status.HTTP_201_CREATED
        )
