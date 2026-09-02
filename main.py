import os
import shutil
import threading
import zipfile
import webbrowser

import requests
import kivy

kivy.require("2.0.0")

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform


def has_all_files_access():
    """Return whether Android has granted the storage access this app needs."""
    if platform != "android":
        return True

    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        return bool(Environment.isExternalStorageManager())
    except Exception as exc:
        print("Storage permission check error:", exc)
        return False


def request_all_files_access():
    """Open Android's system screen for the app's all-files permission."""
    if platform != "android":
        return False

    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Settings = autoclass("android.provider.Settings")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")

        activity = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse("package:" + activity.getPackageName()))
        activity.startActivity(intent)
        return True
    except Exception as exc:
        print("Storage settings launch error:", exc)
        return False


def ensure_storage_access():
    """Keep the original /storage/emulated/0 workflow working on Android 11+."""
    if platform != "android" or has_all_files_access():
        return True

    request_all_files_access()
    show_popup(
        "مجوز دسترسی به حافظه",
        "برای دانلود دیتا و اعمال تنظیمات دوربین، دسترسی فایل‌ها لازم است.\n"
        "در صفحه‌ای که باز می‌شود، دسترسی این برنامه را فعال کنید و سپس دوباره عملیات را اجرا کنید."
    )
    return False


APP_NAME = "شبیه ساز FC 27 غیر رسمی"

DATA_DOWNLOAD_URL = "https://s25.uupload.ir/files/irangamepespsp/GAME(2).zip"
DATA_FILE_NAME = "GAME(2).zip"

SIMULATOR_DOWNLOAD_URL = "http://cafebazaar.ir/app/?id=com.parian.pspplugin&ref=share"
PPSSPP_PACKAGE_NAME = "com.parian.pspplugin"

RUBIKA_URL = "https://rubika.ir/id_Iran_game_link"

if platform == "android":
    EXTERNAL_STORAGE_PATH = "/storage/emulated/0"
else:
    EXTERNAL_STORAGE_PATH = os.path.expanduser("~")

GAME_ROOT_PATH = EXTERNAL_STORAGE_PATH

DOWNLOAD_FILE_PATH = os.path.join(
    EXTERNAL_STORAGE_PATH,
    DATA_FILE_NAME
)

TEMP_DOWNLOAD_PATH = DOWNLOAD_FILE_PATH + ".part"

SYSDIR_PATH = os.path.join(
    EXTERNAL_STORAGE_PATH,
    "PSP_GAME",
    "SYSDIR"
)

ASSETS_BASE_PATH = "assets"
CAMERA_COUNT = 5
CAMERA_IMAGE_FILENAME = "Image.png"
CAMERA_EBOOT_FILENAME = "EBOOT.OLD"

GUIDE_TEXT = """
به بخش راهنما و رفع مشکل خوش آمدید!

1. در گام اول روی گزینه «دانلود دیتا» بزنید و صبر کنید
تا دانلود و استخراج به اتمام برسد.

2. روی گزینه «نصب شبیه‌ساز» بزنید و شبیه‌ساز را
از بازار نصب کنید.

3. پس از نصب شبیه‌ساز، روی گزینه «شروع بازی» بزنید
تا PPSSPP باز شود.

4. از بخش «تنظیمات» می‌توانید یکی از ۵ تنظیمات
دوربین را انتخاب کنید.

با انتخاب هر دوربین، فایل تنظیمات همان دوربین
به صورت خودکار جایگزین فایل قبلی می‌شود.

اگر مشکل دیگری وجود داشت، به روبیکا مراجعه کنید.
"""

download_lock = threading.Lock()


def show_popup(title, message):
    def _show(dt):
        content = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(15)
        )

        message_label = Label(
            text=message,
            halign="center",
            valign="middle"
        )

        message_label.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        close_button = Button(
            text="باشه",
            size_hint_y=None,
            height=dp(50)
        )

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.88, 0.5),
            auto_dismiss=False
        )

        close_button.bind(
            on_press=lambda instance: popup.dismiss()
        )

        content.add_widget(message_label)
        content.add_widget(close_button)
        popup.open()

    Clock.schedule_once(_show, 0)


def ensure_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as exc:
        print("Directory creation error:", exc)
        return False


