from django.db import models
from django.contrib.auth.models import User


class HardwareInventory(models.Model):
    hostname = models.CharField(max_length=100, verbose_name="نام دستگاه")
    mac_address = models.CharField(max_length=50, unique=True, verbose_name="آدرس MAC")
    ip_address = models.GenericIPAddressField(verbose_name="آدرس IP")
    cpu_model = models.CharField(max_length=200, verbose_name="مدل CPU")
    motherboard = models.CharField(max_length=200, verbose_name="مدل مادربرد")
    ram_size = models.CharField(max_length=50, verbose_name="میزان RAM")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        verbose_name = "سخت‌افزار"
        verbose_name_plural = "تجهیزات سخت‌افزاری"

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class OrganizationalUnit(models.Model):
    name = models.CharField(max_length=150, verbose_name="نام واحد سازمانی")
    # اگر parent خالی باشد یعنی سطح اول (معاونت/مدیریت مستقل) است.
    # اگر پر باشد، یعنی فرزند یک واحد دیگر و سطح دوم (مدیریت زیرمجموعه) است.
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sub_units",
        verbose_name="واحد بالادستی (سطح اول)",
    )

    class Meta:
        verbose_name = "واحد سازمانی"
        verbose_name_plural = "چارت سازمانی"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("NEW", "جدید (در انتظار ارجاع)"),
        ("ASSIGNED", "ارجاع شده به راهبر"),
        ("CLOSED", "خاتمه یافته"),
    ]

    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tickets", verbose_name="کاربر"
    )
    fullname = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    location = models.CharField(max_length=250, verbose_name="محل استقرار اداری")
    mobile = models.CharField(max_length=15, verbose_name="شماره موبایل")
    phone = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="شماره تلفن"
    )
    hardware = models.ForeignKey(
        HardwareInventory,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="مشخصات سیستم",
    )
    current_handler = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"is_staff": True},
        related_name="handled_tickets",
        verbose_name="راهبر پیگیری‌کننده",
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="NEW", verbose_name="وضعیت"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    location = models.ForeignKey(
        OrganizationalUnit, on_delete=models.PROTECT, verbose_name="محل استقرار اداری"
    )

    class Meta:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت‌ها"

    def __str__(self):
        return f"تیکت {self.id} - {self.fullname}"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages", verbose_name="تیکت"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="فرستنده")
    message_text = models.TextField(verbose_name="متن پیام")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")

    class Meta:
        ordering = ["created_at"]
        verbose_name = "پیام"
        verbose_name_plural = "روال گفتگو"


# این مدل را به فایل models.py قبلی اضافه کنید:
