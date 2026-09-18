#!/usr/bin/env bash
set -euo pipefail

APK="$(find runtime-apk -type f -name '*.apk' -print -quit)"
test -n "$APK"
test -f "$APK"

adb wait-for-device
adb shell getprop ro.build.version.sdk | tee smoke-sdk.txt
adb shell getprop ro.product.cpu.abilist | tee smoke-abis.txt
adb shell getconf PAGE_SIZE | tee smoke-page-size.txt || true

adb install -r "$APK" | tee smoke-install.txt
adb logcat -c
adb shell am force-stop com.muka.ascension || true

adb shell am start -W \
  -n com.muka.ascension/.LauncherActivity \
  --ez ascension.selftest true \
  | tee smoke-activity.txt

ok=0
for i in $(seq 1 45); do
  adb logcat -d -v threadtime > smoke-logcat.txt

  if grep -q 'ASCENSION_ANDROID_SELFTEST_OK' smoke-logcat.txt; then
    ok=1
    break
  fi

  if grep -Eq \
    'ASCENSION_ANDROID_SELFTEST_FAILED|android selftest:|Fatal signal|FATAL EXCEPTION|UnsatisfiedLinkError' \
    smoke-logcat.txt; then
    break
  fi

  sleep 1
done

echo '=== Ascension runtime markers ==='
grep -E 'ASCENSION_ANDROID_SELFTEST|android selftest:|Ascension|FATAL EXCEPTION|Fatal signal|UnsatisfiedLinkError' \
  smoke-logcat.txt | tail -n 240 || true

if [ "$ok" -ne 1 ]; then
  echo 'Android runtime self-test did not reach ASCENSION_ANDROID_SELFTEST_OK' >&2
  adb shell dumpsys activity top > smoke-activity-top.txt || true
  exit 1
fi