def download_file(url, destination, progress_callback=None, cancel_event=None):
    try:
        if not url.lower().startswith("https://"):
            raise ValueError("لینک دانلود باید HTTPS باشد.")

        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Android) "
                "eFootball-2027-PSP"
            )
        }

        with requests.get(
            url,
            headers=headers,
            stream=True,
            timeout=(20, 60),
            allow_redirects=True
        ) as response:

            response.raise_for_status()

            total_size = int(
                response.headers.get("content-length", "0")
            )

            downloaded = 0

            with open(TEMP_DOWNLOAD_PATH, "wb") as file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 256
                ):
                    if (
                        cancel_event is not None
                        and cancel_event.is_set()
                    ):
                        raise InterruptedError(
                            "دانلود توسط کاربر لغو شد."
                        )

                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (
                            downloaded / total_size
                        ) * 100
                    else:
                        progress = 0

                    if progress_callback:
                        Clock.schedule_once(
                            lambda dt, p=progress:
                            progress_callback(p),
                            0
                        )

        if not os.path.exists(TEMP_DOWNLOAD_PATH):
            raise IOError("فایل دانلودشده ایجاد نشد.")

        file_size = os.path.getsize(TEMP_DOWNLOAD_PATH)

        if file_size <= 0:
            raise IOError("فایل دانلودشده خالی است.")

        if os.path.exists(destination):
            os.remove(destination)

        os.replace(TEMP_DOWNLOAD_PATH, destination)

        if progress_callback:
            Clock.schedule_once(
                lambda dt: progress_callback(100),
                0
            )

        return True, None

    except InterruptedError as exc:
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass
        return False, str(exc)

    except requests.exceptions.Timeout:
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass
        return False, (
            "زمان اتصال به سرور تمام شد.\n"
            "لطفاً اینترنت خود را بررسی کنید."
        )

    except requests.exceptions.ConnectionError:
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass
        return False, "اتصال به اینترنت برقرار نشد."

    except requests.exceptions.HTTPError as exc:
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass
        return False, f"سرور دانلود خطا داد:\n{exc}"

    except Exception as exc:
        if os.path.exists(TEMP_DOWNLOAD_PATH):
            try:
                os.remove(TEMP_DOWNLOAD_PATH)
            except Exception:
                pass
        return False, str(exc)


def validate_zip(zip_path):
    try:
        if not os.path.exists(zip_path):
            return False, "GAME.zip پیدا نشد."

        if os.path.getsize(zip_path) <= 0:
            return False, "GAME.zip خالی است."

        with zipfile.ZipFile(zip_path, "r") as archive:
            if archive.testzip() is not None:
                return False, "فایل ZIP خراب است."

            if not archive.namelist():
                return False, "فایل ZIP خالی است."

        return True, None

    except zipfile.BadZipFile:
        return False, "GAME.zip یک فایل ZIP معتبر نیست."

    except Exception as exc:
        return False, str(exc)


def safe_extract_zip(zip_path, destination):
    try:
        destination = os.path.abspath(destination)

        with zipfile.ZipFile(zip_path, "r") as archive:
            for member in archive.infolist():
                member_path = os.path.abspath(
                    os.path.join(destination, member.filename)
                )

                if not (
                    member_path == destination
                    or member_path.startswith(destination + os.sep)
                ):
                    raise RuntimeError(
                        "ZIP شامل مسیر غیرمجاز است."
                    )

            archive.extractall(destination)

        return True, None

    except zipfile.BadZipFile:
        return False, "فایل ZIP خراب یا نامعتبر است."

    except Exception as exc:
        return False, str(exc)


def verify_game_data():
    psp_game = os.path.join(
        EXTERNAL_STORAGE_PATH,
        "PSP_GAME"
    )

    psp_folder = os.path.join(
        EXTERNAL_STORAGE_PATH,
        "PSP"
    )

    return (
        os.path.isdir(psp_game)
        and os.path.isdir(psp_folder)
    )


def extract_game_data(zip_path):
    valid, error = validate_zip(zip_path)

    if not valid:
        return False, error

    success, error = safe_extract_zip(
        zip_path,
        GAME_ROOT_PATH
    )

    if not success:
        return False, error

    if not verify_game_data():
        return False, (
            "استخراج انجام شد، اما پوشه‌های "
            "PSP و PSP_GAME پیدا نشدند."
        )

    return True, None


def open_url(url):
    try:
        if platform == "android":
            from jnius import autoclass

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            Intent = autoclass(
                "android.content.Intent"
            )

            Uri = autoclass(
                "android.net.Uri"
            )

            intent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse(url)
            )

            PythonActivity.mActivity.startActivity(intent)
        else:
            webbrowser.open(url)

        return True

    except Exception as exc:
        print("URL error:", exc)
        show_popup("خطا", "باز کردن لینک انجام نشد.")
        return False


