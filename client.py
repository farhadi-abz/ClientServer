import sys
import socket
import re
import uuid
import platform
import requests
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QComboBox,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)
from PyQt6.QtCore import Qt

try:
    import wmi
except ImportError:
    wmi = None

SERVER_URL = "http://127.0.0.1:8000"


class AppMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.token = None
        self.all_org_data = []
        self.my_tickets = []  # ذخیره تیکت‌های دریافت شده از سرور
        self.selected_ticket_id = None
        self.hardware_data = self.fetch_hardware_specs()
        self.setup_ui()

    def fetch_hardware_specs(self):
        specs = {
            "hostname": socket.gethostname(),
            "ip": "127.0.0.1",
            "mac": "00:00:00:00:00:00",
            "cpu": platform.processor(),
            "motherboard": "Unknown",
            "ram": "Unknown",
        }
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            specs["ip"] = s.getsockname()[0]
            s.close()
        except:
            pass
        specs["mac"] = ":".join(re.findall("..", "%012x" % uuid.getnode())).upper()
        if wmi:
            try:
                c = wmi.WMI()
                specs["cpu"] = c.Win32_Processor()[0].Name.strip()
                specs["motherboard"] = (
                    f"{c.Win32_BaseBoard()[0].Manufacturer} {c.Win32_BaseBoard()[0].Product}"
                )
                specs["ram"] = (
                    f"{round(int(c.Win32_ComputerSystem()[0].TotalPhysicalMemory) / (1024**3))} GB"
                )
            except:
                pass
        return specs

    def setup_ui(self):
        self.setWindowTitle("سیستم پشتیبانی فنی و تیکتینگ سازمان")
        self.setMinimumSize(650, 550)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        main_layout = QVBoxLayout()

        # هدر اطلاعات سیستم
        sys_box = QLabel(
            f"🖥️ رایانه: {self.hardware_data['hostname']} | 🌐 آی‌پب: {self.hardware_data['ip']}"
        )
        sys_box.setStyleSheet(
            "color: #fff; background-color: #2c3e50; padding: 8px; font-weight: bold;"
        )
        main_layout.addWidget(sys_box)

        # باکس لاگین و احراز هویت اولیه
        auth_layout = QHBoxLayout()
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("نام کاربری")
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("کلمه عبور")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_connect = QPushButton("ورود و اتصال به شبکه")
        self.btn_connect.clicked.connect(self.authenticate_user)

        auth_layout.addWidget(self.txt_user)
        auth_layout.addWidget(self.txt_pass)
        auth_layout.addWidget(self.btn_connect)
        main_layout.addLayout(auth_layout)

        # تعریف تب‌ها
        self.tabs = QTabWidget()
        self.tabs.setEnabled(False)  # تا قبل لاگین غیرفعال است

        # ساخت تب اول: ثبت تیکت
        self.tab_create = QWidget()
        self.setup_create_tab()
        self.tabs.addTab(self.tab_create, "✉️ ثبت درخواست جدید")

        # ساخت تب دوم: سوابق و گفتگو
        self.tab_history = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.tab_history, "💬 کارتابل و سوابق گفتگو")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def setup_create_tab(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("نام و نام خانوادگی کارمند:"))
        self.txt_name = QLineEdit()
        layout.addWidget(self.txt_name)

        layout.addWidget(QLabel("سطح اول (معاونت / مدیریت مستقل):"))
        self.combo_level1 = QComboBox()
        self.combo_level1.currentIndexChanged.connect(self.on_level1_changed)
        layout.addWidget(self.combo_level1)

        layout.addWidget(QLabel("سطح دوم (مدیریت زیرمجموعه):"))
        self.combo_level2 = QComboBox()
        layout.addWidget(self.combo_level2)

        phone_layout = QHBoxLayout()
        self.txt_mobile = QLineEdit()
        self.txt_mobile.setPlaceholderText("موبایل (اجباری)")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("تلفن داخلی")
        phone_layout.addWidget(self.txt_phone)
        phone_layout.addWidget(self.txt_mobile)
        layout.addWidget(QLabel("اطلاعات تماس:"))
        layout.addLayout(phone_layout)

        layout.addWidget(QLabel("شرح مشکل:"))
        self.txt_desc = QTextEdit()
        layout.addWidget(self.txt_desc)

        self.btn_send = QPushButton("ارسال درخواست پشتیبانی به واحد فناوری")
        self.btn_send.setStyleSheet(
            "background-color: #27ae60; color: white; font-weight: bold; padding: 10px;"
        )
        self.btn_send.clicked.connect(self.handle_submission)
        layout.addWidget(self.btn_send)

        self.tab_create.setLayout(layout)

    def setup_history_tab(self):
        layout = QHBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # سمت راست: لیست تیکت‌ها
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<b>لیست تیکت‌های شما:</b>"))
        self.list_tickets = QListWidget()
        self.list_tickets.itemClicked.connect(self.on_ticket_selected)
        left_layout.addWidget(self.list_tickets)
        self.btn_refresh = QPushButton("🔄 بروزرسانی کارتابل")
        self.btn_refresh.clicked.connect(self.load_user_tickets)
        left_layout.addWidget(self.btn_refresh)
        left_widget.setLayout(left_layout)

        # سمت چپ: روال چت و گفتگو
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        self.lbl_chat_title = QLabel("برای مشاهده روال گفتگو، یک تیکت را انتخاب کنید.")
        self.lbl_chat_title.setStyleSheet("font-weight: bold; color: #2980b9;")
        right_layout.addWidget(self.lbl_chat_title)

        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setReadOnly(True)
        right_layout.addWidget(self.txt_chat_history)

        chat_input_layout = QHBoxLayout()
        self.txt_reply_msg = QLineEdit()
        self.txt_reply_msg.setPlaceholderText("متن پاسخ خود را بنویسید...")
        self.btn_send_reply = QPushButton("ارسال")
        self.btn_send_reply.clicked.connect(self.submit_reply)
        chat_input_layout.addWidget(self.txt_reply_msg)
        chat_input_layout.addWidget(self.btn_send_reply)
        right_layout.addLayout(chat_input_layout)

        right_widget.setLayout(right_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)
        self.tab_history.setLayout(layout)

    def authenticate_user(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور الزامی است.")
            return

        try:
            auth_res = requests.post(
                f"{SERVER_URL}/api/api-token-auth/",
                data={"username": username, "password": password},
                timeout=5,
            )
            if auth_res.status_code != 200:
                QMessageBox.critical(self, "خطا", "تایید هویت ناموفق بود.")
                return

            self.token = auth_res.json().get("token")
            headers = {"Authorization": f"Token {self.token}"}

            # دانلود چارت سازمانی
            chart_res = requests.get(
                f"{SERVER_URL}/api/org-chart/", headers=headers, timeout=5
            )
            if chart_res.status_code == 200:
                self.all_org_data = chart_res.json()
                self.populate_level1()
                self.load_user_tickets()  # لود تیکت‌های قبلی در تب دوم

                self.tabs.setEnabled(True)
                self.btn_connect.setText("✓ وارد شد")
                self.btn_connect.setEnabled(False)
            else:
                QMessageBox.critical(self, "خطا", "خطا در دانلود زیرساخت سازمانی.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ارتباط با سرور برقرار نشد: {e}")

    def populate_level1(self):
        self.combo_level1.clear()
        self.combo_level1.addItem("انتخاب کنید...", None)
        for item in self.all_org_data:
            if item["parent"] is None:
                self.combo_level1.addItem(item["name"], item["id"])

    def on_level1_changed(self, index):
        self.combo_level2.clear()
        parent_id = self.combo_level1.currentData()
        if parent_id is None:
            return
        self.combo_level2.addItem("انتخاب کنید...", None)
        for item in self.all_org_data:
            if item["parent"] == parent_id:
                self.combo_level2.addItem(item["name"], item["id"])

    def handle_submission(self):
        selected_unit_id = (
            self.combo_level2.currentData() or self.combo_level1.currentData()
        )
        if (
            selected_unit_id is None
            or not self.txt_mobile.text().strip()
            or not self.txt_desc.toPlainText().strip()
        ):
            QMessageBox.warning(
                self, "خطا", "تکمیل واحد سازمانی، موبایل و شرح مشکل الزامی است."
            )
            return

        payload = {
            "user_info": {
                "fullname": self.txt_name.text().strip(),
                "location": selected_unit_id,
                "mobile": self.txt_mobile.text().strip(),
                "phone": self.txt_phone.text().strip(),
                "description": self.txt_desc.toPlainText().strip(),
            },
            "hardware_info": self.hardware_data,
        }

        try:
            res = requests.post(
                f"{SERVER_URL}/api/tickets/",
                json=payload,
                headers={"Authorization": f"Token {self.token}"},
                timeout=7,
            )
            if res.status_code == 201:
                QMessageBox.information(self, "موفقیت", "درخواست شما ثبت شد.")
                self.txt_desc.clear()
                self.load_user_tickets()  # لیست چت را بروز کن
            else:
                QMessageBox.critical(self, "خطا", "خطا در ثبت.")
        except:
            QMessageBox.critical(self, "خطا", "خطای شبکه.")

    def load_user_tickets(self):
        try:
            res = requests.get(
                f"{SERVER_URL}/api/my-tickets/",
                headers={"Authorization": f"Token {self.token}"},
                timeout=5,
            )
            if res.status_code == 200:
                self.my_tickets = res.json()
                self.list_tickets.clear()
                for ticket in self.my_tickets:
                    item = QListWidgetItem(
                        f"🎫 تیکت {ticket['id']} [{ticket['status_display']}] - راهبر: {ticket['handler_name']}"
                    )
                    item.setData(Qt.ItemDataRole.UserRole, ticket["id"])
                    self.list_tickets.addItem(item)
        except:
            pass

    def on_ticket_selected(self, item):
        self.selected_ticket_id = item.data(Qt.ItemDataRole.UserRole)
        ticket = next(
            (t for t in self.my_tickets if t["id"] == self.selected_ticket_id), None
        )
        if not ticket:
            return

        self.lbl_chat_title.setText(
            f"💬 گفتگو تیکت {ticket['id']} (راهبر: {ticket['handler_name']})"
        )
        self.update_chat_box(ticket)

    def update_chat_box(self, ticket):
        self.txt_chat_history.clear()
        chat_content = ""
        for msg in ticket["messages"]:
            sender_tag = "[کارشناس فناوری]" if msg["is_staff_reply"] else "[شما]"
            chat_content += f"<b>{sender_tag} {msg['sender_name']}:</b><br>{msg['message_text']}<br><small style='color:gray;'>{msg['created_at'][:16].replace('T', ' ')}</small><br><br>"

        self.txt_chat_history.setHtml(chat_content)

        # اگر تیکت بسته شده باشد، دکمه ارسال پاسخ را قفل می‌کنیم
        if ticket["status"] == "CLOSED":
            self.txt_reply_msg.setEnabled(False)
            self.txt_reply_msg.setPlaceholderText("این تیکت خاتمه یافته است.")
            self.btn_send_reply.setEnabled(False)
        else:
            self.txt_reply_msg.setEnabled(True)
            self.txt_reply_msg.setPlaceholderText("متن پاسخ خود را بنویسید...")
            self.btn_send_reply.setEnabled(True)

    def submit_reply(self):
        text = self.txt_reply_msg.text().strip()
        if not text or not self.selected_ticket_id:
            return

        try:
            res = requests.post(
                f"{SERVER_URL}/api/tickets/{self.selected_ticket_id}/reply/",
                json={"message_text": text},
                headers={"Authorization": f"Token {self.token}"},
                timeout=5,
            )
            if res.status_code == 201:
                self.txt_reply_msg.clear()
                self.load_user_tickets()  # لود مجدد داده‌ها
                # رفرش کردن باکس چت فعلی
                ticket = next(
                    (t for t in self.my_tickets if t["id"] == self.selected_ticket_id),
                    None,
                )
                if ticket:
                    self.update_chat_box(ticket)
            else:
                QMessageBox.critical(
                    self, "خطا", res.json().get("error", "خطا در ارسال")
                )
        except:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = AppMainWindow()
    win.show()
    sys.exit(app.exec())
