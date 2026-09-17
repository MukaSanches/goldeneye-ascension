package com.muka.ascension;

import android.annotation.TargetApi;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Build;
import android.os.Bundle;
import android.view.Surface;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.widget.RelativeLayout;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import org.libsdl.app.SDLActivity;

/**
 * Android-first host for the native GoldenEye engine.
 *
 * SDL still owns the GL surface and native thread, while Android owns touch,
 * gyro, system bars, lifecycle and back navigation.
 */
public final class GameActivity extends SDLActivity implements SensorEventListener {
    private static final float GYRO_YAW_GAIN = 82.0f;
    private static final float GYRO_PITCH_GAIN = 70.0f;
    private static final long BUTTON_PULSE_MS = 90L;

    private SensorManager sensorManager;
    private Sensor gyroscope;
    private MobileControlsView controls;
    private boolean nativeInputReady;
    private long lastGyroTimestampNs;
    private Object backCallback33;

    @Override
    protected String[] getLibraries() {
        return new String[] { "SDL2", "ascension" };
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // SDLActivity returns early with its own error dialog if native
        // libraries fail to load. Preserve that diagnostic.
        if (mLayout == null) {
            return;
        }

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        hideSystemBars();

        controls = new MobileControlsView(this);
        RelativeLayout.LayoutParams params = new RelativeLayout.LayoutParams(
                RelativeLayout.LayoutParams.MATCH_PARENT,
                RelativeLayout.LayoutParams.MATCH_PARENT);
        mLayout.addView(controls, params);
        controls.bringToFront();

        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        if (sensorManager != null) {
            gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        }

        if (Build.VERSION.SDK_INT >= 33) {
            registerBackCallback33();
        }

        NativeInput.reset();
        nativeInputReady = true;
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!nativeInputReady) {
            return;
        }

        hideSystemBars();
        lastGyroTimestampNs = 0L;
        if (sensorManager != null && gyroscope != null) {
            sensorManager.registerListener(
                    this, gyroscope, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    protected void onPause() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        lastGyroTimestampNs = 0L;
        if (controls != null) {
            controls.cancelAllInputs();
        }
        if (nativeInputReady) {
            NativeInput.reset();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (Build.VERSION.SDK_INT >= 33) {
            unregisterBackCallback33();
        }
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        if (nativeInputReady) {
            NativeInput.reset();
        }
        super.onDestroy();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemBars();
        }
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        pulsePause();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!nativeInputReady || controls == null
                || !controls.isLookGestureActive()
                || event.sensor.getType() != Sensor.TYPE_GYROSCOPE) {
            lastGyroTimestampNs = 0L;
            return;
        }

        long now = event.timestamp;
        if (lastGyroTimestampNs == 0L) {
            lastGyroTimestampNs = now;
            return;
        }

        float dt = (now - lastGyroTimestampNs) * 1.0e-9f;
        lastGyroTimestampNs = now;
        if (dt <= 0.0f || dt > 0.10f) {
            return;
        }

        float yawRate;
        float pitchRate;
        int rotation = getWindowManager().getDefaultDisplay().getRotation();

        // Sensor axes use the device's natural coordinates. Convert them to
        // the current landscape screen axes before producing relative look.
        switch (rotation) {
            case Surface.ROTATION_90:
                yawRate = -event.values[0];
                pitchRate = event.values[1];
                break;
            case Surface.ROTATION_270:
                yawRate = event.values[0];
                pitchRate = -event.values[1];
                break;
            case Surface.ROTATION_180:
                yawRate = event.values[1];
                pitchRate = event.values[0];
                break;
            case Surface.ROTATION_0:
            default:
                yawRate = -event.values[1];
                pitchRate = -event.values[0];
                break;
        }

        NativeInput.addGyro(
                clamp(yawRate * dt * GYRO_YAW_GAIN, -6.0f, 6.0f),
                clamp(pitchRate * dt * GYRO_PITCH_GAIN, -6.0f, 6.0f));
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // Incremental gyro look needs no calibration state.
    }

    private void pulsePause() {
        if (!nativeInputReady) {
            return;
        }
        NativeInput.setTouchActive(true);
        NativeInput.setButton(NativeInput.BTN_PAUSE, true);

        View host = controls != null ? controls : mLayout;
        if (host != null) {
            host.postDelayed(() -> {
                if (!nativeInputReady) {
                    return;
                }
                NativeInput.setButton(NativeInput.BTN_PAUSE, false);
                if (controls == null || !controls.hasActiveTouch()) {
                    NativeInput.setTouchActive(false);
                }
            }, BUTTON_PULSE_MS);
        }
    }

    private void hideSystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            hideSystemBars30();
        } else {
            hideSystemBarsLegacy();
        }
    }

    @TargetApi(30)
    private void hideSystemBars30() {
        WindowInsetsController controller = getWindow().getInsetsController();
        if (controller == null) {
            return;
        }
        controller.setSystemBarsBehavior(
                WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
        controller.hide(WindowInsets.Type.statusBars()
                | WindowInsets.Type.navigationBars());
    }

    @SuppressWarnings("deprecation")
    private void hideSystemBarsLegacy() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }

    @TargetApi(33)
    private void registerBackCallback33() {
        OnBackInvokedCallback callback = this::pulsePause;
        getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback);
        backCallback33 = callback;
    }

    @TargetApi(33)
    private void unregisterBackCallback33() {
        if (backCallback33 instanceof OnBackInvokedCallback) {
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(
                    (OnBackInvokedCallback) backCallback33);
            backCallback33 = null;
        }
    }

    private static float clamp(float value, float lo, float hi) {
        return value < lo ? lo : (value > hi ? hi : value);
    }
}