def launch_ppsspp():
    if platform != "android":
        show_popup(
            "اطلاعات",
            "اجرای PPSSPP فقط روی Android انجام می‌شود."
        )
        return False

    try:
        from jnius import autoclass

        PythonActivity = autoclass(
            "org.kivy.android.PythonActivity"
        )

        Intent = autoclass(
            "android.content.Intent"
        )

        intent = Intent(Intent.ACTION_MAIN)
        intent.setPackage(PPSSPP_PACKAGE_NAME)

        PythonActivity.mActivity.startActivity(intent)
        return True

    except Exception as exc:
        print("PPSSPP launch error:", exc)

        show_popup(
            "PPSSPP نصب نیست",
            "ابتدا PPSSPP را از بخش «نصب شبیه‌ساز» نصب کنید."
        )

        return False


def get_camera_asset_path(camera_number, filename):
    return os.path.join(
        ASSETS_BASE_PATH,
        f"Camera_{camera_number}",
        filename
    )


def apply_camera_setting(camera_number):
    try:
        source = get_camera_asset_path(
            camera_number,
            CAMERA_EBOOT_FILENAME
        )

        destination_directory = SYSDIR_PATH

        destination = os.path.join(
            destination_directory,
            CAMERA_EBOOT_FILENAME
        )

        if not os.path.isfile(source):
            return False, (
                f"فایل تنظیمات دوربین {camera_number} پیدا نشد."
            )

        if not ensure_directory(destination_directory):
            return False, "ساخت پوشه SYSDIR انجام نشد."

        if os.path.exists(destination):
            try:
                os.remove(destination)
            except Exception as exc:
                return False, (
                    "حذف فایل قبلی انجام نشد:\n"
                    f"{exc}"
                )

        shutil.copyfile(source, destination)

        if not os.path.isfile(destination):
            return False, "کپی فایل تنظیمات انجام نشد."

        return True, None

    except Exception as exc:
        return False, str(exc)


