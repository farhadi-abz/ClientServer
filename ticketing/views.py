from django.contrib.auth import get_user_model
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.serializers import ModelSerializer

# امپورت مدل‌ها و سریالایزر تفکیک‌شده
from .models import HardwareInventory, Ticket, TicketMessage, OrganizationalUnit
from .serializers import UserTicketListSerializer

User = get_user_model()


# ==========================================
# ۱. سیستم احراز هویت اختصاصی با نقش کاربر
# ==========================================
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)

        # ارسال توکن به همراه وضعیت راهبر بودن کاربر برای کلاینت
        return Response(
            {
                "token": token.key,
                "user_id": user.pk,
                "email": user.email,
                "is_staff": user.is_staff,
            }
        )


# ==========================================
# ۲. ثبت تیکت جدید به همراه اطلاعات سخت‌افزاری
# ==========================================
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

        # ایجاد تیکت جدید با ساختار صحیح
        ticket_obj = Ticket.objects.create(
            creator=user,
            fullname=user_info.get("fullname"),
            location_id=user_info.get("location"),
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


# ==========================================
# ۳. نمودار و چارت سازمانی
# ==========================================
class OrgUnitSerializer(ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ["id", "name", "parent"]


class OrganizationalChartAPI(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = OrganizationalUnit.objects.all()
    serializer_class = OrgUnitSerializer


# ==========================================
# ۴. کارتابل هوشمند نمایش تیکت‌ها (اصلاح تکرار و خطای ۵۰۰)
# ==========================================
class UserTicketsListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserTicketListSerializer

    def get_queryset(self):
        user = self.request.user
        try:
            # ۱. اگر کاربر «مدیر کل» یا سوپریوزر باشد -> کل تیکت‌های سیستم را برای ارجاع مدیریت کند
            if user.is_superuser:
                return Ticket.objects.all().order_by("-id")

            # ۲. اگر کاربر «راهبر/کارشناس عادی» باشد -> فقط تیکت‌هایی که به خودش ارجاع شده را ببیند
            elif user.is_staff:
                # فرض می‌کنیم نام فیلد کارشناس در مدل شما current_handler یا handler است
                if hasattr(Ticket, "current_handler"):
                    return Ticket.objects.filter(current_handler=user).order_by("-id")
                elif hasattr(Ticket, "handler"):
                    return Ticket.objects.filter(handler=user).order_by("-id")
                return Ticket.objects.none()

            # ۳. اگر کاربر معمولی باشد -> فقط تیکت‌های خودش را ببیند
            else:
                return Ticket.objects.filter(creator=user).order_by("-id")

        except Exception as e:
            print(f"❌ Error in get_queryset: {e}")
            return Ticket.objects.none()


# ==========================================
# ۵. ارسال پاسخ هوشمند (اصلاح دسترسی راهبر برای چت)
# ==========================================
class SendReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        user = request.user
        try:
            # هوشمندسازی: اگر کاربر راهبر است فقط تیکت وجود داشته باشد، اگر کاربر عادی است حتماً مالک آن باشد
            if user.is_staff:
                ticket = Ticket.objects.get(id=ticket_id)
            else:
                ticket = Ticket.objects.get(id=ticket_id, creator=user)
        except Ticket.DoesNotExist:
            return Response(
                {"error": "تیکت یافت نشد یا دسترسی ندارید"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # بررسی خاتمه یافتن تیکت
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

        # ایجاد پیام جدید در چت روم تیکت
        new_msg = TicketMessage.objects.create(
            ticket=ticket, sender=user, message_text=message_text
        )

        return Response(
            {"message": "پاسخ شما با موفقیت ثبت شد"}, status=status.HTTP_201_CREATED
        )


class AssignTicketAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        # فقط مدیران (Superuser) اجازه ارجاع تیکت دارند
        if not request.user.is_superuser:
            return Response(
                {"error": "تنها مدیر سیستم اجازه ارجاع تیکت‌ها را دارد."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return Response(
                {"error": "تیکت یافت نشد."}, status=status.HTTP_404_NOT_FOUND
            )

        handler_id = request.data.get("handler_id")
        if not handler_id:
            return Response(
                {"error": "شناسه راهبر ارسال نشده است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            handler_user = User.objects.get(id=handler_id, is_staff=True)
        except User.DoesNotExist:
            return Response(
                {"error": "کارشناس معتبری با این شناسه یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ارجاع تیکت به کارشناس و تغییر وضعیت به در جریان (ASSIGNED یا IN_PROGRESS)
        if hasattr(ticket, "current_handler"):
            ticket.current_handler = handler_user
        elif hasattr(ticket, "handler"):
            ticket.handler = handler_user

        ticket.status = "IN_PROGRESS"  # یا هر وضعیتی که برای ارجاع در نظر دارید
        ticket.save()

        # ثبت یک پیام سیستمی درون چت‌روم تیکت جهت اطلاع
        TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            message_text=f"🔄 این تیکت توسط مدیر به کارشناس [{handler_user.username}] ارجاع داده شد.",
        )

        return Response(
            {"message": f"تیکت با موفقیت به {handler_user.username} ارجاع شد."},
            status=status.HTTP_200_OK,
        )
