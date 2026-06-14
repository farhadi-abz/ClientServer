# Register your models here.
from django.contrib import admin
from django.http import HttpResponse
import openpyxl
from .models import HardwareInventory, Ticket, TicketMessage, OrganizationalUnit


# اکشن خروجی اکسل برای سخت‌افزارها
@admin.action(description="خروجی اکسل از سخت‌افزارهای انتخاب شده")
def export_hardware_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "گزارش سخت‌افزار"
    ws.views.sheetView[0].rightToLeft = True

    headers = [
        "نام دستگاه",
        "آدرس IP",
        "آدرس MAC",
        "مدل CPU",
        "مدل مادربرد",
        "میزان RAM",
        "آخرین بروزرسانی",
    ]
    ws.append(headers)
    for obj in queryset:
        ws.append(
            [
                obj.hostname,
                obj.ip_address,
                obj.mac_address,
                obj.cpu_model,
                obj.motherboard,
                obj.ram_size,
                obj.last_updated.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=hardware_inventory.xlsx"
    wb.save(response)
    return response


# اکشن خروجی اکسل برای تیکت‌ها
@admin.action(description="خروجی اکسل از تیکت‌های انتخاب شده")
def export_tickets_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "گزارش تیکت‌ها"
    ws.views.sheetView[0].rightToLeft = True

    headers = [
        "شناسه تیکت",
        "کاربر",
        "نام و نام خانوادگی",
        "محل استقرار",
        "موبایل",
        "تلفن",
        "راهبر پیگیری‌کننده",
        "وضعیت",
        "تاریخ ثبت",
    ]
    ws.append(headers)
    for obj in queryset:
        handler = obj.current_handler.username if obj.current_handler else "بدون راهبر"
        ws.append(
            [
                obj.id,
                obj.creator.username,
                obj.fullname,
                obj.location,
                obj.mobile,
                obj.phone,
                handler,
                obj.get_status_display(),
                obj.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=tickets_report.xlsx"
    wb.save(response)
    return response


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 1
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "fullname",
        "location",
        "status",
        "current_handler",
        "created_at",
    )
    list_filter = ("status", "location", "created_at")
    search_fields = ("fullname", "mobile", "location")
    inlines = [TicketMessageInline]
    actions = [export_tickets_excel]

    # مدیریت تفکیک دسترسی بین مدیر سیستم و راهبرها
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # مدیر سیستم همه تیکت‌ها را می‌بیند
        return qs.filter(
            current_handler=request.user
        )  # راهبر فقط تیکت‌های ارجاعی به خودش را می‌بیند

    def get_readonly_fields(self, request, obj=None):
        # اگر کاربر سوپریوزر نباشد (یعنی راهبر باشد)، نتواند ارجاع تیکت را تغییر دهد
        if not request.user.is_superuser:
            return (
                "creator",
                "hardware",
                "fullname",
                "location",
                "mobile",
                "phone",
                "current_handler",
            )
        return ()


@admin.register(HardwareInventory)
class HardwareInventoryAdmin(admin.ModelAdmin):
    list_display = (
        "hostname",
        "ip_address",
        "mac_address",
        "cpu_model",
        "ram_size",
        "last_updated",
    )
    search_fields = ("hostname", "ip_address", "mac_address")
    actions = [export_hardware_excel]


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    list_filter = ("parent",)
    search_fields = ("name",)