class MainLayout(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = "vertical"
        self.padding = dp(15)
        self.spacing = dp(12)

        self.download_running = False
        self.download_cancel_event = None

        self.download_button = None
        self.simulator_button = None
        self.start_game_button = None

        self.create_buttons()

        Clock.schedule_once(
            self.initial_check,
            0.5
        )

        Clock.schedule_once(
            self.show_welcome_popup,
            0.7
        )

    def initial_check(self, dt):
        self.start_game_button.disabled = False

    def show_welcome_popup(self, dt=None):
        content = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(15)
        )

        label = Label(
            text=(
                "به برنامه خوش آمدید!\n"
                "برای ادامه روی تایید بزنید."
            ),
            halign="center",
            valign="middle"
        )

        label.bind(
            size=lambda instance, value:
            setattr(instance, "text_size", value)
        )

        button = Button(
            text="تایید",
            size_hint_y=None,
            height=dp(50)
        )

        popup = Popup(
            title="خوش آمدید",
            content=content,
            size_hint=(0.85, 0.4),
            auto_dismiss=False
        )

        button.bind(
            on_press=lambda instance: popup.dismiss()
        )

        content.add_widget(label)
        content.add_widget(button)

        popup.open()

    def create_buttons(self):
        self.download_button = Button(
            text="دانلود دیتا",
            size_hint_y=None,
            height=dp(65)
        )

        self.download_button.bind(
            on_press=self.download_data
        )

        self.add_widget(self.download_button)

        self.simulator_button = Button(
            text="نصب شبیه‌ساز",
            size_hint_y=None,
            height=dp(65)
        )

        self.simulator_button.bind(
            on_press=self.download_simulator
        )

        self.add_widget(self.simulator_button)

        self.start_game_button = Button(
            text="شروع بازی",
            size_hint_y=None,
            height=dp(65),
            disabled=False
        )

        self.start_game_button.bind(
            on_press=self.start_game
        )

        self.add_widget(self.start_game_button)

        settings_button = Button(
            text="تنظیمات",
            size_hint_y=None,
            height=dp(65)
        )

        settings_button.bind(
            on_press=self.open_settings
        )

        self.add_widget(settings_button)

        guide_button = Button(
            text="راهنما و رفع مشکل",
            size_hint_y=None,
            height=dp(65)
        )

        guide_button.bind(
            on_press=self.open_guide
        )

        self.add_widget(guide_button)

        rubika_button = Button(
            text="روبیکا",
            size_hint_y=None,
            height=dp(65)
        )

        rubika_button.bind(
            on_press=self.open_rubika
        )

        self.add_widget(rubika_button)

    def download_data(self, instance):
        if not ensure_storage_access():
            return

        if self.download_running:
            show_popup(
                "در حال دانلود",
                "دانلود دیتا در حال انجام است."
            )
            return

        self.download_running = True
        self.download_cancel_event = threading.Event()
        self.download_button.disabled = True
        self.download_button.text = "در حال دانلود... 0%"

        thread = threading.Thread(
            target=self._download_data_worker,
            daemon=True
        )

        thread.start()

    def _download_data_worker(self):
        with download_lock:
            success, error = download_file(
                DATA_DOWNLOAD_URL,
                DOWNLOAD_FILE_PATH,
                self.update_download_progress,
                self.download_cancel_event
            )

        if not success:
            Clock.schedule_once(
                lambda dt: self.download_finished(
                    False,
                    error
                ),
                0
            )
            return

        success, error = extract_game_data(
            DOWNLOAD_FILE_PATH
        )

        Clock.schedule_once(
            lambda dt: self.download_finished(
                success,
                error
            ),
            0
        )

    def update_download_progress(self, progress):
        self.download_button.text = (
            f"در حال دانلود... {int(progress)}%"
        )

    def download_finished(self, success, error):
        self.download_running = False
        self.download_button.disabled = False
        self.download_button.text = "دانلود دیتا"

        if success:
            show_popup(
                "موفق",
                "دانلود و استخراج دیتا با موفقیت انجام شد."
            )
        else:
            show_popup(
                "خطا",
                error or "عملیات انجام نشد."
            )

    def download_simulator(self, instance):
        open_url(SIMULATOR_DOWNLOAD_URL)

    def start_game(self, instance):
        launch_ppsspp()

    def open_settings(self, instance):
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(10)
        )

        title = Label(
            text="انتخاب تنظیمات دوربین",
            size_hint_y=None,
            height=dp(45)
        )

        content.add_widget(title)

        scroll = ScrollView()

        camera_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(15),
            padding=dp(5),
            size_hint_y=None
        )

        camera_layout.bind(
            minimum_height=camera_layout.setter("height")
        )

        for camera_number in range(1, CAMERA_COUNT + 1):
            camera_box = BoxLayout(
                orientation="vertical",
                spacing=dp(5),
                size_hint_y=None,
                height=dp(220)
            )

            image_path = get_camera_asset_path(
                camera_number,
                CAMERA_IMAGE_FILENAME
            )

            if os.path.exists(image_path):
                camera_image = Image(
                    source=image_path,
                    size_hint_y=None,
                    height=dp(150),
                    allow_stretch=True,
                    keep_ratio=True
                )
            else:
                camera_image = Label(
                    text="Image.png پیدا نشد.",
                    size_hint_y=None,
                    height=dp(150)
                )

            camera_button = Button(
                text=f"انتخاب تنظیمات دوربین {camera_number}",
                size_hint_y=None,
                height=dp(55)
            )

            camera_button.bind(
                on_press=lambda instance,
                number=camera_number:
                self.select_camera(number, popup)
            )

            camera_box.add_widget(camera_image)
            camera_box.add_widget(camera_button)
            camera_layout.add_widget(camera_box)

        scroll.add_widget(camera_layout)
        content.add_widget(scroll)

        close_button = Button(
            text="بستن",
            size_hint_y=None,
            height=dp(50)
        )

        content.add_widget(close_button)

        popup = Popup(
            title="تنظیمات دوربین",
            content=content,
            size_hint=(0.95, 0.9),
            auto_dismiss=False
        )

        close_button.bind(
            on_press=lambda instance: popup.dismiss()
        )

        popup.open()

    def select_camera(self, camera_number, popup):
        if not ensure_storage_access():
            return

        success, error = apply_camera_setting(camera_number)

        if success:
            popup.dismiss()

            show_popup(
                "موفق",
                f"تنظیمات دوربین {camera_number} با موفقیت اعمال شد."
            )
        else:
            show_popup(
                "خطا",
                error or "اعمال تنظیمات انجام نشد."
            )

    def open_guide(self, instance):
        content = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        scroll = ScrollView()

        label = Label(
            text=GUIDE_TEXT,
            halign="right",
            valign="top",
            size_hint_y=None
        )

        label.bind(
            width=lambda instance, value:
            setattr(instance, "text_size", (value, None))
        )

        label.bind(
            texture_size=lambda instance, value:
            setattr(instance, "height", value[1])
        )

        scroll.add_widget(label)
        content.add_widget(scroll)

        close_button = Button(
            text="بستن",
            size_hint_y=None,
            height=dp(50)
        )

        content.add_widget(close_button)

        popup = Popup(
            title="راهنما و رفع مشکل",
            content=content,
            size_hint=(0.92, 0.85),
            auto_dismiss=False
        )

        close_button.bind(
            on_press=lambda instance: popup.dismiss()
        )

        popup.open()

    def open_rubika(self, instance):
        open_url(RUBIKA_URL)


class EFootball2027PSPApp(App):

    def build(self):
        self.title = APP_NAME
        return MainLayout()


if __name__ == "__main__":
    EFootball2027PSPApp().run()
