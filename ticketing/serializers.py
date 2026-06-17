from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Ticket, TicketMessage

User = get_user_model()


# ==========================================
# ۱. سریالایزر پیام‌های تیکت (اصلاح نام متد)
# ==========================================
class TicketMessageSerializer(serializers.ModelSerializer):
    is_staff_reply = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source="sender.username", read_only=True)
    created_at = serializers.SerializerMethodField()  # تبدیل امن تاریخ جلالی به متن

    class Meta:
        model = TicketMessage
        fields = ["id", "message_text", "created_at", "sender_name", "is_staff_reply"]

    # 🎯 اصلاح اساسی: نام متد باید دقیقاً با نام فیلد همخوانی داشته باشد (get_is_staff_reply)
    def get_is_staff_reply(self, obj):
        if obj.sender:
            return obj.sender.is_staff
        return False

    def get_created_at(self, obj):
        # جلوگیری از خطای فرمت‌دهی تاریخ جلالی در رست‌فریمورک
        if obj.created_at:
            return str(obj.created_at)
        return ""


# ==========================================
# ۲. سریالایزر اصلی تیکت‌ها
# ==========================================
class UserTicketListSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)
    handler_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "fullname",
            "status",
            "status_display",
            "handler_name",
            "messages",
        ]

    def get_handler_name(self, obj):
        for field_name in ["current_handler", "handler", "assigned_to", "supporter"]:
            if hasattr(obj, field_name):
                user_obj = getattr(obj, field_name, None)
                if user_obj:
                    return getattr(user_obj, "username", "بدون راهبر")
        return "بدون راهبر"

    def get_status_display(self, obj):
        if hasattr(obj, "get_status_display"):
            return obj.get_status_display()
        return getattr(obj, "status", "NEW")
