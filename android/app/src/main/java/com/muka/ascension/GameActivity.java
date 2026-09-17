package com.muka.ascension;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.view.Surface;
import android.view.WindowManager;
import android.widget.RelativeLayout;

import org.libsdl.app.SDLActivity;

/** SDL host plus the Android-native mobile control surface. */
public final class GameActivity extends SDLActivity implements SensorEventListener {
    private static final float GYRO_YAW_GAIN = 0.45f;
    private static final float GYRO_PITCH_GAIN = 0.36f;

    private SensorManager sensorManager;
    private Sensor gyroscope;
    private MobileControlsView controls;
    private boolean nativeInputReady;
    private long lastGyroTimestampNs;

    @Override
    protected String[] getLibraries() {
        // The last library is where SDLActivity resolves SDL_main().
        return new String[] { "SDL2", "ascension" };
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // SDLActivity returns early with its own error dialog if native
        // libraries fail to load. Do not mask that useful error with an NPE.
        if (mLayout == null) {
            return;
        }

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

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

        // Mobile input is a permanent additive source while this Activity is
        // alive. Zero-valued touch axes never override a stronger SDL gamepad.
        NativeInput.setTouchActive(true);
        nativeInputReady = true;
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (!nativeInputReady) {
            return;
        }
        NativeInput.setTouchActive(true);
        lastGyroTimestampNs = 0L;
        if (sensorManager != null && gyroscope != null) {
            sensorManager.registerListener(this, gyroscope, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    protected void onPause() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        lastGyroTimestampNs = 0L;
        if (nativeInputReady) {
            NativeInput.reset();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        if (nativeInputReady) {
            NativeInput.reset();
        }
        super.onDestroy();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (!nativeInputReady || controls == null || !controls.hasActiveTouch()
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

        // Sensor axes remain in the device's natural coordinate system. Map
        // them into screen-space yaw/pitch so both landscape orientations work.
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
                clamp(yawRate * dt * GYRO_YAW_GAIN, -0.35f, 0.35f),
                clamp(pitchRate * dt * GYRO_PITCH_GAIN, -0.35f, 0.35f));
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // No calibration state is required for incremental aiming.
    }

    private static float clamp(float value, float lo, float hi) {
        return value < lo ? lo : (value > hi ? hi : value);
    }
}
