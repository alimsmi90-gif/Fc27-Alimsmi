[app]

title = شبیه ساز FC 27 غیر رسمی

package.name = fc27unofficial

package.domain = org.fc27unofficial

source.dir = .

source.include_exts = py,png,jpg,jpeg,kv,old

source.include_patterns = assets/*,assets/**/*

version = 1.1.0

requirements = python3,kivy==2.3.0,requests,pyjnius

orientation = portrait

fullscreen = 0


android.api = 35

android.minapi = 21

# android.ndk = 28c

android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True


android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.private_storage = False


[buildozer]

log_level = 2

warn_on_root = 1

p4a.branch = master
